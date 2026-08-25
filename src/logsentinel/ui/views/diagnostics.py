from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from logsentinel.ui.client import DashboardApiClient
from logsentinel.ui.models import AppMode, BenchmarkEntry, DriftMetrics, ModelStatus


def render_diagnostics_view(
    state: dict[str, Any],
    client: DashboardApiClient | None = None,
    environment: str = "hdfs",
) -> None:
    """Render the 'How is the model performing?' model health and diagnostics workspace."""
    mode = state.get("mode", AppMode.DEMO)
    is_demo = mode == AppMode.DEMO or mode == "demo" or "honesty_label" in state

    # Persistent honesty disclaimer banner in demo mode
    if is_demo:
        honesty_msg = state.get(
            "honesty_label",
            "Illustrative preview — not measured benchmark results",
        )
        st.markdown(
            f"""
            <div class="honesty-banner" style="
                background: #FFF4E5;
                border-left: 4px solid #FF8A00;
                border-radius: 6px;
                padding: 10px 16px;
                margin-bottom: 16px;
                color: #994B00;
                font-size: 13px;
                font-weight: 500;
            ">
                <strong>⚠️ {honesty_msg}:</strong>
                The performance numbers, drift metrics, and threshold curves below are
                illustrative traces designed for UI demonstration and offline evaluation.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <h2 style="margin-bottom: 4px; font-weight: 700;">
                Model Diagnostics & Benchmark Performance
            </h2>
            <div style="color: #637083; font-size: 14px;">
                How is the model performing? Monitor vocabulary drift,
                simulate threshold impact, and compare hybrid models against baselines.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    status: ModelStatus | None = state.get("status")
    default_thresh = status.threshold if status else 0.80

    # 1. Threshold Sensitivity Slider & Impact Simulation
    st.markdown("### Operational Threshold Sensitivity")
    col_slider, col_impact = st.columns([2.5, 1.5])

    with col_slider:
        threshold = st.slider(
            "Anomaly Detection Threshold (τ)",
            min_value=0.0,
            max_value=1.0,
            value=float(default_thresh),
            step=0.01,
            help="Incidents with ensemble fused score >= τ trigger operator alerting.",
            key="diagnostics_threshold_slider",
        )

    drift: DriftMetrics = state.get("drift") or DriftMetrics(
        unseen_templates_count=0,
        unseen_rate_pct=0.0,
        population_drift_score=0.0,
        alert_volume_per_day=140,
    )

    base_alerts = drift.alert_volume_per_day or 150
    # Simulate impact on daily alert volume based on chosen threshold
    simulated_alerts = int(max(5, base_alerts * ((1.05 - threshold) / (1.05 - default_thresh))))

    with col_impact:
        st.metric(
            "Projected Daily Alerts",
            f"{simulated_alerts} / day",
            delta=f"{simulated_alerts - base_alerts:+d} vs baseline",
            delta_color="inverse",
        )

    # 2. Drift Metric Cards
    st.markdown("### Template Vocabulary & Distribution Drift")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            label="Unseen Templates",
            value=f"{drift.unseen_templates_count}",
            delta=f"{drift.unseen_rate_pct:.1f}% unseen rate",
            delta_color="inverse" if drift.unseen_templates_count > 20 else "normal",
        )
    with c2:
        st.metric(
            label="Unseen Template Rate",
            value=f"{drift.unseen_rate_pct:.1f}%",
            delta="Target: < 5.0%",
            delta_color="normal" if drift.unseen_rate_pct <= 5.0 else "inverse",
        )
    with c3:
        st.metric(
            label="Population Drift Score",
            value=f"{drift.population_drift_score:.2f}",
            delta="Stable" if drift.population_drift_score < 0.5 else "Elevated Drift",
            delta_color="normal" if drift.population_drift_score < 0.5 else "inverse",
        )
    with c4:
        st.metric(
            label="Baseline Alert Volume",
            value=f"{drift.alert_volume_per_day} / day",
            delta=f"Active Threshold {threshold:.2f}",
        )

    # 3. Benchmark Comparison Table
    st.markdown("### Benchmark Comparison: Baseline vs Neural vs Hybrid Models")
    benchmarks_data = state.get("benchmarks", [])
    if benchmarks_data:
        benchmark_rows = []
        for bm in benchmarks_data:
            if isinstance(bm, BenchmarkEntry):
                model_name = bm.model
                pr_auc = bm.pr_auc
                recall = bm.recall
                alerts = bm.alerts
            else:
                model_name = bm.get("model", "Unknown")
                pr_auc = float(bm.get("pr_auc", 0.0))
                recall = float(bm.get("recall", 0.0))
                alerts = int(bm.get("alerts", 0))

            if "Hybrid" in model_name or "Calibrated" in model_name:
                category = "Hybrid (Statistical + Neural)"
            elif "Transformer" in model_name or "DeepLog" in model_name:
                category = "Neural Sequence"
            else:
                category = "Statistical Baseline"

            benchmark_rows.append(
                {
                    "Model": model_name,
                    "Category": category,
                    "PR-AUC": f"{pr_auc:.3f}",
                    "Recall @ 95% Precision": f"{recall:.1%}",
                    "Daily False Alerts": alerts,
                }
            )

        df_benchmarks = pd.DataFrame(benchmark_rows)
        st.dataframe(df_benchmarks, width="stretch", hide_index=True)
    else:
        st.info("No benchmark comparison data available for this environment.")
