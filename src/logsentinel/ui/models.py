from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AppMode(StrEnum):
    LIVE = "live"
    DEMO = "demo"


class AnomalyTone(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NORMAL = "normal"


def score_tone(score: float) -> AnomalyTone:
    if score >= 0.8:
        return AnomalyTone.HIGH
    if score >= 0.5:
        return AnomalyTone.MEDIUM
    if score >= 0.3:
        return AnomalyTone.LOW
    return AnomalyTone.NORMAL


@dataclass(frozen=True)
class ModelStatus:
    name: str
    version: str
    model_kind: str
    status: str
    threshold: float
    events_indexed: int = 0
    vocabulary_size: int = 0


@dataclass(frozen=True)
class Incident:
    id: str
    time: str
    source: str
    score: float
    tone: AnomalyTone
    signal: str
    status: str
    environment: str
    raw_message_redacted: str
    template_id: str
    template_text: str
    context_sequence: list[str] = field(default_factory=list)
    expected_templates: list[str] = field(default_factory=list)
    contributions: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TimelinePoint:
    timestamp: str
    score: float
    tone: AnomalyTone
    incident_count: int = 1


@dataclass(frozen=True)
class DriftMetrics:
    unseen_templates_count: int
    unseen_rate_pct: float
    population_drift_score: float
    alert_volume_per_day: int


@dataclass(frozen=True)
class BenchmarkEntry:
    model: str
    pr_auc: float
    recall: float
    alerts: int


@dataclass(frozen=True)
class TenantOnboardingStep:
    step_index: int
    title: str
    description: str
    status: str
    isolation_boundary: str
