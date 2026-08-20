from pathlib import Path

from logsentinel.dashboard import dashboard_sample_data, score_tone


def test_dashboard_sample_data_is_explicitly_non_benchmark_and_complete() -> None:
    data = dashboard_sample_data("hdfs")
    assert data["sample_data"] is True
    assert data["benchmark_label"] == "Illustrative preview — not measured results"
    assert len(data["timeline"]) == 24
    assert len(data["incidents"]) >= 5
    assert [step["name"] for step in data["onboarding"]] == [
        "Redact",
        "Parse",
        "Train adapter",
        "Calibrate",
        "Deploy",
    ]
    assert {row["model"] for row in data["benchmarks"]} == {
        "PCA",
        "Isolation Forest",
        "DeepLog",
        "Transformer",
        "Hybrid",
    }


def test_score_tone_has_stable_operational_thresholds() -> None:
    assert score_tone(0.2) == "normal"
    assert score_tone(0.45) == "low"
    assert score_tone(0.7) == "medium"
    assert score_tone(0.9) == "high"


def test_dashboard_uses_current_streamlit_width_api() -> None:
    source = Path("src/logsentinel/dashboard.py").read_text(encoding="utf-8")
    assert "use_container_width" not in source
