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

COMPONENT_NAMES = ("rarity", "pca", "isolation_forest")


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

    def fit(
        self,
        train: list[EncodedSequence],
        validation: list[EncodedSequence],
    ) -> HybridDetector:
        if not train or not validation:
            raise ValueError("hybrid training requires non-empty train and validation sequences")
        if any(row.label != 0 for row in train):
            raise ValueError("hybrid base detectors must be fitted on normal training sequences")
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
        train_components = self._component_matrix(train)
        self._normal_mean = np.mean(train_components, axis=0)
        standard_deviation = np.std(train_components, axis=0)
        self._normal_std = np.where(standard_deviation > 1e-12, standard_deviation, 1.0)
        validation_components = self._component_matrix(validation)
        labels = np.asarray([row.label for row in validation], dtype=int)
        if len(np.unique(labels)) == 2:
            self.fusion = FusionCalibrator(feature_names=COMPONENT_NAMES).fit(
                validation_components, labels
            )
            fused = self.fusion.score(validation_components)
            self.threshold = select_f1_threshold(labels, fused)
        else:
            normal_scores = self._normal_only_score(validation_components)
            self.normal_calibrator = NormalOnlyCalibrator().fit(normal_scores)
            self.threshold = self.normal_calibrator.threshold
        return self

    def score(self, sequences: list[EncodedSequence]) -> list[SequenceScore]:
        if self.threshold is None:
            raise RuntimeError("hybrid detector has not been fitted")
        components = self._component_matrix(sequences)
        if self.fusion is not None:
            anomaly_scores = self.fusion.score(components)
        else:
            anomaly_scores = self._normal_only_score(components)
        results = []
        for index, row in enumerate(sequences):
            values = dict(zip(COMPONENT_NAMES, components[index], strict=True))
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

    def _component_matrix(self, sequences: list[EncodedSequence]) -> np.ndarray:
        return np.column_stack(
            [
                self.rarity.score(sequences),
                self.pca.score(sequences),
                self.isolation_forest.score(sequences),
            ]
        )

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
