from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class EncodedSequence:
    sequence_id: str
    event_ids: tuple[str, ...]
    label: int
    started_at: datetime
    ended_at: datetime

    @property
    def duration_seconds(self) -> float:
        return max((self.ended_at - self.started_at).total_seconds(), 1.0)


@dataclass(frozen=True)
class FeatureBatch:
    counts: np.ndarray
    signals: np.ndarray

    @property
    def combined(self) -> np.ndarray:
        return np.concatenate([self.counts, self.signals], axis=1)


class FeatureExtractor:
    signal_names = ("rarity", "unseen_rate", "length_z", "burst_z")

    def __init__(self) -> None:
        self.vocabulary: tuple[str, ...] = ()
        self._index: dict[str, int] = {}
        self._frequency: Counter[str] = Counter()
        self._total_events = 0
        self._length_mean = 0.0
        self._length_std = 1.0
        self._burst_mean = 0.0
        self._burst_std = 1.0
        self._fitted = False

    def fit(self, sequences: list[EncodedSequence]) -> FeatureExtractor:
        if not sequences:
            raise ValueError("cannot fit features on an empty sequence collection")
        self._frequency = Counter(event for row in sequences for event in row.event_ids)
        self.vocabulary = tuple(sorted(self._frequency))
        self._index = {event: index for index, event in enumerate(self.vocabulary)}
        self._total_events = sum(self._frequency.values())
        lengths = np.asarray([len(row.event_ids) for row in sequences], dtype=float)
        bursts = np.asarray(
            [len(row.event_ids) / row.duration_seconds for row in sequences], dtype=float
        )
        self._length_mean, self._length_std = _mean_and_safe_std(lengths)
        self._burst_mean, self._burst_std = _mean_and_safe_std(bursts)
        self._fitted = True
        return self

    def transform(self, sequences: list[EncodedSequence]) -> FeatureBatch:
        if not self._fitted:
            raise RuntimeError("feature extractor has not been fitted")
        counts = np.zeros((len(sequences), len(self.vocabulary)), dtype=float)
        signals = np.zeros((len(sequences), len(self.signal_names)), dtype=float)
        denominator = self._total_events + max(len(self.vocabulary), 1)
        for row_index, row in enumerate(sequences):
            unknown = 0
            surprise = []
            for event_id in row.event_ids:
                column = self._index.get(event_id)
                if column is None:
                    unknown += 1
                    probability = 1 / denominator
                else:
                    counts[row_index, column] += 1
                    probability = (self._frequency[event_id] + 1) / denominator
                surprise.append(-np.log(probability))
            length = len(row.event_ids)
            signals[row_index] = (
                float(np.mean(surprise)) if surprise else 0.0,
                unknown / max(length, 1),
                abs(length - self._length_mean) / self._length_std,
                abs(length / row.duration_seconds - self._burst_mean) / self._burst_std,
            )
        return FeatureBatch(counts=counts, signals=signals)


class RarityDetector:
    def __init__(self) -> None:
        self.extractor = FeatureExtractor()

    def fit(self, sequences: list[EncodedSequence]) -> RarityDetector:
        self.extractor.fit(sequences)
        return self

    def score(self, sequences: list[EncodedSequence]) -> np.ndarray:
        return self.extractor.transform(sequences).signals[:, 0]


class PCADetector:
    def __init__(self) -> None:
        self.extractor = FeatureExtractor()
        self.scaler = StandardScaler()
        self.model: PCA | None = None

    def fit(self, sequences: list[EncodedSequence]) -> PCADetector:
        matrix = self.extractor.fit(sequences).transform(sequences).counts
        scaled = self.scaler.fit_transform(matrix)
        components = max(1, min(scaled.shape[0] - 1, scaled.shape[1]))
        self.model = PCA(n_components=components, svd_solver="full").fit(scaled)
        return self

    def score(self, sequences: list[EncodedSequence]) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("PCA detector has not been fitted")
        scaled = self.scaler.transform(self.extractor.transform(sequences).counts)
        reconstructed = self.model.inverse_transform(self.model.transform(scaled))
        return np.mean(np.square(scaled - reconstructed), axis=1)


class IsolationForestDetector:
    def __init__(self, *, random_state: int = 42) -> None:
        self.extractor = FeatureExtractor()
        self.model = IsolationForest(
            n_estimators=200,
            contamination="auto",
            random_state=random_state,
            n_jobs=-1,
        )

    def fit(self, sequences: list[EncodedSequence]) -> IsolationForestDetector:
        matrix = self.extractor.fit(sequences).transform(sequences).combined
        self.model.fit(matrix)
        return self

    def score(self, sequences: list[EncodedSequence]) -> np.ndarray:
        matrix = self.extractor.transform(sequences).combined
        return -self.model.decision_function(matrix)


class FusionCalibrator:
    def __init__(self, *, feature_names: tuple[str, ...]) -> None:
        self.feature_names = feature_names
        self.scaler = StandardScaler()
        self.model = LogisticRegression(class_weight="balanced", random_state=42)
        self._fitted = False

    def fit(self, features: np.ndarray, labels: np.ndarray) -> FusionCalibrator:
        _validate_feature_matrix(features, self.feature_names)
        if len(np.unique(labels)) != 2:
            raise ValueError("fusion calibration requires both normal and anomalous labels")
        scaled = self.scaler.fit_transform(features)
        self.model.fit(scaled, labels)
        self._fitted = True
        return self

    def score(self, features: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("fusion calibrator has not been fitted")
        _validate_feature_matrix(features, self.feature_names)
        return self.model.predict_proba(self.scaler.transform(features))[:, 1]

    def explain(self, row: np.ndarray) -> dict[str, float]:
        if not self._fitted:
            raise RuntimeError("fusion calibrator has not been fitted")
        matrix = np.asarray(row, dtype=float).reshape(1, -1)
        _validate_feature_matrix(matrix, self.feature_names)
        contributions = self.scaler.transform(matrix)[0] * self.model.coef_[0]
        return dict(zip(self.feature_names, contributions, strict=True))


class NormalOnlyCalibrator:
    def __init__(self, *, quantile: float = 0.995) -> None:
        if not 0 < quantile < 1:
            raise ValueError("quantile must be between zero and one")
        self.quantile = quantile
        self.threshold: float | None = None

    def fit(self, normal_scores: np.ndarray) -> NormalOnlyCalibrator:
        if len(normal_scores) == 0:
            raise ValueError("normal-only calibration requires at least one score")
        self.threshold = float(np.quantile(normal_scores, self.quantile))
        return self

    def predict(self, scores: np.ndarray) -> np.ndarray:
        if self.threshold is None:
            raise RuntimeError("normal-only calibrator has not been fitted")
        return (np.asarray(scores) > self.threshold).astype(int)


def _mean_and_safe_std(values: np.ndarray) -> tuple[float, float]:
    standard_deviation = float(np.std(values))
    return float(np.mean(values)), standard_deviation if standard_deviation > 1e-12 else 1.0


def _validate_feature_matrix(matrix: np.ndarray, names: tuple[str, ...]) -> None:
    if matrix.ndim != 2 or matrix.shape[1] != len(names):
        raise ValueError(f"expected a feature matrix with {len(names)} columns")

