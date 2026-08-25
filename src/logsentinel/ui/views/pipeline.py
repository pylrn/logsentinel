from __future__ import annotations

import re
from typing import Any

import streamlit as st

from logsentinel.privacy import Redactor
from logsentinel.ui.client import DashboardApiClient
from logsentinel.ui.components.pipeline_stepper import render_log_pipeline_journey
from logsentinel.ui.components.score_breakdown import render_score_breakdown
from logsentinel.ui.models import Incident


def _derive_template(redacted: str) -> tuple[str, str]:
    """Derive deterministic template ID and pattern from redacted log text."""
    pattern = re.sub(r"<[A-Z0-9_-]+>", "<*>", redacted)
    # Generate clean short template ID
    cleaned = "".join(c for c in pattern if c.isalnum() or c in " _-")[:24]
    tid = f"T_{abs(hash(cleaned)) % 10000:04d}"
    return tid, pattern


def render_pipeline_view(
    state: dict[str, Any],
    client: DashboardApiClient | None = None,
    environment: str = "hdfs",
) -> None:
    """Render the 'Why was this flagged?' diagnostic log transformation workspace."""
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <h2 style="margin-bottom: 4px; font-weight: 700;">Diagnostic Pipeline Journey</h2>
            <div style="color: #637083; font-size: 14px;">
                Why was this flagged? Trace each log event through the 5-stage
                transformation pipeline from raw text to ensemble anomaly score.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    incidents: list[Incident] = state.get("incidents", [])
    redactor = Redactor()

    options: list[str | int] = []
    option_labels: dict[str | int, str] = {}

    for idx, inc in enumerate(incidents):
        options.append(idx)
        tone_val = inc.tone.value if hasattr(inc.tone, "value") else str(inc.tone)
        severity = tone_val.capitalize()
        option_labels[idx] = (
            f"Incident #{inc.id} ({severity} Severity - Score {inc.score:.2f}) - {inc.signal}"
        )

    options.append("Custom Raw Log Input")
    option_labels["Custom Raw Log Input"] = "✏️ Custom Raw Log Input (Test Arbitrary Log)"

    selected_choice = st.selectbox(
        "Choose a Sample Incident or Custom Input to Trace",
        options=options,
        format_func=lambda opt: option_labels.get(opt, str(opt)),
        key="pipeline_sample_selector",
    )

    if selected_choice == "Custom Raw Log Input":
        default_custom = (
            "10.251.43.115 [WARN] DataNode-3: blk_-1073741829 CRC error block verification timeout"
            if environment == "hdfs"
            else "FATAL 192.168.1.50 R02-M1-N0-C:J12-U11 kernel panic buffer overrun at 0xdeadbeef"
        )
        custom_raw = st.text_area(
            "Enter Raw Unredacted Log Event",
            value=default_custom,
            key="pipeline_custom_raw_input",
        )
        raw_log = custom_raw
        redacted_log = redactor.redact(raw_log)
        template_id, template_text = _derive_template(redacted_log)
        context = ["INIT_001", "BOOT_004", template_id]
        predictions = ["NORMAL_ACK", "HEARTBEAT_OK"]
        contributions = {
            "Rarity": 0.40,
            "PCA": 0.25,
            "Isolation Forest": 0.15,
            "Transformer": 0.20,
        }
        has_error = any(kw in raw_log for kw in ("ERROR", "FATAL", "panic", "WARN"))
        fused_score = 0.88 if has_error else 0.22
    else:
        incident: Incident = incidents[int(selected_choice)]
        raw_log = f"[{incident.time}] {incident.source}: {incident.raw_message_redacted}"
        redacted_log = incident.raw_message_redacted
        template_id = incident.template_id
        template_text = incident.template_text
        context = incident.context_sequence
        predictions = incident.expected_templates
        contributions = incident.contributions or {
            "Rarity": 0.35,
            "PCA": 0.25,
            "Isolation Forest": 0.20,
            "Transformer": 0.20,
        }
        fused_score = incident.score

    # Render 5-stage transformation journey stepper & transformations
    render_log_pipeline_journey(
        raw_log=raw_log,
        redacted_log=redacted_log,
        template_id=template_id,
        template_text=template_text,
        context=context,
        predictions=predictions,
        contributions=contributions,
        fused_score=fused_score,
    )

    # Detailed Ensemble Contribution Breakdown
    st.markdown("### Ensemble Model Contribution Breakdown")
    render_score_breakdown(contributions)
