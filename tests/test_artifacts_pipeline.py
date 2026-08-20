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


def test_hybrid_detector_fuses_transformer_next_event_signals() -> None:
    train, validation = train_and_validation()
    train_signals = np.asarray(
        [[0.1, 1.0, 0.0, 0.2] for _ in train], dtype=float
    )
    validation_signals = np.asarray(
        [
            [0.1, 1.0, 0.0, 0.2],
            [0.2, 1.0, 0.0, 0.3],
            [4.0, 7.0, 1.0, 2.0],
            [5.0, 8.0, 1.0, 2.2],
        ],
        dtype=float,
    )
    detector = HybridDetector(random_state=7).fit(
        train,
        validation,
        train_transformer_signals=train_signals,
        validation_transformer_signals=validation_signals,
    )

    results = detector.score(validation, transformer_signals=validation_signals)

    assert set(results[0].component_scores) == {
        "rarity",
        "pca",
        "isolation_forest",
        "qwen_nll",
        "qwen_rank",
        "qwen_top_k_miss",
        "qwen_entropy",
    }
    assert detector.uses_transformer is True
    with pytest.raises(ValueError, match="transformer signals are required"):
        detector.score(validation)


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


def test_transformer_artifact_snapshots_adapter_inside_environment_package(
    tmp_path: Path,
) -> None:
    train, validation = train_and_validation()
    adapter_source = tmp_path / "trained-adapter"
    adapter_source.mkdir()
    (adapter_source / "adapter_model.safetensors").write_bytes(b"adapter-weights")
    (adapter_source / "logsentinel_adapter.json").write_text(
        '{"schema_version": 1, "base_model": "Qwen/Qwen2.5-1.5B", '
        '"codec": {"event_ids": ["E1"], "tokens": ["<EVT_000000>"]}}',
        encoding="utf-8",
    )
    signals_train = np.ones((len(train), 4), dtype=float)
    signals_validation = np.asarray(
        [[1, 1, 0, 1], [1, 1, 0, 1], [5, 5, 1, 2], [6, 6, 1, 2]],
        dtype=float,
    )
    detector = HybridDetector().fit(
        train,
        validation,
        train_transformer_signals=signals_train,
        validation_transformer_signals=signals_validation,
    )
    artifact = EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=DatasetName.HDFS,
            version="with-qwen",
            threshold=detector.threshold or 0.5,
            split_id="adapter-split",
            model_kind="hybrid-transformer",
            adapter_version="adapter-v1",
        ),
        detector=detector,
        adapter_path=adapter_source,
    )

    store = ArtifactStore(tmp_path / "artifacts")
    target = store.save(artifact)
    loaded = store.load(DatasetName.HDFS, "with-qwen")

    assert loaded.adapter_path == target / "adapter"
    assert (loaded.adapter_path / "adapter_model.safetensors").read_bytes() == b"adapter-weights"
    assert loaded.adapter_path.is_relative_to(tmp_path / "artifacts")


def test_transformer_artifact_detects_adapter_corruption(tmp_path: Path) -> None:
    train, validation = train_and_validation()
    adapter_source = tmp_path / "adapter"
    adapter_source.mkdir()
    (adapter_source / "logsentinel_adapter.json").write_text("{}", encoding="utf-8")
    artifact = EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=DatasetName.BGL,
            version="qwen-v1",
            threshold=0.5,
            split_id="split",
            model_kind="hybrid-transformer",
            adapter_version="adapter-v1",
        ),
        detector=HybridDetector().fit(
            train,
            validation,
            train_transformer_signals=np.ones((len(train), 4)),
            validation_transformer_signals=np.ones((len(validation), 4)),
        ),
        adapter_path=adapter_source,
    )
    store = ArtifactStore(tmp_path / "artifacts")
    target = store.save(artifact)
    (target / "adapter" / "logsentinel_adapter.json").write_text(
        "corrupted", encoding="utf-8"
    )

    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        store.load(DatasetName.BGL, "qwen-v1")


def test_artifact_rejects_adapter_detector_mode_mismatch(tmp_path: Path) -> None:
    train, validation = train_and_validation()
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    artifact = EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=DatasetName.HDFS,
            version="mismatch",
            threshold=0.5,
            split_id="split",
            model_kind="hybrid-transformer",
            adapter_version="v1",
        ),
        detector=HybridDetector().fit(train, validation),
        adapter_path=adapter,
    )

    with pytest.raises(ValueError, match="detector mode"):
        ArtifactStore(tmp_path / "artifacts").save(artifact)
