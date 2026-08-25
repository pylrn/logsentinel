from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from logsentinel.ui.client import ApiConnectionError, DashboardApiClient
from logsentinel.ui.components.anomaly_timeline import render_anomaly_timeline
from logsentinel.ui.components.empty_state import render_empty_state
from logsentinel.ui.components.error_state import render_error_state
from logsentinel.ui.components.incident_inspector import render_incident_inspector
from logsentinel.ui.models import AppMode, Incident, score_tone


def render_overview_view(
    state: dict[str, Any],
    client: DashboardApiClient | None = None,
    environment: str = "hdfs",
) -> None:
    """Render the 'What is happening?' operational incident workspace."""
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <h2 style="margin-bottom: 4px; font-weight: 700;">Operational Incident Overview</h2>
            <div style="color: #637083; font-size: 14px;">
                What is happening right now across fleet sequences, anomalies, and active alerts.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mode = state.get("mode", AppMode.DEMO)
    is_live = mode == AppMode.LIVE or mode == "live"

    incidents: list[Incident] = []
    timeline = state.get("timeline", [])

    if is_live and client is not None:
        try:
            incidents = client.anomalies(environment, limit=100)
        except ApiConnectionError as exc:
            render_error_state(
                error=exc,
                api_url=getattr(client, "base_url", "http://127.0.0.1:8000"),
                key_prefix="overview_api_err",
            )
            return
        except Exception as exc:
            render_error_state(
                error=exc,
                api_url=getattr(client, "base_url", "http://127.0.0.1:8000"),
                key_prefix="overview_unhandled_err",
            )
            return
    else:
        incidents = state.get("incidents", [])

    # 1. 24h Fleet Timeline
    if timeline:
        st.markdown("### 24-Hour Fleet Anomaly Activity")
        render_anomaly_timeline(timeline)

    # 2. Detected Incidents & Inspector
    st.markdown("### Detected Incidents & Anomalies")

    if not incidents:
        render_empty_state(
            title="No Active Incidents Detected",
            message=(
                "All monitored node sequences and template patterns are within baseline bounds. "
                "No anomalous events currently require operator triage."
            ),
            icon="✔",
            key_prefix="overview_no_incidents",
        )
    else:
        # Incident table preview
        incident_rows = [
            {
                "ID": inc.id,
                "Time": inc.time,
                "Source": inc.source,
                "Score": f"{inc.score:.3f}",
                "Severity": inc.tone.value.capitalize()
                if hasattr(inc.tone, "value")
                else str(inc.tone).capitalize(),
                "Signal": inc.signal,
                "Status": inc.status,
            }
            for inc in incidents
        ]
        df_incidents = pd.DataFrame(incident_rows)
        st.dataframe(df_incidents, width="stretch", hide_index=True)

        # Incident Selection & Inspection
        incident_ids = [inc.id for inc in incidents]
        selected_id = st.selectbox(
            "Select Incident to Inspect in Detail",
            options=incident_ids,
            index=0,
            key="overview_incident_selector",
        )

        selected_incident = next((inc for inc in incidents if inc.id == selected_id), None)

        def handle_operator_feedback(inc_id: str, feedback_type: str) -> None:
            if is_live and client is not None:
                try:
                    client.submit_feedback(
                        environment=environment,
                        incident_id=inc_id,
                        feedback=feedback_type,
                    )
                except Exception as fb_exc:
                    st.toast(f"Feedback submission failed: {fb_exc}")

        render_incident_inspector(
            incident=selected_incident,
            on_feedback_callback=handle_operator_feedback,
            key_prefix="overview_inspector",
        )

    # 3. Replay Sample Event & Log Ingestion
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    with st.expander("📥 Replay Sample Event / Ingest Logs", expanded=False):
        col_replay, col_upload = st.columns(2)

        with col_replay:
            st.markdown("<strong>Replay Single Log Event</strong>", unsafe_allow_html=True)
            replay_text = st.text_area(
                "Raw Log Message",
                value="Received block blk_-1073741829 from 10.251.43.115 status: ERROR_CRC",
                key="overview_replay_text",
            )
            if st.button("Score / Replay Event", key="overview_replay_btn", width="stretch"):
                if is_live and client is not None:
                    try:
                        res = client.score_events(
                            environment=environment,
                            events=[{"raw_message": replay_text, "source": "manual_replay"}],
                        )
                        st.success("Event scored successfully by Live Backend!")
                        st.json(res)
                    except Exception as score_exc:
                        st.error(f"Live scoring failed: {score_exc}")
                else:
                    has_error = "ERROR" in replay_text or "CRITICAL" in replay_text
                    simulated_score = 0.94 if has_error else 0.18
                    tone_name = score_tone(simulated_score).value.capitalize()
                    st.info(f"Simulated Score: {simulated_score:.3f} ({tone_name} Severity)")
                    st.json(
                        {
                            "status": "success",
                            "mode": "demo_simulation",
                            "score": simulated_score,
                            "explanation": "Simulated pipeline scoring result",
                        }
                    )

        with col_upload:
            st.markdown("<strong>Batch Log File Upload</strong>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Upload log file (.log, .txt, .json, .jsonl, .csv)",
                type=["log", "txt", "json", "jsonl", "csv"],
                key="overview_file_uploader",
            )
            if uploaded_file is not None:
                st.success(
                    f"File '{uploaded_file.name}' staged for batch processing "
                    f"({uploaded_file.size} bytes)."
                )
