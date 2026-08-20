from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_report(
    *,
    labels: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    latencies_ms: np.ndarray | None = None,
) -> dict[str, float]:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    predictions = (scores >= threshold).astype(int)
    normal_count = max(int(np.sum(labels == 0)), 1)
    false_positives = int(np.sum((labels == 0) & (predictions == 1)))
    report = {
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "pr_auc": float(average_precision_score(labels, scores)),
        "roc_auc": _safe_roc_auc(labels, scores),
        "false_alerts_per_1000": false_positives / normal_count * 1000,
        "threshold": float(threshold),
    }
    if latencies_ms is not None and len(latencies_ms):
        report["p50_latency_ms"] = float(np.percentile(latencies_ms, 50))
        report["p95_latency_ms"] = float(np.percentile(latencies_ms, 95))
    return report


def bootstrap_f1_interval(
    labels: np.ndarray,
    predictions: np.ndarray,
    *,
    samples: int = 1000,
    random_state: int = 42,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    if samples <= 0:
        raise ValueError("samples must be positive")
    labels = np.asarray(labels, dtype=int)
    predictions = np.asarray(predictions, dtype=int)
    if len(labels) != len(predictions) or len(labels) == 0:
        raise ValueError("labels and predictions must be non-empty and equally sized")
    generator = np.random.default_rng(random_state)
    estimates = []
    for _ in range(samples):
        indices = generator.integers(0, len(labels), len(labels))
        estimates.append(f1_score(labels[indices], predictions[indices], zero_division=0))
    alpha = (1 - confidence) / 2
    return (
        float(np.quantile(estimates, alpha)),
        float(f1_score(labels, predictions, zero_division=0)),
        float(np.quantile(estimates, 1 - alpha)),
    )


def _safe_roc_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(labels)) < 2:
        return float("nan")
    return float(roc_auc_score(labels, scores))

