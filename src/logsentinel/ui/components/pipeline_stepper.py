from __future__ import annotations

import html
from typing import Any

import streamlit as st

from logsentinel.ui.styles import COLOR_BORDER, COLOR_MUTED, COLOR_SURFACE


def _get_status_badge(status: str) -> tuple[str, str, str]:
    """Return background, text color, and symbol for step status."""
    st_clean = status.lower().replace(" ", "_")
    if st_clean in ("done", "completed", "complete", "success"):
        return "#E8F8F0", "#085E3B", "✔"
    if st_clean in ("in_progress", "running", "active", "processing"):
        return "#E6F0FE", "#0B6CFB", "⏳"
    if st_clean in ("failed", "error"):
        return "#FDE8E8", "#9B1C1C", "✖"
    return "#F0F4F8", "#637083", "○"


def render_pipeline_stepper(steps_data: list[dict[str, Any]]) -> None:
    """Render a horizontal stepper component showing status across pipeline stages."""
    if not steps_data:
        return

    cols = st.columns(len(steps_data), gap="small")
    for idx, (col, step) in enumerate(zip(cols, steps_data, strict=False)):
        title = step.get("title", step.get("name", f"Step {idx + 1}"))
        status = step.get("status", "pending")
        details = step.get("details", step.get("description", ""))

        bg_color, text_color, symbol = _get_status_badge(status)
        safe_title = html.escape(str(title))
        safe_status = html.escape(str(status).capitalize())
        safe_details = html.escape(str(details))

        with col:
            st.markdown(
                f"""
                <div style="
                    background: {COLOR_SURFACE};
                    border: 1px solid {COLOR_BORDER};
                    border-top: 3px solid {text_color};
                    border-radius: 6px;
                    padding: 12px;
                    min-height: 110px;
                ">
                    <div style="display: flex; justify-content: space-between;
                                align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 11px; font-weight: 700;
                                     color: {COLOR_MUTED}; text-transform: uppercase;">
                            Step {idx + 1}
                        </span>
                        <span style="
                            font-size: 11px;
                            font-weight: 600;
                            background: {bg_color};
                            color: {text_color};
                            padding: 1px 6px;
                            border-radius: 4px;
                        ">
                            {symbol} {safe_status}
                        </span>
                    </div>
                    <div style="font-size: 13px; font-weight: 600;
                                color: #142033; margin-bottom: 4px;">
                        {safe_title}
                    </div>
                    <div style="font-size: 11px; color: {COLOR_MUTED}; line-height: 1.4;">
                        {safe_details}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_log_pipeline_journey(
    raw_log: str,
    redacted_log: str,
    template_id: str,
    template_text: str,
    context: list[str],
    predictions: list[str],
    contributions: dict[str, float],
    fused_score: float,
) -> None:
    """Render an interactive 5-stage log event journey diagram from raw text to anomaly score."""
    stages = [
        {"title": "1. Ingestion", "status": "completed", "details": "Raw event captured"},
        {"title": "2. Redaction", "status": "completed", "details": "PII / IP scrubbed"},
        {
            "title": "3. Drain3 Parser",
            "status": "completed",
            "details": f"Template {template_id}",
        },
        {
            "title": "4. Context Window",
            "status": "completed",
            "details": f"Window length {len(context)}",
        },
        {
            "title": "5. Score Fusion",
            "status": "completed",
            "details": f"Score: {fused_score:.2f}",
        },
    ]

    render_pipeline_stepper(stages)

    with st.expander("🔍 Detailed Pipeline Transformations", expanded=True):
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("<strong>Stage 1: Raw Ingested Log</strong>", unsafe_allow_html=True)
            st.code(raw_log, language="text")
        with col_t2:
            st.markdown(
                "<strong>Stage 2: Sanitized / Redacted Text</strong>",
                unsafe_allow_html=True,
            )
            st.code(redacted_log, language="text")

        col_t3, col_t4 = st.columns(2)
        with col_t3:
            st.markdown(
                f"<strong>Stage 3: Extracted Template</strong><br>"
                f"ID: <code>{html.escape(template_id)}</code><br>"
                f"Pattern: <code>{html.escape(template_text)}</code>",
                unsafe_allow_html=True,
            )
        with col_t4:
            ctx_str = (
                " → ".join(f"<code>{html.escape(t)}</code>" for t in context)
                if context
                else "<em>Empty</em>"
            )
            pred_str = (
                ", ".join(f"<code>{html.escape(t)}</code>" for t in predictions)
                if predictions
                else "<em>None</em>"
            )
            st.markdown(
                f"<strong>Stage 4: Sequence Context & Prediction</strong><br>"
                f"Context: {ctx_str}<br>"
                f"Top Predicted: {pred_str}",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<strong>Stage 5: Final Ensemble Score:</strong> <code>{fused_score:.3f}</code>",
            unsafe_allow_html=True,
        )
