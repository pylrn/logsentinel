from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from logsentinel.artifacts import (
    ArtifactIntegrityError,
    ArtifactMetadata,
    ArtifactStore,
    EnvironmentArtifact,
)
from logsentinel.detection import EncodedSequence
from logsentinel.pipeline import HybridDetector, select_f1_threshold
from logsentinel.schemas import DatasetName


def seq(index: int, events: tuple[str, ...], label: int = 0) -> EncodedSequence:
    start = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=index)
    return EncodedSequence(
        sequence_id=f"s-{index}",
        event_ids=events,
        label=label,
        started_at=start,
        ended_at=start + timedelta(seconds=max(len(events), 1)),
    )


def train_and_validation():
    train = [
        seq(0, ("E1", "E2", "E1")),
        seq(1, ("E1", "E2")),
        seq(2, ("E1", "E3")),
        seq(3, ("E1", "E2", "E3")),
        seq(4, ("E1", "E2")),
        seq(5, ("E1", "E3", "E2")),
    ]
    validation = [
        seq(10, ("E1", "E2"), 0),
        seq(11, ("E1", "E3"), 0),
        seq(12, ("X", "Y", "Z"), 1),
        seq(13, ("X", "X", "X", "X"), 1),
    ]
    return train, validation


def test_hybrid_detector_returns_interpretable_component_scores() -> None:
    train, validation = train_and_validation()
    detector = HybridDetector(random_state=7).fit(train, validation)
    results = detector.score(validation)
    assert len(results) == len(validation)
    assert all(0 <= result.anomaly_score <= 1 for result in results)
    assert set(results[0].component_scores) == {"rarity", "pca", "isolation_forest"}
    assert results[-1].anomaly_score > results[0].anomaly_score
    assert detector.threshold is not None
    assert detector.expected_next(("E1",), top_k=2)[0] in {"E2", "E3"}


def test_select_f1_threshold_is_deterministic() -> None:
    labels = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.4, 0.6, 0.9])
    assert select_f1_threshold(labels, scores) == pytest.approx(0.6)


def test_artifact_store_round_trips_and_refuses_overwrite(tmp_path: Path) -> None:
    train, validation = train_and_validation()
    detector = HybridDetector(random_state=7).fit(train, validation)
    artifact = EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=DatasetName.HDFS,
            version="2026-08-20.test",
            threshold=detector.threshold or 0.5,
            split_id="split-abc",
        ),
        detector=detector,
    )
    store = ArtifactStore(tmp_path)
    path = store.save(artifact)
    loaded = store.load(DatasetName.HDFS, "2026-08-20.test")
    assert loaded.metadata == artifact.metadata
    original = [item.anomaly_score for item in detector.score(validation)]
    restored = [item.anomaly_score for item in loaded.detector.score(validation)]
    assert restored == pytest.approx(original)
    with pytest.raises(FileExistsError):
        store.save(artifact)
    assert path.name == "2026-08-20.test"


def test_artifact_integrity_check_detects_corruption(tmp_path: Path) -> None:
    train, validation = train_and_validation()
    detector = HybridDetector(random_state=7).fit(train, validation)
    artifact = EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=DatasetName.BGL,
            version="v1",
            threshold=detector.threshold or 0.5,
            split_id="split-bgl",
        ),
        detector=detector,
    )
    store = ArtifactStore(tmp_path)
    path = store.save(artifact)
    (path / "model.joblib").write_bytes(b"corrupted")
    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        store.load(DatasetName.BGL, "v1")


def test_artifact_lookup_cannot_cross_environment(tmp_path: Path) -> None:
    train, validation = train_and_validation()
    artifact = EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=DatasetName.HDFS,
            version="same-version",
            threshold=0.5,
            split_id="one",
        ),
        detector=HybridDetector().fit(train, validation),
    )
    store = ArtifactStore(tmp_path)
    store.save(artifact)
    with pytest.raises(FileNotFoundError):
        store.load(DatasetName.BGL, "same-version")
