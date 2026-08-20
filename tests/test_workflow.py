from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from logsentinel.neural import TransformerSequenceScore
from logsentinel.schemas import DatasetName, LogEvent
from logsentinel.sequencing import build_bgl_windows, build_hdfs_sequences
from logsentinel.workflow import (
    PreparedDataset,
    prepare_events,
    sample_events,
    train_hybrid_artifact,
)


def test_prepare_events_fits_parser_on_training_only_and_persists_without_raw_secrets(
    tmp_path: Path,
) -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    events = []
    for index in range(10):
        message = "normal event" if index < 6 else f"novel test token=secret-{index}"
        events.append(
            LogEvent(
                timestamp=start + timedelta(minutes=index),
                dataset=DatasetName.HDFS,
                source="DataNode",
                host_hash="host-hash",
                severity="WARN" if index >= 8 else "INFO",
                message=message,
                ground_truth_label=int(index in {6, 8}),
                group_hash=f"group-{index}",
            )
        )
    prepared = prepare_events(events, dataset=DatasetName.HDFS)
    assert prepared.parser.vocabulary_size == 1
    assert prepared.test[-1].event_ids == ("<UNK>",)
    path = tmp_path / "prepared.json"
    prepared.save(path)
    assert "secret-9" not in path.read_text(encoding="utf-8")
    loaded = PreparedDataset.load(path)
    assert loaded.split_id == prepared.split_id
    assert loaded.test == prepared.test


def test_sample_events_cover_normal_and_anomalous_sequences_for_both_datasets() -> None:
    for dataset in DatasetName:
        events = sample_events(dataset, count=120)
        assert events
        assert {item.ground_truth_label for item in events} == {0, 1}
        assert all(item.dataset is dataset for item in events)
    assert len(build_hdfs_sequences(sample_events(DatasetName.HDFS, count=120))) == 30
    assert len(build_bgl_windows(sample_events(DatasetName.BGL, count=120))) == 24


def test_sample_workflow_trains_versioned_artifact(tmp_path: Path) -> None:
    prepared = prepare_events(sample_events(DatasetName.HDFS, count=180), dataset=DatasetName.HDFS)
    artifact = train_hybrid_artifact(
        prepared,
        version="sample-v1",
        artifact_root=tmp_path,
    )
    assert artifact.metadata.environment is DatasetName.HDFS
    assert artifact.metadata.version == "sample-v1"
    assert (tmp_path / "hdfs" / "sample-v1" / "integrity.json").is_file()


def test_workflow_calibrates_and_packages_transformer_hybrid(tmp_path: Path) -> None:
    prepared = prepare_events(
        sample_events(DatasetName.HDFS, count=180), dataset=DatasetName.HDFS
    )
    adapter = tmp_path / "adapter-source"
    adapter.mkdir()
    (adapter / "logsentinel_adapter.json").write_text("{}", encoding="utf-8")

    class FakeScorer:
        def score(self, sequences):
            return [
                TransformerSequenceScore(
                    negative_log_likelihood=4.0 if row.label else 0.2,
                    mean_rank=5.0 if row.label else 1.0,
                    top_k_miss_rate=float(row.label),
                    entropy=2.0 if row.label else 0.3,
                    expected_event_ids=(row.event_ids[0],),
                )
                for row in sequences
            ]

    artifact = train_hybrid_artifact(
        prepared,
        version="qwen-v1",
        artifact_root=tmp_path / "artifacts",
        transformer_scorer=FakeScorer(),
        adapter_path=adapter,
    )

    assert artifact.detector.uses_transformer is True
    assert artifact.metadata.model_kind == "hybrid-transformer"
    assert artifact.metadata.adapter_version == "adapter-source"
    assert artifact.adapter_path == (
        tmp_path / "artifacts" / "hdfs" / "qwen-v1" / "adapter"
    )
    assert (
        tmp_path
        / "artifacts"
        / "hdfs"
        / "qwen-v1"
        / "adapter"
        / "logsentinel_adapter.json"
    ).is_file()
