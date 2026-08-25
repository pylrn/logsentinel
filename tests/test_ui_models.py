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
    assert score_tone(0.65) == AnomalyTone.MEDIUM
    assert score_tone(0.35) == AnomalyTone.LOW
    assert score_tone(0.15) == AnomalyTone.NORMAL


def test_incident_model_instantiation():
    incident = Incident(
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
    assert incident.score == 0.96
    assert incident.tone == AnomalyTone.HIGH
    assert incident.contributions["Rarity"] == 0.42
