from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from logsentinel.artifacts import (
    ArtifactMetadata,
    ArtifactStore,
    EnvironmentArtifact,
)
from logsentinel.detection import EncodedSequence
from logsentinel.neural import transformer_signal_matrix
from logsentinel.parsing import DeterministicTemplateMiner
from logsentinel.pipeline import HybridDetector
from logsentinel.privacy import Redactor, stable_hash
from logsentinel.schemas import DatasetName, EventSequence, LogEvent
from logsentinel.sequencing import build_bgl_windows, build_hdfs_sequences
from logsentinel.splits import temporal_split


@dataclass(frozen=True)
class PreparedDataset:
    dataset: DatasetName
    split_id: str
    train: tuple[EncodedSequence, ...]
    validation: tuple[EncodedSequence, ...]
    test: tuple[EncodedSequence, ...]
    parser: DeterministicTemplateMiner

    def save(self, path: Path | str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset": self.dataset.value,
            "split_id": self.split_id,
            "parser": self.parser.to_dict(),
            "train": [_encoded_to_dict(item) for item in self.train],
            "validation": [_encoded_to_dict(item) for item in self.validation],
            "test": [_encoded_to_dict(item) for item in self.test],
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: Path | str) -> PreparedDataset:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            dataset=DatasetName(payload["dataset"]),
            split_id=str(payload["split_id"]),
            train=tuple(_encoded_from_dict(item) for item in payload["train"]),
            validation=tuple(_encoded_from_dict(item) for item in payload["validation"]),
            test=tuple(_encoded_from_dict(item) for item in payload["test"]),
            parser=DeterministicTemplateMiner.from_dict(payload["parser"]),
        )


def prepare_events(
    events: list[LogEvent],
    *,
    dataset: DatasetName,
) -> PreparedDataset:
    dataset = DatasetName(dataset)
    if not events:
        raise ValueError("cannot prepare an empty event collection")
    if any(item.dataset is not dataset for item in events):
        raise ValueError("all events must belong to the selected dataset")
    redactor = Redactor()
    safe_events = [
        item.model_copy(update={"message": redactor.redact(item.message)}) for item in events
    ]
    raw_sequences = (
        build_hdfs_sequences(safe_events)
        if dataset is DatasetName.HDFS
        else build_bgl_windows(safe_events)
    )
    split = temporal_split(raw_sequences)
    if not split.train or not split.validation or not split.test:
        raise ValueError("dataset is too small for non-empty temporal partitions")
    parser = DeterministicTemplateMiner()
    train = tuple(_encode_sequence(item, parser, fit=True) for item in split.train)
    parser.freeze()
    validation = tuple(_encode_sequence(item, parser, fit=False) for item in split.validation)
    test = tuple(_encode_sequence(item, parser, fit=False) for item in split.test)
    split_id = stable_hash(
        "|".join(
            [
                dataset.value,
                "60-20-20",
                *(item.sequence_id for item in (*train, *validation, *test)),
            ]
        ),
        salt="split",
    )
    return PreparedDataset(
        dataset=dataset,
        split_id=split_id,
        train=train,
        validation=validation,
        test=test,
        parser=parser,
    )


def train_hybrid_artifact(
    prepared: PreparedDataset,
    *,
    version: str,
    artifact_root: Path | str,
    random_state: int = 42,
    transformer_scorer: Any | None = None,
    adapter_path: Path | str | None = None,
) -> EnvironmentArtifact:
    if (transformer_scorer is None) != (adapter_path is None):
        raise ValueError("transformer scorer and adapter path must be provided together")
    train_signals = validation_signals = None
    if transformer_scorer is not None:
        train_signals = transformer_signal_matrix(
            transformer_scorer.score(list(prepared.train))
        )
        validation_signals = transformer_signal_matrix(
            transformer_scorer.score(list(prepared.validation))
        )
    detector = HybridDetector(random_state=random_state).fit(
        list(prepared.train),
        list(prepared.validation),
        train_transformer_signals=train_signals,
        validation_transformer_signals=validation_signals,
    )
    selected_adapter = Path(adapter_path).resolve() if adapter_path is not None else None
    artifact = EnvironmentArtifact(
        metadata=ArtifactMetadata(
            environment=prepared.dataset,
            version=version,
            threshold=detector.threshold or 0.0,
            split_id=prepared.split_id,
            model_kind=(
                "hybrid-transformer" if transformer_scorer is not None else "hybrid-statistical"
            ),
            adapter_version=selected_adapter.name if selected_adapter is not None else None,
        ),
        detector=detector,
        parser=prepared.parser,
        adapter_path=selected_adapter,
    )
    store = ArtifactStore(artifact_root)
    store.save(artifact)
    return store.load(prepared.dataset, version)


def sample_events(dataset: DatasetName, *, count: int = 240) -> list[LogEvent]:
    dataset = DatasetName(dataset)
    if count < 20:
        raise ValueError("sample generation requires at least 20 events")
    start = datetime(2025, 1, 1, tzinfo=UTC)
    normal_messages = (
        "block verification succeeded",
        "received block from <IP>",
        "block committed to storage",
    )
    rows = []
    for index in range(count):
        anomalous = index % 17 == 0
        timestamp = (
            start + timedelta(seconds=index)
            if dataset is DatasetName.HDFS
            else start + timedelta(seconds=(index // 5) * 60 + (index % 5))
        )
        rows.append(
            LogEvent(
                timestamp=timestamp,
                dataset=dataset,
                source="DataNode" if dataset is DatasetName.HDFS else "KERNEL",
                host_hash=stable_hash(f"node-{index % 8}", salt="sample-host"),
                severity="ERROR" if anomalous else "INFO",
                message=(
                    "replica verification failed repeatedly"
                    if anomalous
                    else normal_messages[index % len(normal_messages)]
                ),
                ground_truth_label=int(anomalous),
                group_hash=(
                    stable_hash(f"block-{index // 4}", salt="sample-group")
                    if dataset is DatasetName.HDFS
                    else None
                ),
            )
        )
    return rows


def _encode_sequence(
    sequence: EventSequence,
    parser: DeterministicTemplateMiner,
    *,
    fit: bool,
) -> EncodedSequence:
    messages = [item.message for item in sequence.events]
    matches = (
        parser.fit_transform(messages)
        if fit
        else [parser.transform(item) for item in messages]
    )
    return EncodedSequence(
        sequence_id=sequence.sequence_id,
        event_ids=tuple(item.event_id for item in matches),
        label=sequence.label,
        started_at=sequence.started_at,
        ended_at=sequence.ended_at,
    )


def _encoded_to_dict(item: EncodedSequence) -> dict[str, object]:
    payload = asdict(item)
    payload["event_ids"] = list(item.event_ids)
    payload["started_at"] = item.started_at.isoformat()
    payload["ended_at"] = item.ended_at.isoformat()
    return payload


def _encoded_from_dict(payload: dict[str, object]) -> EncodedSequence:
    return EncodedSequence(
        sequence_id=str(payload["sequence_id"]),
        event_ids=tuple(str(item) for item in payload["event_ids"]),
        label=int(payload["label"]),
        started_at=datetime.fromisoformat(str(payload["started_at"])),
        ended_at=datetime.fromisoformat(str(payload["ended_at"])),
    )
