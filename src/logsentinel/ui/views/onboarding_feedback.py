from __future__ import annotations

import json
from typing import Any

import streamlit as st

from logsentinel.ui.client import DashboardApiClient
from logsentinel.ui.components.pipeline_stepper import render_pipeline_stepper
from logsentinel.ui.models import AppMode, TenantOnboardingStep


def render_onboarding_view(
    state: dict[str, Any],
    client: DashboardApiClient | None = None,
    environment: str = "hdfs",
) -> None:
    """Render the 'How would my company use it?' tenant onboarding & feedback workspace."""
    mode = state.get("mode", AppMode.DEMO)
    is_live = mode == AppMode.LIVE or mode == "live"

    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <h2 style="margin-bottom: 4px; font-weight: 700;">
                Enterprise Onboarding & Human-in-the-Loop Feedback
            </h2>
            <div style="color: #637083; font-size: 14px;">
                How would my company use it? Safe tenant-isolated onboarding with strict
                zero-leakage boundaries, coupled with continuous analyst feedback.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. 5-Stage Tenant Onboarding Journey
    st.markdown("### Tenant Onboarding Architecture")

    default_onboarding = [
        TenantOnboardingStep(
            step_index=1,
            title="Redact",
            description="Scrub IPs, tokens, block IDs, and sensitive PII",
            status="Done",
            isolation_boundary="Tenant-isolated regex boundary at ingress",
        ),
        TenantOnboardingStep(
            step_index=2,
            title="Parse",
            description="Mine templates deterministically via Drain3",
            status="Done",
            isolation_boundary="Frozen vocabulary; zero cross-tenant template mixing",
        ),
        TenantOnboardingStep(
            step_index=3,
            title="Train Adapter",
            description="Learn tenant-specific normal sequence patterns",
            status="Done",
            isolation_boundary="Tenant-isolated LoRA weights; base LLM remains frozen",
        ),
        TenantOnboardingStep(
            step_index=4,
            title="Calibrate",
            description="Tune threshold on held-out normal sequences",
            status="Done",
            isolation_boundary="Tenant-specific isotonic threshold curve",
        ),
        TenantOnboardingStep(
            step_index=5,
            title="Deploy",
            description="Serve low-latency real-time inference via FastAPI",
            status="Done",
            isolation_boundary="Local zero-leakage serving; memory-isolated instances",
        ),
    ]

    onboarding_steps: list[TenantOnboardingStep] = state.get("onboarding", default_onboarding)

    stepper_data = [
        {
            "title": f"{step.step_index}. {step.title}",
            "status": step.status.lower(),
            "details": step.description,
        }
        for step in onboarding_steps
    ]
    render_pipeline_stepper(stepper_data)

    # Tenant Isolation Details
    with st.expander("🛡️ Enterprise Multi-Tenant Isolation Boundaries", expanded=True):
        for step in onboarding_steps:
            st.markdown(
                f"""
                <div style="margin-bottom: 8px; font-size: 13px;">
                    <strong>Stage {step.step_index}: {step.title}</strong> —
                    <span style="color: #0B6CFB; font-weight: 600;">Isolation Boundary:</span>
                    <code>{step.isolation_boundary}</code><br>
                    <span style="color: #637083;">{step.description}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 2. Analyst Feedback Loop & Submission
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    st.markdown("### Analyst Triage & Feedback Loop")
    st.markdown(
        "<div style='color: #637083; font-size: 13px; margin-bottom: 12px;'>"
        "Submit domain operator corrections to refine downstream threshold "
        "calibration and LoRA adapter fine-tuning."
        "</div>",
        unsafe_allow_html=True,
    )

    col_id, col_label = st.columns(2)
    with col_id:
        incident_id = st.text_input(
            "Incident ID / Alert Reference",
            value="HDFS-INC-21" if environment == "hdfs" else "BGL-INC-21",
            key="onboarding_feedback_incident_id",
        )
    with col_label:
        feedback_type = st.selectbox(
            "Feedback Classification",
            options=["True Anomaly", "False Positive", "Needs Investigation", "Acknowledged"],
            key="onboarding_feedback_type",
        )

    reason = st.text_area(
        "Analyst Notes & Context (Optional)",
        placeholder=(
            "Provide operator context, e.g., 'Planned cluster maintenance at 02:00 UTC "
            "caused expected burst.'"
        ),
        key="onboarding_feedback_reason",
    )

    col_submit, col_export = st.columns([2, 2])

    feedback_payload = {
        "environment": environment,
        "incident_id": incident_id,
        "feedback": feedback_type,
        "reason": reason,
    }

    with col_submit:
        if st.button("Submit Analyst Feedback", key="onboarding_submit_btn", width="stretch"):
            if is_live and client is not None:
                try:
                    client.submit_feedback(
                        environment=environment,
                        incident_id=incident_id,
                        feedback=feedback_type,
                        reason=reason,
                    )
                    st.toast(f"Feedback successfully recorded for Incident #{incident_id}!")
                except Exception as exc:
                    st.error(f"Live feedback submission failed: {exc}")
            else:
                st.toast(f"Feedback recorded locally for Incident #{incident_id} (Demo Mode)!")

    with col_export:
        feedback_export_data = json.dumps([feedback_payload], indent=2)
        st.download_button(
            label="📥 Export Analyst Feedback (JSON)",
            data=feedback_export_data,
            file_name=f"logsentinel_feedback_{environment}.json",
            mime="application/json",
            key="onboarding_export_btn",
            width="stretch",
        )
