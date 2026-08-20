from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import pairwise

import numpy as np
from sklearn.metrics import f1_score

from logsentinel.detection import (
    EncodedSequence,
    FusionCalibrator,
    IsolationForestDetector,
    NormalOnlyCalibrator,
    PCADetector,
    RarityDetector,
)

STATISTICAL_COMPONENT_NAMES = ("rarity", "pca", "isolation_forest")
TRANSFORMER_COMPONENT_NAMES = (
    "qwen_nll",
    "qwen_rank",
    "qwen_top_k_miss",
    "qwen_entropy",
)


@dataclass(frozen=True)
class SequenceScore:
    sequence_id: str
    anomaly_score: float
    is_anomaly: bool
    component_scores: dict[str, float]
    contributions: dict[str, float]


class HybridDetector:
    def __init__(self, *, random_state: int = 42) -> None:
        self.rarity = RarityDetector()
        self.pca = PCADetector()
        self.isolation_forest = IsolationForestDetector(random_state=random_state)
        self.fusion: FusionCalibrator | None = None
        self.normal_calibrator: NormalOnlyCalibrator | None = None
        self.threshold: float | None = None
        self._normal_mean: np.ndarray | None = None
        self._normal_std: np.ndarray | None = None
        self._transitions: dict[str, Counter[str]] = {}
        self._global_next: Counter[str] = Counter()
        self.component_names = STATISTICAL_COMPONENT_NAMES

    @property
    def uses_transformer(self) -> bool:
        return self.component_names != STATISTICAL_COMPONENT_NAMES

    def fit(
        self,
        train: list[EncodedSequence],
        validation: list[EncodedSequence],
        *,
        train_transformer_signals: np.ndarray | None = None,
        validation_transformer_signals: np.ndarray | None = None,
    ) -> HybridDetector:
        if not train or not validation:
            raise ValueError("hybrid training requires non-empty train and validation sequences")
        if any(row.label != 0 for row in train):
            raise ValueError("hybrid base detectors must be fitted on normal training sequences")
        if (train_transformer_signals is None) != (validation_transformer_signals is None):
            raise ValueError("train and validation transformer signals must be provided together")
        if train_transformer_signals is not None:
            _validate_transformer_signals(train_transformer_signals, len(train))
            _validate_transformer_signals(validation_transformer_signals, len(validation))
            self.component_names = (
                *STATISTICAL_COMPONENT_NAMES,
                *TRANSFORMER_COMPONENT_NAMES,
            )
        else:
            self.component_names = STATISTICAL_COMPONENT_NAMES
        self.rarity.fit(train)
        self.pca.fit(train)
        self.isolation_forest.fit(train)
        transitions: dict[str, Counter[str]] = defaultdict(Counter)
        global_next: Counter[str] = Counter()
        for row in train:
            for current, following in pairwise(row.event_ids):
                transitions[current][following] += 1
                global_next[following] += 1
        self._transitions = dict(transitions)
        self._global_next = global_next
        train_components = self._component_matrix(train, train_transformer_signals)
        self._normal_mean = np.mean(train_components, axis=0)
        standard_deviation = np.std(train_components, axis=0)
        self._normal_std = np.where(standard_deviation > 1e-12, standard_deviation, 1.0)
        validation_components = self._component_matrix(
            validation, validation_transformer_signals
        )
        labels = np.asarray([row.label for row in validation], dtype=int)
        if len(np.unique(labels)) == 2:
            self.fusion = FusionCalibrator(feature_names=self.component_names).fit(
                validation_components, labels
            )
            fused = self.fusion.score(validation_components)
            self.threshold = select_f1_threshold(labels, fused)
        else:
            normal_scores = self._normal_only_score(validation_components)
            self.normal_calibrator = NormalOnlyCalibrator().fit(normal_scores)
            self.threshold = self.normal_calibrator.threshold
        return self

    def score(
        self,
        sequences: list[EncodedSequence],
        *,
        transformer_signals: np.ndarray | None = None,
    ) -> list[SequenceScore]:
        if self.threshold is None:
            raise RuntimeError("hybrid detector has not been fitted")
        if self.uses_transformer and transformer_signals is None:
            raise ValueError("transformer signals are required by this hybrid detector")
        if not self.uses_transformer and transformer_signals is not None:
            raise ValueError("this detector was calibrated without transformer signals")
        components = self._component_matrix(sequences, transformer_signals)
        if self.fusion is not None:
            anomaly_scores = self.fusion.score(components)
        else:
            anomaly_scores = self._normal_only_score(components)
        results = []
        for index, row in enumerate(sequences):
            values = dict(zip(self.component_names, components[index], strict=True))
            if self.fusion is not None:
                contributions = self.fusion.explain(components[index])
            else:
                contributions = values.copy()
            results.append(
                SequenceScore(
                    sequence_id=row.sequence_id,
                    anomaly_score=float(anomaly_scores[index]),
                    is_anomaly=bool(anomaly_scores[index] >= self.threshold),
                    component_scores={name: float(value) for name, value in values.items()},
                    contributions={
                        name: float(value) for name, value in contributions.items()
                    },
                )
            )
        return results

    def expected_next(self, context: tuple[str, ...], *, top_k: int = 3) -> tuple[str, ...]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not context:
            candidates = self._global_next
        else:
            candidates = self._transitions.get(context[-1], self._global_next)
        return tuple(event for event, _ in candidates.most_common(top_k))

    def _component_matrix(
        self,
        sequences: list[EncodedSequence],
        transformer_signals: np.ndarray | None = None,
    ) -> np.ndarray:
        columns = [
            self.rarity.score(sequences),
            self.pca.score(sequences),
            self.isolation_forest.score(sequences),
        ]
        if transformer_signals is not None:
            values = _validate_transformer_signals(transformer_signals, len(sequences))
            columns.extend(values[:, index] for index in range(values.shape[1]))
        return np.column_stack(columns)

    def _normal_only_score(self, components: np.ndarray) -> np.ndarray:
        if self._normal_mean is None or self._normal_std is None:
            raise RuntimeError("hybrid detector has not been fitted")
        standardized = (components - self._normal_mean) / self._normal_std
        return np.mean(np.maximum(standardized, 0), axis=1)


def select_f1_threshold(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    if len(labels) != len(scores) or len(labels) == 0:
        raise ValueError("labels and scores must be non-empty and equally sized")
    best_threshold = float(scores[0])
    best_f1 = -1.0
    for threshold in np.unique(scores):
        predictions = (scores >= threshold).astype(int)
        candidate = f1_score(labels, predictions, zero_division=0)
        if candidate > best_f1 or (candidate == best_f1 and threshold > best_threshold):
            best_f1 = float(candidate)
            best_threshold = float(threshold)
    return best_threshold


def _validate_transformer_signals(
    signals: np.ndarray | None, expected_rows: int
) -> np.ndarray:
    values = np.asarray(signals, dtype=float)
    if values.shape != (expected_rows, len(TRANSFORMER_COMPONENT_NAMES)):
        raise ValueError(
            "transformer signals must have shape "
            f"({expected_rows}, {len(TRANSFORMER_COMPONENT_NAMES)})"
        )
    if not np.isfinite(values).all():
        raise ValueError("transformer signals must be finite")
    return values
