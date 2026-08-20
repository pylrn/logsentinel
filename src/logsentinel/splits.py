from __future__ import annotations

from dataclasses import dataclass

from logsentinel.schemas import EventSequence


@dataclass(frozen=True)
class DatasetSplit:
    train: tuple[EventSequence, ...]
    validation: tuple[EventSequence, ...]
    test: tuple[EventSequence, ...]


def temporal_split(
    sequences: list[EventSequence],
    *,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
    normal_train_only: bool = True,
) -> DatasetSplit:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between zero and one")
    if not 0 < validation_fraction < 1 or train_fraction + validation_fraction >= 1:
        raise ValueError("validation fraction must leave a non-empty test fraction")
    ordered = sorted(sequences, key=lambda item: (item.started_at, item.sequence_id))
    train_end = int(len(ordered) * train_fraction)
    validation_end = int(len(ordered) * (train_fraction + validation_fraction))
    raw_train = ordered[:train_end]
    if normal_train_only:
        raw_train = [item for item in raw_train if item.label == 0]
    split = DatasetSplit(
        train=tuple(raw_train),
        validation=tuple(ordered[train_end:validation_end]),
        test=tuple(ordered[validation_end:]),
    )
    _assert_disjoint(split)
    return split


def _assert_disjoint(split: DatasetSplit) -> None:
    identifiers = [
        {item.sequence_id for item in partition}
        for partition in (split.train, split.validation, split.test)
    ]
    if identifiers[0] & identifiers[1] or identifiers[0] & identifiers[2]:
        raise ValueError("train split overlaps validation or test")
    if identifiers[1] & identifiers[2]:
        raise ValueError("validation split overlaps test")

