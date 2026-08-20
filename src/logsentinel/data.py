from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import UTC, datetime
from itertools import islice
from typing import Any

from logsentinel.privacy import Redactor, stable_hash
from logsentinel.schemas import DatasetName, LogEvent

DATASET_REPOSITORIES = {
    DatasetName.HDFS: "logfit-project/HDFS_v1",
    DatasetName.BGL: "logfit-project/BGL",
}


class DatasetAdapter:
    def __init__(self, dataset: DatasetName, *, redactor: Redactor | None = None) -> None:
        self.dataset = DatasetName(dataset)
        self.redactor = redactor or Redactor()

    def normalize(self, record: Mapping[str, Any]) -> LogEvent:
        if self.dataset is DatasetName.HDFS:
            return self._normalize_hdfs(record)
        return self._normalize_bgl(record)

    def _normalize_hdfs(self, record: Mapping[str, Any]) -> LogEvent:
        block_id = str(record.get("block_id") or "").strip()
        if not block_id:
            raise ValueError("HDFS record is missing block_id")
        date = str(record.get("date") or "").zfill(6)
        time = str(record.get("time") or "").zfill(6)
        try:
            timestamp = datetime.strptime(date + time, "%y%m%d%H%M%S").replace(tzinfo=UTC)
        except ValueError as exc:
            raise ValueError(f"invalid HDFS date/time: {date} {time}") from exc
        component = str(record.get("component") or "unknown")
        host = str(record.get("host") or component)
        return LogEvent(
            timestamp=timestamp,
            dataset=self.dataset,
            source=component,
            host_hash=stable_hash(host, salt="host"),
            severity=str(record.get("level") or "UNKNOWN").upper(),
            message=self.redactor.redact(str(record.get("content") or "<EMPTY>")),
            ground_truth_label=_binary_label(record.get("anomaly", 0)),
            group_hash=stable_hash(block_id, salt="group"),
        )

    def _normalize_bgl(self, record: Mapping[str, Any]) -> LogEvent:
        try:
            timestamp = datetime.fromtimestamp(int(record["timestamp"]), tz=UTC)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            raise ValueError("invalid or missing BGL timestamp") from exc
        component = str(record.get("component") or record.get("type") or "unknown")
        host = str(record.get("node") or record.get("node_repeat") or "unknown")
        return LogEvent(
            timestamp=timestamp,
            dataset=self.dataset,
            source=component,
            host_hash=stable_hash(host, salt="host"),
            severity=str(record.get("level") or "UNKNOWN").upper(),
            message=self.redactor.redact(str(record.get("content") or "<EMPTY>")),
            ground_truth_label=_binary_label(record.get("anomaly", 0)),
        )


def _binary_label(value: object) -> int:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"0", "false", "normal", "-", ""}:
            return 0
        if normalized in {"1", "true", "anomaly", "abnormal"}:
            return 1
    integer = int(value)
    if integer not in (0, 1):
        raise ValueError(f"expected a binary anomaly label, got {value!r}")
    return integer


def iter_public_records(
    dataset: DatasetName,
    *,
    limit: int | None = None,
    loader: Callable[..., Iterable[Mapping[str, Any]]] | None = None,
) -> Iterator[LogEvent]:
    dataset = DatasetName(dataset)
    if limit is not None and limit < 0:
        raise ValueError("limit cannot be negative")
    if loader is None:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError(
                "dataset streaming requires the 'data' extra: pip install 'logsentinel[data]'"
            ) from exc
        loader = load_dataset
    records = loader(DATASET_REPOSITORIES[dataset], split="train", streaming=True)
    selected = islice(records, limit) if limit is not None else records
    adapter = DatasetAdapter(dataset)
    for record in selected:
        yield adapter.normalize(record)

