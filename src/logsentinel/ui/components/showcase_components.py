"""Reusable UI components for the LogSentinel Model Proof workspace.

Provides interactive zero-leakage journey steppers, partition health cards,
chronologically partitioned log tables with radio filters, and causal explainers
with Plotly attribution bar charts and curated operational guidance.
"""

from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from logsentinel.ui.showcase_engine import ShowcaseEnvironmentProfile, ShowcaseLogRecord
from logsentinel.ui.styles import (
    COLOR_ACCENT,
    COLOR_ANOMALY_HIGH,
    COLOR_BORDER,
    COLOR_CANVAS,
    COLOR_INK,
    COLOR_MUTED,
    COLOR_READY,
    COLOR_SURFACE,
    get_tone_badge_html,
)


def create_attribution_figure(contributions: dict[str, float]) -> go.Figure:
    """Create a horizontal attribution bar chart for ensemble feature contributions.

    Styled using WCAG AA design tokens (#0B6CFB, #E3242B, #10A66A).
    """
    if not contributions:
        fig = go.Figure(data=[go.Bar(x=[], y=[], orientation="h")])
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis=dict(showgrid=False, range=[0, 1]),
            yaxis=dict(showgrid=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # Reverse keys so the highest or first contribution appears at top on horizontal bar chart
    keys = list(contributions.keys())[::-1]
    values = [contributions[k] for k in keys]
    total = sum(values) if sum(values) > 0 else 1.0
    text_labels = [f"{v:.2f} ({v / total * 100:.1f}%)" for v in values]

    # WCAG AA compliant colors based on contribution intensity
    colors = [
        COLOR_ANOMALY_HIGH if v >= 0.3 else COLOR_ACCENT if v >= 0.1 else COLOR_READY
        for v in values
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=values,
                y=keys,
                orientation="h",
                text=text_labels,
                textposition="auto",
                marker=dict(
                    color=colors,
                    line=dict(width=1, color=COLOR_BORDER),
                ),
                hoverinfo="x+y",
            )
        ]
    )

    fig.update_layout(
        height=max(180, len(keys) * 45),
        margin=dict(l=10, r=20, t=15, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color=COLOR_INK,
            family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=COLOR_BORDER,
            color=COLOR_MUTED,
            range=[0, max(1.0, max(values, default=1.0) * 1.2)],
            title="Attribution Weight (Score Component)",
        ),
        yaxis=dict(
            showgrid=False,
            color=COLOR_INK,
        ),
    )
    return fig


