"""Reusable UI components for the LogSentinel Model Proof & Generalization Showcase."""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from logsentinel.ui.showcase_engine import (
    ShowcaseEnvironmentProfile,
    ShowcaseLogRecord,
)
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

    Styled using WCAG AA design tokens with high-contrast text and crisp bar markers.
    """
    if not contributions:
        fig = go.Figure(data=[go.Bar(x=[], y=[], orientation="h")])
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis=dict(showgrid=False, range=[0, 1]),
            yaxis=dict(showgrid=False),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
        )
        return fig

    # Reverse keys so the highest or first contribution appears at top on horizontal bar chart
    keys = list(contributions.keys())[::-1]
    values = [contributions[k] for k in keys]
    total = sum(values) if sum(values) > 0 else 1.0
    text_labels = [f" {v:.2f} ({v / total * 100:.1f}%)" for v in values]

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
                textposition="outside",
                marker=dict(
                    color=colors,
                    line=dict(width=1, color=COLOR_BORDER),
                ),
                hoverinfo="x+y",
            )
        ]
    )

    max_val = max(values, default=1.0)
    fig.update_layout(
        height=max(180, len(keys) * 45),
        margin=dict(l=10, r=40, t=15, b=20),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            color="#142033",
            size=12,
            family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#E5EBF2",
            tickfont=dict(size=11, color="#142033"),
            title=dict(
                text="Attribution Weight (Score Component)",
                font=dict(size=12, color="#142033"),
            ),
            range=[0, max(0.5, max_val * 1.35)],
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=12, color="#142033"),
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
            card_html = (
                f'<div style="background:{COLOR_SURFACE};border:1px solid {COLOR_BORDER};'
                f'border-top:3px solid {color};border-radius:8px;padding:14px;'
                f'min-height:140px;box-shadow:0 1px 3px rgba(0,0,0,0.05);">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;margin-bottom:8px;">'
                f'<span style="font-size:11px;font-weight:700;color:{COLOR_MUTED};'
                f'text-transform:uppercase;">{step_num}</span>'
                f'<span style="font-size:11px;font-weight:600;background:{bg};color:{color};'
                f'padding:2px 7px;border-radius:4px;">{symbol} {status}</span>'
                f'</div>'
                f'<div style="font-size:13px;font-weight:700;color:{COLOR_INK};margin-bottom:6px;">'
                f'{title}</div>'
                f'<div style="font-size:11px;color:{COLOR_MUTED};line-height:1.45;">'
                f'{desc}</div></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)


def render_partition_health_cards(profile: ShowcaseEnvironmentProfile) -> None:
    """Render metric health cards for baseline fit, test accuracy, and false alert rate."""
    cols = st.columns(4)
    col1, col2, col3, col4 = cols[0], cols[1], cols[2], cols[3]
    with col1:
        st.metric(
            label="Baseline Normal Fit",
            value=f"{profile.baseline_normal_fit * 100:.1f}%",
            delta=f"{profile.train_count} train sessions (Past)",
            help="Coverage of normal baseline events within the 99.5% EVT boundary.",
        )
    with col2:
        st.metric(
            label="Held-Out Test Accuracy",
            value=f"{profile.test_accuracy * 100:.1f}%",
            delta=f"{profile.test_count} unseen test sessions",
            delta_color="normal",
            help="Empirical detection accuracy measured exclusively on the held-out test split.",
        )
    with col3:
        st.metric(
            label="Precision & Recall @ τ",
            value=f"P: {profile.precision * 100:.1f}%",
            delta=f"Recall: {profile.recall * 100:.1f}% (τ={profile.threshold:.2f})",
            delta_color="normal",
            help=f"Precision and recall at threshold τ={profile.threshold:.2f}.",
        )
    with col4:
        st.metric(
            label="False Alert Rate",
            value=f"{profile.false_alert_rate_pct:.2f}%",
            delta="Target: < 0.20%",
            delta_color="normal" if profile.false_alert_rate_pct <= 0.20 else "inverse",
            help="Rate of false positives on normal traffic. Target is <0.20%.",
        )


def render_showcase_log_table(
    records: list[ShowcaseLogRecord],
    key_prefix: str = "showcase_tbl",
) -> ShowcaseLogRecord | None:
    """Render interactive filterable log table and return the selected ShowcaseLogRecord."""
    if not records:
        st.info("No records available in this environment profile.")
        return None

    # Filter selector
    filter_options = [
        "All Records",
        "Train Normal (Past)",
        "Validation (Calibration)",
        "Test Normal (Future)",
        "Test Anomalies / Attacks (Future)",
    ]

    selected_filter = st.radio(
        "Partition Filter",
        options=filter_options,
        horizontal=True,
        key=f"{key_prefix}_partition_filter",
    )

    # Apply filtering
    if selected_filter == "Train Normal (Past)":
        filtered_records = [r for r in records if r.partition == "train"]
    elif selected_filter == "Validation (Calibration)":
        filtered_records = [r for r in records if r.partition == "validation"]
    elif selected_filter == "Test Normal (Future)":
        filtered_records = [
            r for r in records if r.partition == "test" and r.ground_truth == 0
        ]
    elif selected_filter == "Test Anomalies / Attacks (Future)":
        filtered_records = [
            r for r in records if r.partition == "test" and r.ground_truth == 1
        ]
    else:
        filtered_records = list(records)

    if not filtered_records:
        st.warning(f"No records found matching filter: '{selected_filter}'")
        return None

    # Construct clean tabular dataframe
    table_rows: list[dict[str, Any]] = []
    for r in filtered_records:
        tone_str = (
            "HIGH"
            if r.anomaly_score >= 0.85
            else "MED"
            if r.anomaly_score >= 0.50
            else "NORMAL"
        )
        verdict_badge = (
            f"● {tone_str} ({r.anomaly_score:.2f})"
            if r.anomaly_score >= 0.50
            else f"✔ Normal ({r.anomaly_score:.2f})"
        )
        gt_str = "🚨 Anomaly (1)" if r.ground_truth == 1 else "Normal (0)"
        attack_tag = (
            r.attack_technique or ("Novel/Anomaly" if r.ground_truth == 1 else "Normal Flow")
        )

        table_rows.append(
            {
                "ID": r.id,
                "Time": r.timestamp.replace("T", " ")[:19],
                "Partition": r.partition.capitalize(),
                "Host": r.host,
                "Redacted Log Message": r.raw_message_redacted,
                "Template ID": r.template_id,
                "Score / Tone": verdict_badge,
                "Ground Truth": gt_str,
                "Scenario Tag": attack_tag,
            }
        )

    df = pd.DataFrame(table_rows)

    # Display stats summary
    st.markdown(
        f"<div style='font-size:13px;color:{COLOR_MUTED};margin-bottom:6px;'>"
        f"Showing <strong>{len(filtered_records)}</strong> logs for <em>{selected_filter}</em>. "
        f"Click or select an event below to inspect causal attribution."
        f"</div>",
        unsafe_allow_html=True,
    )

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
    )

    # Interactive selector for detailed explainer
    options_map = {
        idx: f"#{r.id} | {r.partition.upper()} | Score: {r.anomaly_score:.3f} | "
        f"{r.raw_message_redacted[:60]}..."
        for idx, r in enumerate(filtered_records)
    }

    selected_idx = st.selectbox(
        "Select Log Event to Inspect Causal Breakdown & Response Actions",
        options=list(options_map.keys()),
        format_func=lambda i: options_map.get(i, f"Event #{i}"),
        key=f"{key_prefix}_record_selector",
    )

    if isinstance(selected_idx, int) and 0 <= selected_idx < len(filtered_records):
        return filtered_records[selected_idx]
    return filtered_records[0]


def render_showcase_explainer(record: ShowcaseLogRecord, threshold: float) -> None:
    """Render comprehensive causal explainer for a selected showcase log record."""
    is_anomaly_detected = record.anomaly_score >= threshold
    if is_anomaly_detected:
        tone = "high" if record.anomaly_score >= 0.9 else "medium"
    else:
        tone = "low" if record.anomaly_score >= 0.5 else "normal"

    tone_badge = get_tone_badge_html(tone, record.anomaly_score)

    if is_anomaly_detected:
        status_pill = (
            '<span style="background:#FDE8E8;color:#9B1C1C;padding:3px 8px;'
            'border-radius:4px;font-weight:700;font-size:12px;">🚨 ANOMALY DETECTED</span>'
        )
    else:
        status_pill = (
            '<span style="background:#E8F8F0;color:#085E3B;padding:3px 8px;'
            'border-radius:4px;font-weight:700;font-size:12px;">✔ NORMAL OPERATION</span>'
        )

    if record.attack_technique:
        attack_esc = html.escape(record.attack_technique)
        attack_html = (
            f'<div><span style="color:{COLOR_MUTED};font-weight:600;">Attack Technique:</span> '
            f'<span style="background:#FFF4E5;color:#994B00;padding:2px 6px;border-radius:4px;'
            f'font-weight:700;font-family:monospace;">{attack_esc}</span></div>'
        )
    else:
        attack_html = ""

    safe_partition = html.escape(record.partition)
    safe_host = html.escape(record.host)
    safe_time = html.escape(record.timestamp)
    gt_label = "🚨 Anomaly (1)" if record.ground_truth == 1 else "✔ Normal (0)"

    header_html = (
        f'<div style="background:{COLOR_SURFACE};border:1px solid {COLOR_BORDER};'
        f'border-radius:8px;padding:16px;margin-top:16px;margin-bottom:16px;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.04);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:18px;font-weight:700;color:{COLOR_INK};">'
        f'Event #{html.escape(record.id)} Analysis</span>'
        f'{tone_badge}{status_pill}</div>'
        f'<div style="font-size:13px;color:{COLOR_MUTED};">'
        f'<strong>Partition:</strong> <span style="text-transform:capitalize;">'
        f'{safe_partition}</span> | <strong>Host:</strong> '
        f'<span style="background:#F0F4F8;padding:2px 6px;border-radius:4px;'
        f'font-family:monospace;color:{COLOR_INK};">{safe_host}</span> | '
        f'<strong>Time:</strong> {safe_time}</div></div>'
        f'<div style="display:flex;gap:24px;padding-top:10px;border-top:1px solid '
        f'{COLOR_BORDER};font-size:13px;align-items:center;">'
        f'<div><span style="color:{COLOR_MUTED};font-weight:600;">Calibrated Score:</span> '
        f'<span style="font-size:15px;font-weight:700;color:{COLOR_INK};margin-left:4px;'
        f'font-family:monospace;">{record.anomaly_score:.3f}</span></div>'
        f'<div><span style="color:{COLOR_MUTED};font-weight:600;">Decision Threshold τ:</span> '
        f'<span style="font-size:14px;font-weight:600;color:{COLOR_INK};margin-left:4px;'
        f'font-family:monospace;">{threshold:.2f}</span></div>'
        f'<div><span style="color:{COLOR_MUTED};font-weight:600;">Ground Truth:</span> '
        f'<span style="font-weight:600;color:{COLOR_INK};margin-left:4px;">{gt_label}</span></div>'
        f'{attack_html}</div></div>'
    )

    st.markdown(header_html, unsafe_allow_html=True)

    # Sanitized raw log display
    st.markdown("<strong>Sanitized Raw Log Message</strong>", unsafe_allow_html=True)
    st.code(record.raw_message_redacted, language="text")

    # 2-column breakdown
    cols_lr = st.columns([1, 1], gap="medium")
    col_left, col_right = cols_lr[0], cols_lr[1]

    with col_left:
        st.markdown(
            f"<div style='font-size:14px;font-weight:700;color:{COLOR_INK};margin-bottom:8px;'>"
            f"📊 Signal & Feature Attribution Breakdown"
            f"</div>",
            unsafe_allow_html=True,
        )
        fig = create_attribution_figure(record.contributions)
        st.plotly_chart(fig, width="stretch")

        # Extracted template details
        safe_tid = html.escape(record.template_id)
        safe_ttext = html.escape(record.template_text)
        tmpl_html = (
            f'<div style="background:{COLOR_CANVAS};border:1px solid {COLOR_BORDER};'
            f'border-radius:6px;padding:10px 12px;font-size:12px;margin-top:8px;">'
            f'<strong>Extracted Template ID:</strong> <span style="font-family:monospace;'
            f'background:#E5EBF2;padding:1px 5px;border-radius:3px;font-weight:600;">'
            f'{safe_tid}</span><br><div style="margin-top:4px;"><strong>Template Pattern:'
            f'</strong> <span style="font-family:monospace;color:{COLOR_INK};">{safe_ttext}'
            f'</span></div></div>'
        )
        st.markdown(tmpl_html, unsafe_allow_html=True)

    with col_right:
        st.markdown(
            f"<div style='font-size:14px;font-weight:700;color:{COLOR_INK};margin-bottom:8px;'>"
            f"🧠 Operational Context & Response Guidance"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Operational Impact
        impact_html = (
            f'<div style="background:{COLOR_SURFACE};border:1px solid {COLOR_BORDER};'
            f'border-left:4px solid {COLOR_ACCENT};border-radius:6px;padding:12px;'
            f'margin-bottom:12px;">'
            f'<div style="font-size:12px;font-weight:700;color:{COLOR_INK};margin-bottom:4px;">'
            f'💼 Operational & Business Impact</div>'
            f'<div style="font-size:12px;color:{COLOR_INK};line-height:1.45;">'
            f'{html.escape(record.business_impact)}</div></div>'
        )
        st.markdown(impact_html, unsafe_allow_html=True)

        # Sequence transition context
        if record.expected_templates:
            expected_html = ", ".join(
                f'<span style="font-family:monospace;background:#E5EBF2;padding:1px 5px;'
                f'border-radius:3px;">{html.escape(t)}</span>'
                for t in record.expected_templates
            )
        else:
            expected_html = "<em>None (First event or standard baseline)</em>"

        transition_html = (
            f'<div style="background:{COLOR_SURFACE};border:1px solid {COLOR_BORDER};'
            f'border-left:4px solid #FF8A00;border-radius:6px;padding:12px;margin-bottom:12px;">'
            f'<div style="font-size:12px;font-weight:700;color:{COLOR_INK};margin-bottom:4px;">'
            f'🔄 Sequence Transition Context</div>'
            f'<div style="font-size:12px;color:{COLOR_INK};line-height:1.45;">'
            f'<strong>Observed Template:</strong> <span style="font-family:monospace;'
            f'background:#E5EBF2;padding:1px 5px;border-radius:3px;font-weight:600;">'
            f'{safe_tid}</span><br><div style="margin-top:4px;">'
            f'<strong>Expected Normal Next Templates:</strong> {expected_html}</div></div></div>'
        )
        st.markdown(transition_html, unsafe_allow_html=True)

        # Recommended Action
        action_html = (
            f'<div style="background:{COLOR_SURFACE};border:1px solid {COLOR_BORDER};'
            f'border-left:4px solid {COLOR_READY};border-radius:6px;padding:12px;">'
            f'<div style="font-size:12px;font-weight:700;color:{COLOR_INK};margin-bottom:4px;">'
            f'🛡️ Recommended SOC / SRE Response Action</div>'
            f'<div style="font-size:12px;color:{COLOR_INK};line-height:1.45;">'
            f'{html.escape(record.soc_action)}</div></div>'
        )
        st.markdown(action_html, unsafe_allow_html=True)
