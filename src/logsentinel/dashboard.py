from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from logsentinel.ui.client import DashboardApiClient as UiDashboardApiClient
from logsentinel.ui.models import AppMode


def score_tone(score: float) -> str:
    """Return string severity tone based on operational thresholds."""
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.3:
        return "low"
    return "normal"


def dashboard_sample_data(environment: str) -> dict[str, Any]:
    """Provide backwards-compatible sample data dictionary for offline testing."""
    start = datetime(2025, 5, 12, tzinfo=UTC)
    scores = [
        0.12,
        0.34,
        0.18,
        0.77,
        0.63,
        0.22,
        0.16,
        0.41,
        0.68,
        0.51,
        0.27,
        0.19,
        0.13,
        0.16,
        0.21,
        0.74,
        0.32,
        0.66,
        0.24,
        0.17,
        0.38,
        0.82,
        0.58,
        0.26,
    ]
    timeline = [
        {
            "timestamp": start + timedelta(hours=index),
            "score": score,
            "tone": score_tone(score),
        }
        for index, score in enumerate(scores)
    ]
    incidents = [
        {
            "id": f"sample-{index}",
            "time": (start + timedelta(hours=hour)).isoformat(),
            "source": source,
            "score": score,
            "signal": signal,
            "status": status,
            "environment": environment,
        }
        for index, (hour, source, score, signal, status) in enumerate(
            [
                (21, "DataNode-3", 0.96, "Template rarity", "New"),
                (15, "NameNode-1", 0.91, "Event burst", "Investigating"),
                (8, "DataNode-7", 0.82, "Sequence deviation", "New"),
                (17, "JournalNode-2", 0.78, "PCA reconstruction", "Acknowledged"),
                (4, "DataNode-5", 0.63, "Unseen template", "Investigating"),
                (2, "NameNode-1", 0.58, "Isolation Forest", "New"),
            ]
        )
    ]
    return {
        "sample_data": True,
        "benchmark_label": "Illustrative preview — not measured results",
        "environment": environment,
        "model_version": "sample-preview",
        "model_status": "preview",
        "timeline": timeline,
        "incidents": incidents,
        "benchmarks": [
            {"model": "PCA", "pr_auc": 0.61, "recall": 0.41, "alerts": 412},
            {
                "model": "Isolation Forest",
                "pr_auc": 0.68,
                "recall": 0.54,
                "alerts": 286,
            },
            {"model": "DeepLog", "pr_auc": 0.73, "recall": 0.61, "alerts": 198},
            {
                "model": "Transformer",
                "pr_auc": 0.81,
                "recall": 0.71,
                "alerts": 156,
            },
            {"model": "Hybrid", "pr_auc": 0.86, "recall": 0.78, "alerts": 142},
        ],
        "onboarding": [
            {
                "name": "Redact",
                "description": "Remove sensitive fields",
                "status": "Done",
            },
            {
                "name": "Parse",
                "description": "Extract templates",
                "status": "Done",
            },
            {
                "name": "Train adapter",
                "description": "Learn domain patterns",
                "status": "Done",
            },
            {
                "name": "Calibrate",
                "description": "Validate thresholds",
                "status": "In progress",
            },
            {
                "name": "Deploy",
                "description": "Enable monitoring",
                "status": "Pending",
            },
        ],
    }


class DashboardApiClient:
    """Backwards-compatible wrapper around UiDashboardApiClient."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = UiDashboardApiClient(self.base_url)

    def status(self, environment: str) -> dict[str, Any]:
        import httpx

        response = httpx.get(
            f"{self.base_url}/v1/models/{environment}/status", timeout=5
        )
        response.raise_for_status()
        return response.json()

    def anomalies(self, environment: str) -> list[dict[str, Any]]:
        import httpx

        response = httpx.get(
            f"{self.base_url}/v1/anomalies",
            params={"environment": environment, "limit": 100},
            timeout=5,
        )
        response.raise_for_status()
        return response.json().get("items", [])

    def score(
        self, environment: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._client.score_events(environment, events)


def main() -> None:
    """Entrypoint parsing arguments and dispatching to modular UI app."""
    try:
        import streamlit  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Dashboard requires: pip install 'logsentinel[dashboard]'"
        ) from exc

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--api-url",
        default=os.getenv("LOGSENTINEL_API_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--env",
        default=os.getenv("LOGSENTINEL_ENV", "hdfs"),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=os.getenv("LOGSENTINEL_DEMO", "true").lower()
        in ("1", "true", "yes"),
    )
    args, _ = parser.parse_known_args()

    mode = AppMode.DEMO if args.demo else AppMode.LIVE

    from logsentinel.ui.app import main as ui_main

    ui_main(api_url=args.api_url, default_env=args.env, default_mode=mode)


if __name__ == "__main__":
    main()
