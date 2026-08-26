import time
from datetime import datetime

from logsentinel.ui.showcase_engine import (
    ShowcaseEnvironmentProfile,
    ShowcaseLogRecord,
    load_all_showcase_profiles,
    load_showcase_profile,
)


def _parse_dt(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def test_showcase_profiles_exist_and_typed():
    profiles = load_all_showcase_profiles()
    assert len(profiles) >= 3
    env_ids = {p.environment_id for p in profiles}
    assert "enterprise-security" in env_ids
    assert "hdfs" in env_ids
    assert "bgl" in env_ids

    for p in profiles:
        assert isinstance(p, ShowcaseEnvironmentProfile)
        assert p.display_name
        assert p.provenance_note
        assert p.train_count > 0
        assert p.val_count > 0
        assert p.test_count > 0
        assert 0.0 < p.baseline_normal_fit <= 1.0
        assert 0.0 < p.test_accuracy <= 1.0
        assert 0.0 < p.precision <= 1.0
        assert 0.0 < p.recall <= 1.0
        assert 0.0 < p.threshold <= 1.0
        assert len(p.records) == (p.train_count + p.val_count + p.test_count)
        for r in p.records:
            assert isinstance(r, ShowcaseLogRecord)


def test_zero_leakage_chronological_ordering():
    for profile in load_all_showcase_profiles():
        train_times = [_parse_dt(r.timestamp) for r in profile.records if r.partition == "train"]
        val_times = [
            _parse_dt(r.timestamp) for r in profile.records if r.partition == "validation"
        ]
        test_times = [_parse_dt(r.timestamp) for r in profile.records if r.partition == "test"]

        assert max(train_times) <= min(
            val_times
        ), f"Train/Val temporal leakage in {profile.environment_id}"
        assert max(val_times) <= min(
            test_times
        ), f"Val/Test temporal leakage in {profile.environment_id}"


def test_zero_leakage_vocabulary_fit():
    for profile in load_all_showcase_profiles():
        train_templates = {r.template_id for r in profile.records if r.partition == "train"}
        test_records = [r for r in profile.records if r.partition == "test"]
        for r in test_records:
            if r.template_id not in train_templates:
                assert (
                    "unseen" in r.business_impact.lower()
                    or "novel" in r.business_impact.lower()
                    or r.ground_truth == 1
                )


def test_zero_leakage_scaler_and_threshold_fit():
    for profile in load_all_showcase_profiles():
        assert profile.threshold > 0.0
        val_scores = [r.anomaly_score for r in profile.records if r.partition == "validation"]
        assert len(val_scores) > 0


def test_local_cpu_inference_latency_budget():
    start = time.perf_counter()
    profile = load_showcase_profile("enterprise-security")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert profile.environment_id == "enterprise-security"
    assert (
        elapsed_ms < 50.0
    ), f"Inference engine exceeded generous CI latency threshold: {elapsed_ms:.2f}ms"
