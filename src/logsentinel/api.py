from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from threading import RLock
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from logsentinel.artifacts import EnvironmentArtifact
from logsentinel.detection import EncodedSequence
from logsentinel.privacy import Redactor, stable_hash
from logsentinel.schemas import DatasetName


class ScoreEventInput(BaseModel):
    timestamp: datetime
    source: str = Field(min_length=1, max_length=256)
    host: str = Field(min_length=1, max_length=256)
    severity: str = Field(min_length=1, max_length=32)
    message: str = Field(min_length=1, max_length=32_768)
    group_id: str | None = Field(default=None, max_length=256)

    @field_validator("timestamp")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value


class ScoreRequest(BaseModel):
    environment: DatasetName
    events: list[ScoreEventInput] = Field(min_length=1, max_length=10_000)


class ScoreResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_id: str
    environment: DatasetName
    sequence_id: str
    started_at: datetime
    ended_at: datetime
    anomaly_score: float
    is_anomaly: bool
    component_scores: dict[str, float]
    expected_templates: list[str]
    detected_templates: list[str]
    recent_context: list[str]
    explanation: str


class ScoreResponse(BaseModel):
    environment: DatasetName
    model_version: str
    adapter_version: str | None
    threshold: float
    results: list[ScoreResult]


class AnalystVerdict(StrEnum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class FeedbackRequest(BaseModel):
    environment: DatasetName
    result_id: str = Field(min_length=3, max_length=128)
    verdict: AnalystVerdict
    note: str | None = Field(default=None, max_length=1000)


class ModelRegistry:
    def __init__(self, artifacts: list[EnvironmentArtifact]) -> None:
        self._artifacts = {item.metadata.environment: item for item in artifacts}

    def get(self, environment: DatasetName) -> EnvironmentArtifact:
        try:
            return self._artifacts[DatasetName(environment)]
        except KeyError as exc:
            raise KeyError(f"no model loaded for {environment}") from exc

    def __len__(self) -> int:
        return len(self._artifacts)


class ScoringService:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self.redactor = Redactor()
        self._results: dict[DatasetName, list[ScoreResult]] = {
            environment: [] for environment in DatasetName
        }
        self._feedback: list[FeedbackRequest] = []
        self._lock = RLock()

    def score(self, request: ScoreRequest) -> ScoreResponse:
        artifact = self.registry.get(request.environment)
        ordered = sorted(request.events, key=lambda item: item.timestamp)
        matches = [
            artifact.parser.transform(self.redactor.redact(item.message)) for item in ordered
        ]
        event_ids = tuple(item.event_id for item in matches)
        identity = stable_hash(
            "|".join(
                [
                    request.environment.value,
                    artifact.metadata.version,
                    *(item.timestamp.isoformat() for item in ordered),
                    *event_ids,
                ]
            ),
            salt="score-result",
        )
        encoded = EncodedSequence(
            sequence_id=f"request:{identity}",
            event_ids=event_ids,
            label=0,
            started_at=ordered[0].timestamp,
            ended_at=ordered[-1].timestamp,
        )
        score = artifact.detector.score([encoded])[0]
        expected_ids = artifact.detector.expected_next(event_ids, top_k=3)
        expected_templates = [
            artifact.parser.template_for_event(event_id) or event_id
            for event_id in expected_ids
        ]
        strongest = max(score.contributions, key=lambda name: abs(score.contributions[name]))
        explanation = (
            f"Flagged because {strongest.replace('_', ' ')} contributed most to the "
            "calibrated anomaly score."
            if score.is_anomaly
            else "The sequence remains within the calibrated normal-behavior threshold."
        )
        result = ScoreResult(
            result_id=identity,
            environment=request.environment,
            sequence_id=encoded.sequence_id,
            started_at=encoded.started_at,
            ended_at=encoded.ended_at,
            anomaly_score=score.anomaly_score,
            is_anomaly=score.is_anomaly,
            component_scores=score.component_scores,
            expected_templates=expected_templates,
            detected_templates=[item.template for item in matches[-10:]],
            recent_context=list(event_ids[-10:]),
            explanation=explanation,
        )
        with self._lock:
            self._results[request.environment].append(result)
        return ScoreResponse(
            environment=request.environment,
            model_version=artifact.metadata.version,
            adapter_version=artifact.metadata.adapter_version,
            threshold=artifact.metadata.threshold,
            results=[result],
        )

    def anomalies(self, environment: DatasetName) -> list[ScoreResult]:
        with self._lock:
            return [item for item in self._results[environment] if item.is_anomaly]

    def feedback(self, request: FeedbackRequest) -> None:
        with self._lock:
            known = any(
                item.result_id == request.result_id
                for item in self._results[request.environment]
            )
            if not known:
                raise KeyError("result does not exist in this environment")
            self._feedback.append(request)


def create_app(registry: ModelRegistry) -> FastAPI:
    app = FastAPI(title="LogSentinel API", version="0.1.0")
    service = ScoringService(registry)
    app.state.scoring_service = service

    @app.get("/healthz")
    def health() -> dict[str, object]:
        return {"status": "ready", "models": len(registry)}

    @app.get("/v1/models/{environment}/status")
    def model_status(environment: DatasetName) -> dict[str, object]:
        try:
            artifact = registry.get(environment)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "environment": environment,
            "version": artifact.metadata.version,
            "adapter_version": artifact.metadata.adapter_version,
            "threshold": artifact.metadata.threshold,
            "split_id": artifact.metadata.split_id,
            "model_kind": artifact.metadata.model_kind,
            "status": "ready",
        }

    @app.post("/v1/score", response_model=ScoreResponse)
    def score(request: ScoreRequest) -> ScoreResponse:
        try:
            return service.score(request)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/v1/anomalies")
    def anomalies(
        environment: Annotated[DatasetName, Query()],
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    ) -> dict[str, object]:
        return {"items": service.anomalies(environment)[-limit:]}

    @app.post("/v1/feedback", status_code=status.HTTP_202_ACCEPTED)
    def feedback(request: FeedbackRequest) -> dict[str, str]:
        try:
            service.feedback(request)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"status": "accepted"}

    return app
