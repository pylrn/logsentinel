from __future__ import annotations

import html
from typing import TYPE_CHECKING

import streamlit as st

from logsentinel.ui.components.empty_state import render_empty_state
from logsentinel.ui.components.score_breakdown import render_score_breakdown
from logsentinel.ui.styles import COLOR_BORDER, COLOR_MUTED, get_tone_badge_html

if TYPE_CHECKING:
    from collections.abc import Callable

    from logsentinel.ui.models import Incident


def render_incident_inspector(
    incident: Incident | None,
    on_feedback_callback: Callable[[str, str], None] | None = None,
    key_prefix: str = "incident_inspector",
) -> None:
    """Render comprehensive diagnostics, sequence context, and feedback controls for an incident."""
    if incident is None:
        render_empty_state(
            title="No Incident Selected",
            message=(
                "Select an incident from the timeline or table to inspect its sequence history, "
                "template extraction, and attribution breakdown."
            ),
            icon="🔍",
            key_prefix=f"{key_prefix}_empty",
        )
        return

    # Header with metadata badges
    tone_badge = get_tone_badge_html(incident.tone, incident.score)
    safe_id = html.escape(incident.id)
    safe_source = html.escape(incident.source)
    safe_signal = html.escape(incident.signal)
    safe_status = html.escape(incident.status)
    safe_time = html.escape(incident.time)
    safe_env = html.escape(incident.environment.upper())

    st.markdown(
        f"""
        <div style="border-bottom: 1px solid {COLOR_BORDER};
                    padding-bottom: 12px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between;
                        align-items: center; margin-bottom: 8px;">
                <span style="font-size: 18px; font-weight: 700;
                             color: #142033;">Incident #{safe_id}</span>
                <span>{tone_badge}</span>
            </div>
            <div style="font-size: 13px; color: {COLOR_MUTED};
                        display: flex; flex-wrap: wrap; gap: 16px;">
                <span><strong>Time:</strong> {safe_time}</span>
                <span><strong>Source:</strong> {safe_source}</span>
                <span><strong>Env:</strong> {safe_env}</span>
                <span><strong>Status:</strong> {safe_status}</span>
                <span><strong>Signal:</strong> {safe_signal}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Redacted log message
    st.markdown(
        "<strong>Sanitized Raw Log</strong> (Tenant PII/IP Redacted)",
        unsafe_allow_html=True,
    )
    st.code(incident.raw_message_redacted, language="text")

    # Template Information
    col_tid, col_ttext = st.columns([1, 3])
    with col_tid:
        st.markdown(
            f"<strong>Template ID:</strong> <code>{html.escape(incident.template_id)}</code>",
            unsafe_allow_html=True,
        )
    with col_ttext:
        safe_ttype = html.escape(incident.template_text)
        st.markdown(
            f"<strong>Template Pattern:</strong> <code>{safe_ttype}</code>",
            unsafe_allow_html=True,
        )

    # Sequence History and Predictions
    if incident.context_sequence or incident.expected_templates:
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        col_ctx, col_pred = st.columns(2)
        with col_ctx:
            ctx_items = (
                " → ".join(f"<code>{html.escape(t)}</code>" for t in incident.context_sequence)
                if incident.context_sequence
                else "<em>None</em>"
            )
            st.markdown(
                f"<div style='font-size: 13px;'>"
                f"<strong>Historical Sequence Context (K=10):</strong><br>{ctx_items}"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_pred:
            expected_items = (
                ", ".join(f"<code>{html.escape(t)}</code>" for t in incident.expected_templates)
                if incident.expected_templates
                else "<em>None</em>"
            )
            st.markdown(
                f"<div style='font-size: 13px;'>"
                f"<strong>Expected Next Templates (Neural Top-K):</strong><br>{expected_items}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Score breakdown
    if incident.contributions:
        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
        render_score_breakdown(incident.contributions)

    # Feedback & Triage Action Controls
    st.markdown(
        "<div style='margin-top: 16px; border-top: 1px solid #DCE3EC; padding-top: 12px;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<strong>Operator Triage & Feedback</strong>", unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button(
            "Acknowledge", key=f"{key_prefix}_ack_{incident.id}", width="stretch"
        ):
            if on_feedback_callback:
                on_feedback_callback(incident.id, "acknowledge")
            st.toast(f"Incident #{incident.id} marked as Acknowledged")

    with col_btn2:
        if st.button(
            "Confirm Anomaly", key=f"{key_prefix}_confirm_{incident.id}", width="stretch"
        ):
            if on_feedback_callback:
                on_feedback_callback(incident.id, "confirm")
            st.toast(f"Incident #{incident.id} Confirmed as True Anomaly")

    with col_btn3:
        if st.button(
            "Mark False Positive", key=f"{key_prefix}_fp_{incident.id}", width="stretch"
        ):
            if on_feedback_callback:
                on_feedback_callback(incident.id, "false_positive")
            st.toast(f"Incident #{incident.id} labeled as False Positive")
