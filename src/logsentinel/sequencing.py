from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from logsentinel.privacy import stable_hash
from logsentinel.schemas import DatasetName, EventSequence, LogEvent


def _make_sequence(sequence_id: str, events: list[LogEvent]) -> EventSequence:
    ordered = tuple(sorted(events, key=lambda item: item.timestamp))
    return EventSequence(
        sequence_id=sequence_id,
        dataset=ordered[0].dataset,
        started_at=ordered[0].timestamp,
        ended_at=ordered[-1].timestamp,
        events=ordered,
        label=max(item.ground_truth_label for item in ordered),
    )


def build_hdfs_sequences(events: list[LogEvent]) -> list[EventSequence]:
    grouped: dict[str, list[LogEvent]] = defaultdict(list)
    for item in events:
        if not item.group_hash:
            raise ValueError("HDFS events require a hashed block/group identifier")
        grouped[item.group_hash].append(item)
    sequences = [_make_sequence(f"hdfs:{key}", rows) for key, rows in grouped.items()]
    return sorted(sequences, key=lambda item: (item.started_at, item.sequence_id))


def build_bgl_windows(
    events: list[LogEvent], *, window_seconds: int = 60
) -> list[EventSequence]:
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    grouped: dict[datetime, list[LogEvent]] = defaultdict(list)
    for item in events:
        epoch = int(item.timestamp.timestamp())
        start_epoch = epoch - (epoch % window_seconds)
        start = datetime.fromtimestamp(start_epoch, tz=item.timestamp.tzinfo)
        grouped[start].append(item)
    sequences = []
    for start, rows in grouped.items():
        sequence = _make_sequence(
            f"bgl:{stable_hash(start.isoformat(), salt='window')}", rows
        )
        sequences.append(sequence.model_copy(update={"dataset": DatasetName.BGL}))
    return sorted(sequences, key=lambda item: item.started_at)

