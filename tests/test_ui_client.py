from __future__ import annotations

from typing import Any

import pytest

from logsentinel.ui.client import ApiConnectionError, DashboardApiClient
from logsentinel.ui.models import AnomalyTone, Incident, ModelStatus


class MockResponse:
    def __init__(self, json_data: Any, status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def json(self) -> Any:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_client_initialization_and_url_normalization() -> None:
    default_client = DashboardApiClient()
    assert default_client.base_url == "http://127.0.0.1:8000"

    custom_client = DashboardApiClient("http://localhost:9000/")
    assert custom_client.base_url == "http://localhost:9000"


def test_health_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://mock-api")
    captured_urls: list[str] = []

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        captured_urls.append(url)
        return MockResponse({"status": "ready", "models": 2})

    monkeypatch.setattr("httpx.get", mock_get)
    result = client.health()
    assert result == {"status": "ready", "models": 2}
    assert captured_urls == ["http://mock-api/health"]


def test_health_failure_raises_api_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://mock-api")

    def mock_get_error(*args: Any, **kwargs: Any) -> MockResponse:
        return MockResponse({"detail": "Service Unavailable"}, status_code=503)

    monkeypatch.setattr("httpx.get", mock_get_error)
    with pytest.raises(ApiConnectionError) as exc_info:
        client.health()
    assert "Health check failed" in str(exc_info.value)


def test_status_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://mock-api")
    captured: dict[str, Any] = {}

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MockResponse(
            {
                "environment": "hdfs",
                "version": "hdfs-v1",
                "model_kind": "hybrid-transformer",
                "status": "ready",
                "threshold": 0.82,
                "events_indexed": 482000,
                "vocabulary_size": 29,
            }
        )

    monkeypatch.setattr("httpx.get", mock_get)
    status = client.status("hdfs")

    assert captured["url"] == "http://mock-api/v1/models/hdfs/status"
    assert isinstance(status, ModelStatus)
    assert status.name == "hdfs"
    assert status.version == "hdfs-v1"
    assert status.model_kind == "hybrid-transformer"
    assert status.status == "ready"
    assert status.threshold == 0.82
    assert status.events_indexed == 482000
    assert status.vocabulary_size == 29


def test_status_failure_raises_api_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://mock-api")

    def mock_get_404(*args: Any, **kwargs: Any) -> MockResponse:
        return MockResponse({"detail": "Environment not found"}, status_code=404)

    monkeypatch.setattr("httpx.get", mock_get_404)
    with pytest.raises(ApiConnectionError) as exc_info:
        client.status("unknown_env")
    assert "Failed to query model status for 'unknown_env'" in str(exc_info.value)


def test_anomalies_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://mock-api")
    captured: dict[str, Any] = {}

    def mock_get(url: str, **kwargs: Any) -> MockResponse:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MockResponse(
            {
                "items": [
                    {
                        "id": "HDFS-INC-01",
                        "timestamp": "2025-05-12T12:00:00Z",
                        "source": "DataNode-3",
                        "score": 0.95,
                        "signal": "Template rarity",
                        "status": "Active",
                        "environment": "hdfs",
                        "raw_message_redacted": "Received block <BLOCK_ID>",
                        "template_id": "E_4af1",
                        "template_text": "Received block <*>",
                        "context_sequence": ["E_0012", "E_4af1"],
                        "expected_templates": ["Block verification succeeded"],
                        "contributions": {"Rarity": 0.42, "PCA": 0.31},
                    },
                    {
                        "result_id": "HDFS-INC-02",
                        "started_at": "2025-05-12T12:05:00Z",
                        "sequence_id": "seq-42",
                        "anomaly_score": 0.35,
                        "explanation": "Low rarity spike",
                        "status": "Investigating",
                        "message": "Heartbeat slow",
                        "detected_templates": ["E_0001", "E_0002"],
                        "recent_context": ["E_0001"],
                        "expected_templates": ["Heartbeat ok"],
                        "component_scores": {"rarity": 0.35},
                    },
                ]
            }
        )

    monkeypatch.setattr("httpx.get", mock_get)
    incidents = client.anomalies("hdfs", limit=50)

    assert captured["url"] == "http://mock-api/v1/anomalies"
    assert captured["kwargs"]["params"] == {"environment": "hdfs", "limit": 50}
    assert len(incidents) == 2

    first = incidents[0]
    assert isinstance(first, Incident)
    assert first.id == "HDFS-INC-01"
    assert first.time == "2025-05-12T12:00:00Z"
    assert first.source == "DataNode-3"
    assert first.score == 0.95
    assert first.tone == AnomalyTone.HIGH
    assert first.signal == "Template rarity"
    assert first.status == "Active"
    assert first.environment == "hdfs"
    assert first.raw_message_redacted == "Received block <BLOCK_ID>"
    assert first.template_id == "E_4af1"
    assert first.template_text == "Received block <*>"
    assert first.context_sequence == ["E_0012", "E_4af1"]
    assert first.expected_templates == ["Block verification succeeded"]
    assert first.contributions == {"Rarity": 0.42, "PCA": 0.31}

    second = incidents[1]
    assert isinstance(second, Incident)
    assert second.id == "HDFS-INC-02"
    assert second.time == "2025-05-12T12:05:00Z"
    assert second.source == "seq-42"
    assert second.score == 0.35
    assert second.tone == AnomalyTone.LOW
    assert second.signal == "Low rarity spike"
    assert second.contributions == {"rarity": 0.35}


def test_anomalies_failure_raises_api_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = DashboardApiClient("http://mock-api")

    def mock_get_error(*args: Any, **kwargs: Any) -> MockResponse:
        raise ConnectionError("Network unreachable")

    monkeypatch.setattr("httpx.get", mock_get_error)
    with pytest.raises(ApiConnectionError) as exc_info:
        client.anomalies("hdfs")
    assert "Failed to fetch anomalies for 'hdfs'" in str(exc_info.value)


def test_score_events_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://mock-api")
    captured: dict[str, Any] = {}

    def mock_post(url: str, **kwargs: Any) -> MockResponse:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MockResponse(
            {
                "environment": "hdfs",
                "model_version": "v1",
                "threshold": 0.82,
                "results": [{"anomaly_score": 0.95, "is_anomaly": True}],
            }
        )

    monkeypatch.setattr("httpx.post", mock_post)
    events = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "source": "test",
            "host": "node-1",
            "severity": "INFO",
            "message": "log event",
        }
    ]
    result = client.score_events("hdfs", events)

    assert captured["url"] == "http://mock-api/v1/score"
    assert captured["kwargs"]["json"] == {"environment": "hdfs", "events": events}
    assert captured["kwargs"]["timeout"] == 30
    assert result["threshold"] == 0.82
    assert result["results"][0]["anomaly_score"] == 0.95