def render_showcase_journey_stepper() -> None:
    """Render a visual 4-card stepper showing the zero-leakage ML pipeline journey."""
    stages = [
        {
            "step": "Stage 1",
            "title": "Ingress & Redaction",
            "status": "Sanitized",
            "bg": "#E8F8F0",
            "color": "#085E3B",
            "symbol": "🔒",
            "desc": (
                "Tenant PII, IP addresses, and UUIDs scrubbed with deterministic "
                "token masks before parsing."
            ),
        },
        {
            "step": "Stage 2",
            "title": "Zero-Leakage Chronological Split",
            "status": "Strict Time-Split",
            "bg": "#E6F0FE",
            "color": "#0B6CFB",
            "symbol": "⏱️",
            "desc": (
                "Past events fit normal baseline; future held-out partitions "
                "contain unseen attacks without leakage."
            ),
        },
        {
            "step": "Stage 3",
            "title": "Model Calibration",
            "status": "EVT Calibration",
            "bg": "#FFF4E5",
            "color": "#994B00",
            "symbol": "🎯",
            "desc": (
                "Decision threshold τ tuned on validation split to minimize "
                "operational false alarm rate."
            ),
        },
        {
            "step": "Stage 4",
            "title": "Generalization Evaluation",
            "status": "Held-Out Test",
            "bg": "#FDE8E8",
            "color": "#9B1C1C",
            "symbol": "🛡️",
            "desc": (
                "Evaluated against novel MITRE ATT&CK techniques with sequence NLL "
                "and rarity attribution."
            ),
        },
    ]

    cols = st.columns(4, gap="small")
    for stage, col in zip(stages, cols, strict=False):
        step_num = stage["step"]
        title = html.escape(stage["title"])
        status = html.escape(stage["status"])
        bg = stage["bg"]
        color = stage["color"]
        symbol = stage["symbol"]
        desc = html.escape(stage["desc"])

        with col:
            st.markdown(
                f"""
                <div style="
                    background: {COLOR_SURFACE};
                    border: 1px solid {COLOR_BORDER};
                    border-top: 3px solid {color};
                    border-radius: 8px;
                    padding: 14px;
                    min-height: 140px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                ">
                    <div style="display: flex; justify-content: space-between;
                                align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 700;
                                     color: {COLOR_MUTED}; text-transform: uppercase;">
                            {step_num}
                        </span>
                        <span style="
                            font-size: 11px;
                            font-weight: 600;
                            background: {bg};
                            color: {color};
                            padding: 2px 7px;
                            border-radius: 4px;
                        ">
                            {symbol} {status}
                        </span>
                    </div>
                    <div style="font-size: 13px; font-weight: 700;
                                color: {COLOR_INK}; margin-bottom: 6px;">
                        {title}
                    </div>
                    <div style="font-size: 11px; color: {COLOR_MUTED}; line-height: 1.45;">
                        {desc}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_partition_health_cards(profile: ShowcaseEnvironmentProfile) -> None:
    """Render metric health cards for baseline fit, test accuracy, and false alert rate."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Baseline Normal Fit",
            value=f"{profile.baseline_normal_fit * 100:.1f}%",
            delta=f"{profile.train_count} Train Normal Events",
            help="Normal sequence fitting accuracy on the past training partition.",
        )
    with col2:
        st.metric(
            label="Held-Out Test Accuracy",
            value=f"{profile.test_accuracy * 100:.1f}%",
            delta=f"{profile.test_count} Future Test Events",
            help="Generalization accuracy on unseen future test logs.",
        )
    with col3:
        st.metric(
            label="Precision & Recall @ τ",
            value=f"{profile.precision * 100:.1f}% / {profile.recall * 100:.1f}%",
            delta=f"F1: {profile.f1_score * 100:.1f}% (τ = {profile.threshold:.2f})",
            help=(
                "Operational detection metrics calibrated on validation partition "
                f"at threshold τ = {profile.threshold:.2f}."
            ),
        )
    with col4:
        st.metric(
            label="False Alert Rate",
            value=f"{profile.false_alert_rate_pct:.1f}%",
            delta="Operational Target < 0.2%",
            delta_color="normal",
            help="Percentage of normal baseline operations triggering false positive alerts.",
        )


