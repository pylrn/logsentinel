from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from logsentinel.api import ModelRegistry, create_app
from logsentinel.artifacts import ArtifactMetadata, EnvironmentArtifact
from logsentinel.detection import EncodedSequence
from logsentinel.neural import TransformerSequenceScore
from logsentinel.parsing import DeterministicTemplateMiner
from logsentinel.pipeline import HybridDetector
from logsentinel.schemas import DatasetName


def configured_artifact(
    environment: DatasetName,
    *,
    transformer: bool = False,
    adapter_path=None,
) -> EnvironmentArtifact:
    parser = DeterministicTemplateMiner()
    matches = parser.fit_transform(["normal event", "normal finish", "rare warning"])
    parser.freeze()
    e1, e2, e3 = [item.event_id for item in matches]
    base = datetime(2025, 1, 1, tzinfo=UTC)

    def row(index: int, ids: tuple[str, ...], label: int = 0):
        return EncodedSequence(
            sequence_id=f"s{index}",
            event_ids=ids,
            label=label,
            started_at=base + timedelta(minutes=index),
            ended_at=base + timedelta(minutes=index, seconds=2),
        )

    train = [
        row(0, (e1, e2)),
        row(1, (e1, e2, e1)),
        row(2, (e1, e3)),
        row(3, (e1, e2)),
        row(4, (e1, e2, e3)),
        row(5, (e1, e2)),
    ]
    validation = [
        row(10, (e1, e2), 0),
        row(11, (e1, e3), 0),
        row(12, ("<UNK>", "<UNK>"), 1),
        row(13, ("<UNK>", "<UNK>", "<UNK>"), 1),
    ]
    train_signals = (
        [[0.2, 1.0, 0.0, 0.3] for _ in train] if transformer else None
    )
    validation_signals = (
        [
            [0.2, 1.0, 0.0, 0.3],
            [0.3, 1.0, 0.0, 0.4],
            [5.0, 5.0, 1.0, 2.0],
            [6.0, 6.0, 1.0, 2.2],
        ]
        if transformer
        else None
    )
    detector = HybridDetector(random_state=4).fit(
        train,
        validation,
        train_transformer_signals=train_signals,
        validation_transformer_signals=validation_signals,
    )
    return EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=environment,
            version="test-v1",
            threshold=detector.threshold or 0.5,
            split_id="test-split",
            model_kind="hybrid-transformer" if transformer else "hybrid-statistical",
            adapter_version="adapter-test" if transformer else None,
        ),
        detector=detector,
        parser=parser,
        adapter_path=adapter_path,
    )


def request_event(message: str = "normal event") -> dict[str, object]:
    return {
        "timestamp": "2025-01-01T00:00:00Z",
        "source": "test",
        "host": "node-1",
        "severity": "INFO",
        "message": message,
        "group_id": "block-1",
    }


def client() -> TestClient:
    registry = ModelRegistry(
        [configured_artifact(DatasetName.HDFS), configured_artifact(DatasetName.BGL)]
    )
    return TestClient(create_app(registry))


def test_health_and_model_status_are_versioned() -> None:
    api = client()
    assert api.get("/healthz").json() == {"status": "ready", "models": 2}
    response = api.get("/v1/models/hdfs/status")
    assert response.status_code == 200
    assert response.json()["version"] == "test-v1"
    assert response.json()["environment"] == "hdfs"


def test_score_redacts_secrets_and_returns_components_without_raw_message() -> None:
    api = client()
    secret = "token=super-secret-123"
    response = api.post(
        "/v1/score",
        json={"environment": "hdfs", "events": [request_event(f"normal event {secret}")]},
    )
    assert response.status_code == 200
    body = response.json()
    rendered = str(body)
    assert "super-secret-123" not in rendered
    assert set(body["results"][0]["component_scores"]) == {
        "rarity",
        "pca",
        "isolation_forest",
    }
    assert body["model_version"] == "test-v1"
    assert body["results"][0]["expected_templates"]


def test_anomaly_query_and_feedback_do_not_cross_environment() -> None:
    api = client()
    anomalous = [request_event(f"unknown-{index}") for index in range(5)]
    score = api.post("/v1/score", json={"environment": "hdfs", "events": anomalous})
    result_id = score.json()["results"][0]["result_id"]
    feedback = api.post(
        "/v1/feedback",
        json={"environment": "hdfs", "result_id": result_id, "verdict": "confirmed"},
    )
    assert feedback.status_code == 202
    hdfs = api.get("/v1/anomalies", params={"environment": "hdfs"}).json()
    bgl = api.get("/v1/anomalies", params={"environment": "bgl"}).json()
    assert all(item["environment"] == "hdfs" for item in hdfs["items"])
    assert bgl["items"] == []


def test_score_rejects_empty_and_oversized_batches() -> None:
    api = client()
    empty = api.post("/v1/score", json={"environment": "hdfs", "events": []})
    oversized = api.post(
        "/v1/score",
        json={"environment": "hdfs", "events": [request_event()] * 10_001},
    )
    assert empty.status_code == 422
    assert oversized.status_code == 422


def test_unknown_environment_model_returns_not_found() -> None:
    registry = ModelRegistry([configured_artifact(DatasetName.HDFS)])
    api = TestClient(create_app(registry))
    assert api.get("/v1/models/bgl/status").status_code == 404


def test_score_uses_packaged_qwen_adapter_signals_and_predictions(tmp_path) -> None:
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    artifact = configured_artifact(
        DatasetName.HDFS, transformer=True, adapter_path=adapter
    )
    calls = []

    class FakeScorer:
        def score(self, sequences):
            return [
                TransformerSequenceScore(
                    negative_log_likelihood=0.2,
                    mean_rank=1.0,
                    top_k_miss_rate=0.0,
                    entropy=0.3,
                    expected_event_ids=(sequences[0].event_ids[0],),
                )
            ]

    def factory(path):
        calls.append(path)
        return FakeScorer()

    registry = ModelRegistry([artifact], transformer_scorer_factory=factory)
    api = TestClient(create_app(registry))
    response = api.post(
        "/v1/score",
        json={
            "environment": "hdfs",
            "events": [request_event("normal event"), request_event("normal finish")],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["adapter_version"] == "adapter-test"
    assert {"qwen_nll", "qwen_rank", "qwen_top_k_miss", "qwen_entropy"} <= set(
        body["results"][0]["component_scores"]
    )
    assert body["results"][0]["expected_templates"] == ["normal event"]
    assert calls == [adapter]
    status = api.get("/v1/models/hdfs/status").json()
    assert status["inference_backend"] == "qwen-adapter"
    assert status["adapter_loaded"] is True
