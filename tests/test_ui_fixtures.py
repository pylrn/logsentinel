from __future__ import annotations

import re

from logsentinel.ui.fixtures import get_bgl_demo_data as get_bgl_from_pkg
from logsentinel.ui.fixtures import get_hdfs_demo_data as get_hdfs_from_pkg
from logsentinel.ui.fixtures.bgl import get_bgl_demo_data
from logsentinel.ui.fixtures.hdfs import get_hdfs_demo_data
from logsentinel.ui.models import (
    AnomalyTone,
    AppMode,
    BenchmarkEntry,
    DriftMetrics,
    Incident,
    ModelStatus,
    TenantOnboardingStep,
    TimelinePoint,
)

# Unredacted IPv4 pattern to verify data is sanitized
IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def test_hdfs_fixtures_structure():
    data = get_hdfs_demo_data()

    # Core metadata
    assert data["mode"] == AppMode.DEMO
    assert data["environment"] == "hdfs"
    assert "Illustrative preview — not measured benchmark results" in data["honesty_label"]

    # Model status
    assert isinstance(data["status"], ModelStatus)
    assert data["status"].name == "hdfs"
    assert data["status"].model_kind == "hybrid-transformer"
    assert data["status"].status == "ready"
    assert data["status"].threshold > 0.0
    assert data["status"].events_indexed > 0
    assert data["status"].vocabulary_size > 0

    # Timeline points
    assert isinstance(data["timeline"], list)
    assert len(data["timeline"]) == 24
    for tp in data["timeline"]:
        assert isinstance(tp, TimelinePoint)
        assert isinstance(tp.timestamp, str)
        assert 0.0 <= tp.score <= 1.0
        assert isinstance(tp.tone, AnomalyTone)

    # Incidents
    assert isinstance(data["incidents"], list)
    assert len(data["incidents"]) >= 6
    has_high = False
    for inc in data["incidents"]:
        assert isinstance(inc, Incident)
        assert inc.environment == "hdfs"
        assert inc.id.startswith("HDFS-INC-")
        assert isinstance(inc.tone, AnomalyTone)
        if inc.tone == AnomalyTone.HIGH:
            has_high = True
        assert len(inc.context_sequence) > 0
        assert len(inc.expected_templates) > 0
        assert len(inc.contributions) > 0
        # Verify no unredacted IPs in raw messages
        assert not IP_PATTERN.search(inc.raw_message_redacted)
    assert has_high

    # Drift metrics
    assert isinstance(data["drift"], DriftMetrics)
    assert data["drift"].unseen_templates_count >= 0
    assert data["drift"].unseen_rate_pct >= 0.0
    assert data["drift"].population_drift_score >= 0.0
    assert data["drift"].alert_volume_per_day >= 0

    # Benchmark entries
    assert isinstance(data["benchmarks"], list)
    assert len(data["benchmarks"]) >= 5
    for bm in data["benchmarks"]:
        assert isinstance(bm, BenchmarkEntry)
        assert 0.0 <= bm.pr_auc <= 1.0
        assert 0.0 <= bm.recall <= 1.0
        assert bm.alerts > 0

    # Tenant onboarding steps
    assert isinstance(data["onboarding"], list)
    assert len(data["onboarding"]) == 5
    for idx, step in enumerate(data["onboarding"], start=1):
        assert isinstance(step, TenantOnboardingStep)
        assert step.step_index == idx
        assert step.title
        assert step.description
        assert step.status == "Done"
        assert step.isolation_boundary


def test_bgl_fixtures_structure():
    data = get_bgl_demo_data()

    # Core metadata
    assert data["mode"] == AppMode.DEMO
    assert data["environment"] == "bgl"
    assert "Illustrative preview — not measured benchmark results" in data["honesty_label"]

    # Model status
    assert isinstance(data["status"], ModelStatus)
    assert data["status"].name == "bgl"
    assert data["status"].model_kind == "hybrid-transformer"
    assert data["status"].status == "ready"
    assert data["status"].threshold > 0.0
    assert data["status"].events_indexed > 0
    assert data["status"].vocabulary_size > 0

    # Timeline points
    assert isinstance(data["timeline"], list)
    assert len(data["timeline"]) == 24
    for tp in data["timeline"]:
        assert isinstance(tp, TimelinePoint)
        assert isinstance(tp.timestamp, str)
        assert 0.0 <= tp.score <= 1.0
        assert isinstance(tp.tone, AnomalyTone)

    # Incidents
    assert isinstance(data["incidents"], list)
    assert len(data["incidents"]) >= 6
    has_high = False
    for inc in data["incidents"]:
        assert isinstance(inc, Incident)
        assert inc.environment == "bgl"
        assert inc.id.startswith("BGL-INC-")
        assert isinstance(inc.tone, AnomalyTone)
        if inc.tone == AnomalyTone.HIGH:
            has_high = True
        assert len(inc.context_sequence) > 0
        assert len(inc.expected_templates) > 0
        assert len(inc.contributions) > 0
        # Verify no unredacted IPs in raw messages
        assert not IP_PATTERN.search(inc.raw_message_redacted)
    assert has_high

    # Drift metrics
    assert isinstance(data["drift"], DriftMetrics)
    assert data["drift"].unseen_templates_count >= 0
    assert data["drift"].unseen_rate_pct >= 0.0
    assert data["drift"].population_drift_score >= 0.0
    assert data["drift"].alert_volume_per_day >= 0

    # Benchmark entries
    assert isinstance(data["benchmarks"], list)
    assert len(data["benchmarks"]) >= 5
    for bm in data["benchmarks"]:
        assert isinstance(bm, BenchmarkEntry)
        assert 0.0 <= bm.pr_auc <= 1.0
        assert 0.0 <= bm.recall <= 1.0
        assert bm.alerts > 0

    # Tenant onboarding steps
    assert isinstance(data["onboarding"], list)
    assert len(data["onboarding"]) == 5
    for idx, step in enumerate(data["onboarding"], start=1):
        assert isinstance(step, TenantOnboardingStep)
        assert step.step_index == idx
        assert step.title
        assert step.description
        assert step.status == "Done"
        assert step.isolation_boundary


def test_package_exports():
    assert get_hdfs_from_pkg is get_hdfs_demo_data
    assert get_bgl_from_pkg is get_bgl_demo_data