def render_showcase_log_table(
    records: list[ShowcaseLogRecord],
    key_prefix: str = "showcase_tbl",
) -> ShowcaseLogRecord | None:
    """Render interactive log table with partition filter and record selector."""
    if not records:
        st.info("No showcase log records available.")
        return None

    filter_options = [
        "All Records",
        "Train Normal (Past)",
        "Validation (Calibration)",
        "Test Normal (Future)",
        "Test Anomalies / Attacks (Future)",
    ]

    col_filter, col_stats = st.columns([3, 2])
    with col_filter:
        selected_filter = st.radio(
            "Filter Partition / Record Type",
            options=filter_options,
            index=0,
            horizontal=True,
            key=f"{key_prefix}_partition_filter",
        )

    # Apply filter
    if selected_filter == "Train Normal (Past)":
        filtered_records = [r for r in records if r.partition == "train"]
    elif selected_filter == "Validation (Calibration)":
        filtered_records = [r for r in records if r.partition == "validation"]
    elif selected_filter == "Test Normal (Future)":
        filtered_records = [r for r in records if r.partition == "test" and r.ground_truth == 0]
    elif selected_filter == "Test Anomalies / Attacks (Future)":
        filtered_records = [
            r for r in records if r.partition == "test" and (r.ground_truth == 1 or r.is_anomaly)
        ]
    else:
        filtered_records = list(records)

    if not filtered_records:
        filtered_records = list(records)

    with col_stats:
        normal_cnt = sum(1 for r in filtered_records if r.ground_truth == 0)
        anomaly_cnt = sum(1 for r in filtered_records if r.ground_truth == 1 or r.is_anomaly)
        st.markdown(
            f"""
            <div style="font-size: 12px; color: {COLOR_MUTED};
                        text-align: right; padding-top: 10px;">
                Showing <strong>{len(filtered_records)}</strong> records
                (✔ {normal_cnt} Normal, 🚨 {anomaly_cnt} Anomalies)
            </div>
            """,
            unsafe_allow_html=True,
        )

    table_data = [
        {
            "ID": r.id,
            "Time": r.timestamp,
            "Partition": r.partition.capitalize(),
            "Host": r.host,
            "Redacted Log Message": r.raw_message_redacted,
            "Template ID": r.template_id,
            "Anomaly Score": f"{r.anomaly_score:.2f}",
            "Ground Truth": (
                "Anomaly (1)" if (r.ground_truth == 1 or r.is_anomaly) else "Normal (0)"
            ),
            "Attack Tag / Deviation": r.attack_technique or "Normal Baseline",
        }
        for r in filtered_records
    ]
    df = pd.DataFrame(table_data)
    st.dataframe(df, width="stretch", hide_index=True)

    # Record selector
    options_indices = list(range(len(filtered_records)))

    def _format_record_option(idx: int) -> str:
        rec = filtered_records[idx]
        tag = f" [{rec.attack_technique}]" if rec.attack_technique else ""
        return (
            f"#{rec.id} | {rec.partition.upper()} | "
            f"Score: {rec.anomaly_score:.2f} | {rec.host} | "
            f"{rec.raw_message_redacted[:50]}...{tag}"
        )

    selected_choice = st.selectbox(
        "Select Log Record to Inspect in Causal Explainer",
        options=options_indices,
        index=0,
        format_func=_format_record_option,
        key=f"{key_prefix}_record_selector",
    )

    if isinstance(selected_choice, int):
        if 0 <= selected_choice < len(filtered_records):
            return filtered_records[selected_choice]
        return filtered_records[0]
    if isinstance(selected_choice, ShowcaseLogRecord):
        return selected_choice
    if isinstance(selected_choice, str):
        id_map = {r.id: r for r in filtered_records}
        return id_map.get(selected_choice, filtered_records[0])
    return filtered_records[0]


