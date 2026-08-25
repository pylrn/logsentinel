from __future__ import annotations

from typing import Any

from logsentinel.ui.models import Incident, ModelStatus, score_tone


class ApiConnectionError(Exception):
    """Raised when Live API connection fails without silent fallback."""


class DashboardApiClient:
    """Strict Live API client for LogSentinel backend services.

    Zero silent fallback: all HTTP errors, timeouts, and network failures
    raise `ApiConnectionError` without falling back to mock or demo data.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> dict[str, Any]:
        """Perform a health check against the live backend."""
        import httpx

        try:
            response = httpx.get(f"{self.base_url}/health", timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ApiConnectionError(f"Health check failed at {self.base_url}: {exc}") from exc

    def status(self, environment: str) -> ModelStatus:
        """Query current model status for an environment."""
        import httpx

        try:
            response = httpx.get(
                f"{self.base_url}/v1/models/{environment}/status", timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return ModelStatus(
                name=environment,
                version=data.get("version", "unknown"),
                model_kind=data.get("model_kind", "hybrid-statistical"),
                status=data.get("status", "ready"),
                threshold=float(data.get("threshold", 0.5)),
                events_indexed=int(data.get("events_indexed", 0)),
                vocabulary_size=int(data.get("vocabulary_size", 0)),
            )
        except Exception as exc:
            raise ApiConnectionError(
                f"Failed to query model status for '{environment}' from {self.base_url}: {exc}"
            ) from exc

    def anomalies(self, environment: str, limit: int = 100) -> list[Incident]:
        """Query scored anomalies and convert to typed Incident objects."""
        import httpx

        try:
            response = httpx.get(
                f"{self.base_url}/v1/anomalies",
                params={"environment": environment, "limit": limit},
                timeout=5,
            )
            response.raise_for_status()
            raw_items = response.json().get("items", [])
            incidents: list[Incident] = []
            for item in raw_items:
                score = float(item.get("anomaly_score", item.get("score", 0.0)))
                incidents.append(
                    Incident(
                        id=str(item.get("result_id") or item.get("id", "alert")),
                        time=str(
                            item.get("started_at")
                            or item.get("timestamp")
                            or item.get("time", "")
                        ),
                        source=str(
                            item.get("source")
                            or item.get("sequence_id", "unknown")
                        ),
                        score=score,
                        tone=score_tone(score),
                        signal=str(
                            item.get("signal")
                            or item.get("explanation", "Anomaly detection")
                        ),
                        status=str(item.get("status", "Active")),
                        environment=environment,
                        raw_message_redacted=str(
                            item.get("raw_message_redacted")
                            or item.get("message", "")
                        ),
                        template_id=str(item.get("template_id", "E_UNK")),
                        template_text=str(
                            item.get("template_text")
                            or (
                                item.get("detected_templates")
                                and item["detected_templates"][-1]
                            )
                            or item.get("template", "")
                        ),
                        context_sequence=list(
                            item.get("context_sequence")
                            or item.get("recent_context", [])
                        ),
                        expected_templates=list(item.get("expected_templates", [])),
                        contributions=dict(
                            item.get("contributions")
                            or item.get("component_scores", {})
                        ),
                    )
                )
            return incidents
        except Exception as exc:
            raise ApiConnectionError(
                f"Failed to fetch anomalies for '{environment}' from {self.base_url}: {exc}"
            ) from exc

    def score_events(
        self, environment: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Submit a batch of raw/structured events for real-time scoring."""
        import httpx

        try:
            response = httpx.post(
                f"{self.base_url}/v1/score",
                json={"environment": environment, "events": events},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ApiConnectionError(
                f"Scoring request failed at {self.base_url}: {exc}"
            ) from exc

    def submit_feedback(
        self,
        environment: str,
        incident_id: str,
        feedback: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Submit analyst feedback for an incident/result."""
        import httpx

        try:
            response = httpx.post(
                f"{self.base_url}/v1/feedback",
                json={
                    "environment": environment,
                    "incident_id": incident_id,
                    "feedback": feedback,
                    "reason": reason,
                },
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ApiConnectionError(
                f"Failed to submit feedback to {self.base_url}: {exc}"
            ) from exc
