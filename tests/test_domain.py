from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from logsentinel.parsing import DeterministicTemplateMiner
from logsentinel.privacy import Redactor, stable_hash
from logsentinel.schemas import DatasetName, LogEvent
from logsentinel.sequencing import build_bgl_windows, build_hdfs_sequences
from logsentinel.splits import temporal_split


def event(
    *,
    second: int,
    message: str = "Received block blk_-123 from 10.1.2.3",
    label: int = 0,
    group: str | None = "blk_-123",
) -> LogEvent:
    return LogEvent(
        timestamp=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(seconds=second),
        dataset=DatasetName.HDFS,
        source="DataNode",
        host_hash=stable_hash("node-1"),
        severity="INFO",
        message=message,
        ground_truth_label=label,
        group_hash=stable_hash(group) if group else None,
    )


def test_log_event_rejects_naive_timestamp_and_non_binary_label() -> None:
    with pytest.raises(ValidationError):
        LogEvent(
            timestamp=datetime(2025, 1, 1),
            dataset="hdfs",
            source="x",
            host_hash="abc",
            severity="INFO",
            message="ok",
            ground_truth_label=2,
        )


def test_redactor_replaces_sensitive_values_before_template_mining() -> None:
    raw = "user alice@example.com token=secret-ABC123 connected from 10.1.2.3 to /srv/acme/file"
    normalized = Redactor().redact(raw)
    assert "alice@example.com" not in normalized
    assert "secret-ABC123" not in normalized
    assert "10.1.2.3" not in normalized
    assert "/srv/acme/file" not in normalized
    assert {"<EMAIL>", "<TOKEN>", "<IP>", "<PATH>"} <= set(normalized.split())


def test_stable_hash_is_deterministic_and_salted() -> None:
    assert stable_hash("node-1", salt="a") == stable_hash("node-1", salt="a")
    assert stable_hash("node-1", salt="a") != stable_hash("node-1", salt="b")
    assert "node-1" not in stable_hash("node-1")


def test_template_ids_are_deterministic_and_unknowns_do_not_mutate_frozen_miner() -> None:
    miner = DeterministicTemplateMiner()
    known = miner.fit_transform(["connected from <IP>", "connected from <IP>"])
    assert known[0].event_id == known[1].event_id
    miner.freeze()
    size = miner.vocabulary_size
    unknown = miner.transform("disk exploded with code 7")
    assert unknown.event_id == "<UNK>"
    assert miner.vocabulary_size == size


def test_hdfs_sequences_group_by_hash_and_aggregate_labels() -> None:
    rows = [event(second=3, label=1), event(second=1), event(second=2)]
    sequences = build_hdfs_sequences(rows)
    assert len(sequences) == 1
    assert [item.timestamp.second for item in sequences[0].events] == [1, 2, 3]
    assert sequences[0].label == 1


def test_bgl_windows_are_non_overlapping_and_label_if_any_event_is_anomalous() -> None:
    rows = [
        event(second=1, group=None),
        event(second=59, label=1, group=None),
        event(second=60, group=None),
    ]
    windows = build_bgl_windows(rows, window_seconds=60)
    assert [len(window.events) for window in windows] == [2, 1]
    assert [window.label for window in windows] == [1, 0]


def test_temporal_split_is_deterministic_disjoint_and_training_can_be_normal_only() -> None:
    sequences = []
    for index in range(10):
        item = event(second=index, label=int(index == 2), group=f"blk_{index}")
        sequences.extend(build_hdfs_sequences([item]))
    split = temporal_split(sequences, train_fraction=0.6, validation_fraction=0.2)
    assert len(split.train) == 5  # anomalous sequence is excluded from the first six
    assert len(split.validation) == 2
    assert len(split.test) == 2
    ids = [{s.sequence_id for s in part} for part in (split.train, split.validation, split.test)]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
    assert all(sequence.label == 0 for sequence in split.train)