def test_score_events_failure_raises_api_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = DashboardApiClient("http://mock-api")

    def mock_post_error(*args: Any, **kwargs: Any) -> MockResponse:
        return MockResponse({"detail": "Validation error"}, status_code=422)

    monkeypatch.setattr("httpx.post", mock_post_error)
    with pytest.raises(ApiConnectionError) as exc_info:
        client.score_events("hdfs", [])
    assert "Scoring request failed" in str(exc_info.value)


def test_submit_feedback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://mock-api")
    captured: dict[str, Any] = {}

    def mock_post(url: str, **kwargs: Any) -> MockResponse:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MockResponse({"status": "accepted"})

    monkeypatch.setattr("httpx.post", mock_post)
    result = client.submit_feedback(
        environment="hdfs",
        incident_id="HDFS-INC-01",
        feedback="confirmed",
        reason="Known issue",
    )

    assert captured["url"] == "http://mock-api/v1/feedback"
    assert captured["kwargs"]["json"] == {
        "environment": "hdfs",
        "incident_id": "HDFS-INC-01",
        "feedback": "confirmed",
        "reason": "Known issue",
    }
    assert result == {"status": "accepted"}


def test_submit_feedback_failure_raises_api_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = DashboardApiClient("http://mock-api")

    def mock_post_error(*args: Any, **kwargs: Any) -> MockResponse:
        return MockResponse({"detail": "Not found"}, status_code=404)

    monkeypatch.setattr("httpx.post", mock_post_error)
    with pytest.raises(ApiConnectionError) as exc_info:
        client.submit_feedback("hdfs", "unknown-inc", "rejected")
    assert "Failed to submit feedback" in str(exc_info.value)


def test_never_silently_falls_back_to_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DashboardApiClient("http://down-api")

    def raise_offline(*args: Any, **kwargs: Any) -> MockResponse:
        raise ConnectionError("Server is down")

    monkeypatch.setattr("httpx.get", raise_offline)
    monkeypatch.setattr("httpx.post", raise_offline)

    # Must raise ApiConnectionError on ALL methods, NEVER return demo fixtures
    with pytest.raises(ApiConnectionError):
        client.health()

    with pytest.raises(ApiConnectionError):
        client.status("hdfs")

    with pytest.raises(ApiConnectionError):
        client.anomalies("hdfs")

    with pytest.raises(ApiConnectionError):
        client.score_events("hdfs", [{"message": "test"}])

    with pytest.raises(ApiConnectionError):
        client.submit_feedback("hdfs", "inc-1", "confirmed")
