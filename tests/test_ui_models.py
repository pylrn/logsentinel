from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from logsentinel.ui.models import (
    AnomalyTone,
    AppMode,
    BenchmarkEntry,
    DriftMetrics,
    Incident,
    ModelStatus,
    TenantOnboardingStep,
    TimelinePoint,
    score_tone,
)


def test_score_tone_mapping():
    assert score_tone(0.95) == AnomalyTone.HIGH
    assert score_tone(0.80) == AnomalyTone.HIGH
    assert score_tone(0.65) == AnomalyTone.MEDIUM
    assert score_tone(0.50) == AnomalyTone.MEDIUM
    assert score_tone(0.35) == AnomalyTone.LOW
    assert score_tone(0.30) == AnomalyTone.LOW
    assert score_tone(0.15) == AnomalyTone.NORMAL
    assert score_tone(0.0) == AnomalyTone.NORMAL


def test_app_mode_values():
    assert AppMode.LIVE == "live"
    assert AppMode.DEMO == "demo"
    assert isinstance(AppMode.LIVE, str)
    assert isinstance(AppMode.DEMO, str)


def test_anomaly_tone_values():
    assert AnomalyTone.HIGH == "high"
    assert AnomalyTone.MEDIUM == "medium"
    assert AnomalyTone.LOW == "low"
    assert AnomalyTone.NORMAL == "normal"
    assert isinstance(AnomalyTone.HIGH, str)


def test_model_status_instantiation_and_immutability():
    status = ModelStatus(
        name="HDFS DeepLog",
        version="v1.0",
        model_kind="deeplog",
        status="Active",
        threshold=0.85,
    )
    assert status.name == "HDFS DeepLog"
    assert status.events_indexed == 0
    assert status.vocabulary_size == 0

    with pytest.raises(FrozenInstanceError):
        status.status = "Inactive"  # type: ignore[misc]


def test_incident_model_instantiation_defaults_and_immutability():
    incident_default = Incident(
        id="inc-default",
        time="2025-05-12T12:00:00Z",
        source="DataNode-1",
        score=0.45,
        tone=AnomalyTone.LOW,
        signal="Rarity",
        status="Investigating",
        environment="test",
        raw_message_redacted="Redacted message",
        template_id="E_001",
        template_text="Template text",
    )
    assert incident_default.context_sequence == []
    assert incident_default.expected_templates == []
    assert incident_default.contributions == {}

    incident_full = Incident(
        id="inc-1",
        time="2025-05-12T12:00:00Z",
        source="DataNode-3",
        score=0.96,
        tone=AnomalyTone.HIGH,
        signal="Template rarity",
        status="Active",
        environment="hdfs",
        raw_message_redacted="Received block <BLOCK_ID> from <IP>",
        template_id="E_4af1",
        template_text="Received block <*> from <*>",
        context_sequence=["E_1234", "E_5678"],
        expected_templates=["Block verification succeeded"],
        contributions={"Rarity": 0.42, "PCA": 0.31},
    )
    assert incident_full.score == 0.96
    assert incident_full.tone == AnomalyTone.HIGH
    assert incident_full.contributions["Rarity"] == 0.42

    with pytest.raises(FrozenInstanceError):
        incident_full.score = 0.5  # type: ignore[misc]


def test_timeline_point_instantiation_and_immutability():
    tp_default = TimelinePoint(
        timestamp="2025-05-12T12:00:00Z",
        score=0.85,
        tone=AnomalyTone.HIGH,
    )
    assert tp_default.incident_count == 1

    tp_custom = TimelinePoint(
        timestamp="2025-05-12T12:05:00Z",
        score=0.2,
        tone=AnomalyTone.NORMAL,
        incident_count=5,
    )
    assert tp_custom.incident_count == 5

    with pytest.raises(FrozenInstanceError):
        tp_default.score = 0.1  # type: ignore[misc]


def test_drift_metrics_instantiation_and_immutability():
    drift = DriftMetrics(
        unseen_templates_count=12,
        unseen_rate_pct=3.5,
        population_drift_score=0.18,
        alert_volume_per_day=45,
    )
    assert drift.unseen_templates_count == 12
    assert drift.unseen_rate_pct == 3.5
    assert drift.population_drift_score == 0.18
    assert drift.alert_volume_per_day == 45

    with pytest.raises(FrozenInstanceError):
        drift.unseen_templates_count = 20  # type: ignore[misc]


def test_benchmark_entry_instantiation_and_immutability():
    entry = BenchmarkEntry(
        model="DeepLog",
        pr_auc=0.94,
        recall=0.91,
        alerts=150,
    )
    assert entry.model == "DeepLog"
    assert entry.pr_auc == 0.94
    assert entry.recall == 0.91
    assert entry.alerts == 150

    with pytest.raises(FrozenInstanceError):
        entry.recall = 0.95  # type: ignore[misc]


def test_tenant_onboarding_step_instantiation_and_immutability():
    step = TenantOnboardingStep(
        step_index=1,
        title="Ingest Logs",
        description="Configure log agent",
        status="Completed",
        isolation_boundary="tenant-a",
    )
    assert step.step_index == 1
    assert step.title == "Ingest Logs"
    assert step.description == "Configure log agent"
    assert step.status == "Completed"
    assert step.isolation_boundary == "tenant-a"

    with pytest.raises(FrozenInstanceError):
        step.status = "Pending"  # type: ignore[misc]
