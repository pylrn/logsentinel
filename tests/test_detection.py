from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from logsentinel.detection import (
    EncodedSequence,
    FeatureExtractor,
    FusionCalibrator,
    IsolationForestDetector,
    NormalOnlyCalibrator,
    PCADetector,
    RarityDetector,
)
from logsentinel.evaluation import bootstrap_f1_interval, classification_report


def sequence(
    identifier: str,
    event_ids: tuple[str, ...],
    *,
    label: int = 0,
    duration: float = 10,
) -> EncodedSequence:
    return EncodedSequence(
        sequence_id=identifier,
        event_ids=event_ids,
        label=label,
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        ended_at=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(seconds=duration),
    )


@pytest.fixture
def training_sequences() -> list[EncodedSequence]:
    return [
        sequence("a", ("E1", "E2", "E1"), duration=3),
        sequence("b", ("E1", "E2"), duration=2),
        sequence("c", ("E1", "E3"), duration=2),
        sequence("d", ("E1", "E2", "E3"), duration=3),
        sequence("e", ("E1", "E2"), duration=2),
    ]


def test_feature_extractor_freezes_train_vocabulary_and_scores_unknowns(
    training_sequences: list[EncodedSequence],
) -> None:
    extractor = FeatureExtractor().fit(training_sequences)
    before = extractor.vocabulary
    row = extractor.transform([sequence("new", ("E1", "NEVER_SEEN"))])
    assert extractor.vocabulary == before
    assert row.counts.shape == (1, len(before))
    assert row.signals[0, extractor.signal_names.index("unseen_rate")] == 0.5
    assert np.isfinite(row.signals).all()


def test_rarity_detector_scores_unseen_sequence_higher(
    training_sequences: list[EncodedSequence],
) -> None:
    detector = RarityDetector().fit(training_sequences)
    normal, unknown = detector.score(
        [sequence("normal", ("E1", "E2")), sequence("unknown", ("X", "Y"))]
    )
    assert unknown > normal


@pytest.mark.parametrize("detector", [PCADetector(), IsolationForestDetector(random_state=7)])
def test_unsupervised_baselines_return_finite_scores(detector, training_sequences) -> None:
    detector.fit(training_sequences)
    scores = detector.score([sequence("x", ("E1", "E2")), sequence("y", ("X",))])
    assert scores.shape == (2,)
    assert np.isfinite(scores).all()


def test_fusion_calibrator_is_interpretable_and_deterministic() -> None:
    features = np.array(
        [
            [0.1, 0.0, 0.1],
            [0.2, 0.1, 0.0],
            [2.0, 1.0, 1.2],
            [3.0, 1.0, 2.0],
        ]
    )
    labels = np.array([0, 0, 1, 1])
    fusion = FusionCalibrator(feature_names=("rarity", "unseen", "burst")).fit(
        features, labels
    )
    first = fusion.score(features)
    second = fusion.score(features)
    assert np.allclose(first, second)
    assert first[-1] > first[0]
    assert set(fusion.explain(features[-1])) == {"rarity", "unseen", "burst"}


def test_fusion_requires_both_classes() -> None:
    with pytest.raises(ValueError, match="both normal and anomalous"):
        FusionCalibrator(feature_names=("a",)).fit(np.ones((3, 1)), np.zeros(3))


def test_normal_only_calibration_uses_quantile_and_flags_high_scores() -> None:
    calibrator = NormalOnlyCalibrator(quantile=0.8).fit(np.array([0, 1, 2, 3, 4]))
    assert calibrator.threshold == pytest.approx(3.2)
    assert calibrator.predict(np.array([3.0, 4.0])).tolist() == [0, 1]


def test_classification_report_includes_operational_metrics() -> None:
    report = classification_report(
        labels=np.array([0, 0, 1, 1]),
        scores=np.array([0.1, 0.8, 0.7, 0.9]),
        threshold=0.65,
        latencies_ms=np.array([1, 2, 3, 10]),
    )
    assert report["precision"] == pytest.approx(2 / 3)
    assert report["recall"] == 1
    assert report["false_alerts_per_1000"] == 500
    assert report["p95_latency_ms"] > report["p50_latency_ms"]
    assert 0 <= report["pr_auc"] <= 1


def test_bootstrap_interval_is_deterministic_and_ordered() -> None:
    labels = np.array([0, 0, 1, 1, 1, 0])
    predictions = np.array([0, 1, 1, 1, 0, 0])
    first = bootstrap_f1_interval(labels, predictions, samples=100, random_state=3)
    second = bootstrap_f1_interval(labels, predictions, samples=100, random_state=3)
    assert first == second
    assert first[0] <= first[1] <= first[2]