def render_showcase_explainer(record: ShowcaseLogRecord, threshold: float) -> None:
    """Render comprehensive causal explainer for a selected showcase log record."""
    is_anomaly_detected = record.anomaly_score >= threshold
    if is_anomaly_detected:
        tone = "high" if record.anomaly_score >= 0.9 else "medium"
    else:
        tone = "low" if record.anomaly_score >= 0.5 else "normal"

    tone_badge = get_tone_badge_html(tone, record.anomaly_score)

    status_pill = (
        '<span style="background:#FDE8E8;color:#9B1C1C;padding:2px 8px;'
        'border-radius:4px;font-weight:700;font-size:12px;">🚨 ANOMALY DETECTED</span>'
        if is_anomaly_detected
        else '<span style="background:#E8F8F0;color:#085E3B;padding:2px 8px;'
        'border-radius:4px;font-weight:700;font-size:12px;">✔ NORMAL OPERATION</span>'
    )

    attack_html = (
        f'<div><strong>Attack Technique:</strong> <span style="background:#FFF4E5;'
        f'color:#994B00;padding:1px 6px;border-radius:3px;font-weight:600;">'
        f"{html.escape(record.attack_technique)}</span></div>"
        if record.attack_technique
        else ""
    )

    safe_partition = html.escape(record.partition)
    safe_host = html.escape(record.host)
    safe_time = html.escape(record.timestamp)
    gt_label = "Anomaly (1)" if record.ground_truth == 1 else "Normal (0)"

    st.markdown(
        f"""
        <div style="
            background: {COLOR_SURFACE};
            border: 1px solid {COLOR_BORDER};
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
            margin-bottom: 16px;
        ">
            <div style="display: flex; justify-content: space-between;
                        align-items: center; margin-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 18px; font-weight: 700; color: {COLOR_INK};">
                        Event #{html.escape(record.id)} Analysis
                    </span>
                    {tone_badge}
                    {status_pill}
                </div>
                <div style="font-size: 13px; color: {COLOR_MUTED};">
                    <strong>Partition:</strong>
                    <span style="text-transform: capitalize;">{safe_partition}</span> |
                    <strong>Host:</strong> <code>{safe_host}</code> |
                    <strong>Time:</strong> {safe_time}
                </div>
            </div>
            <div style="display: flex; gap: 24px; padding-top: 8px;
                        border-top: 1px solid {COLOR_BORDER}; font-size: 13px;">
                <div>
                    <strong>Calibrated Score:</strong>
                    <code style="font-size: 14px; font-weight: 700;">
                        {record.anomaly_score:.3f}
                    </code>
                </div>
                <div>
                    <strong>Decision Threshold τ:</strong>
                    <code style="font-size: 14px;">{threshold:.2f}</code>
                </div>
                <div><strong>Ground Truth:</strong> <span>{gt_label}</span></div>
                {attack_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sanitized raw log display
    st.markdown("<strong>Sanitized Raw Log Message</strong>", unsafe_allow_html=True)
    st.code(record.raw_message_redacted, language="text")

    # 2-column breakdown
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown(
            f"""
            <div style="font-size: 14px; font-weight: 700;
                        color: {COLOR_INK}; margin-bottom: 8px;">
                📊 Signal & Feature Attribution Breakdown
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig = create_attribution_figure(record.contributions)
        st.plotly_chart(fig, width="stretch")

        # Extracted template details
        safe_tid = html.escape(record.template_id)
        safe_ttext = html.escape(record.template_text)
        st.markdown(
            f"""
            <div style="
                background: {COLOR_CANVAS};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 12px;
                margin-top: 8px;
            ">
                <strong>Extracted Template ID:</strong> <code>{safe_tid}</code><br>
                <strong>Template Pattern:</strong> <code>{safe_ttext}</code>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            f"""
            <div style="font-size: 14px; font-weight: 700;
                        color: {COLOR_INK}; margin-bottom: 8px;">
                🧠 Operational Context & Response Guidance
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Operational Impact
        st.markdown(
            f"""
            <div style="
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-left: 4px solid {COLOR_ACCENT};
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 12px; font-weight: 700;
                            color: {COLOR_INK}; margin-bottom: 4px;">
                    💼 Operational & Business Impact
                </div>
                <div style="font-size: 12px; color: {COLOR_INK}; line-height: 1.45;">
                    {html.escape(record.business_impact)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Sequence transition context
        expected_html = (
            ", ".join(f"<code>{html.escape(t)}</code>" for t in record.expected_templates)
            if record.expected_templates
            else "<em>None (First event or standard baseline)</em>"
        )
        st.markdown(
            f"""
            <div style="
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-left: 4px solid #FF8A00;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 12px; font-weight: 700;
                            color: {COLOR_INK}; margin-bottom: 4px;">
                    🔄 Sequence Transition Context
                </div>
                <div style="font-size: 12px; color: {COLOR_INK}; line-height: 1.45;">
                    <strong>Observed Template:</strong> <code>{safe_tid}</code><br>
                    <strong>Expected Normal Next Templates:</strong> {expected_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Recommended Action
        st.markdown(
            f"""
            <div style="
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-left: 4px solid {COLOR_READY};
                border-radius: 6px;
                padding: 12px;
            ">
                <div style="font-size: 12px; font-weight: 700;
                            color: {COLOR_INK}; margin-bottom: 4px;">
                    🛡️ Recommended SOC / SRE Response Action
                </div>
                <div style="font-size: 12px; color: {COLOR_INK}; line-height: 1.45;">
                    {html.escape(record.soc_action)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
