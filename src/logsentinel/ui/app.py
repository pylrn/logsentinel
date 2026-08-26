from __future__ import annotations

from typing import Any

import streamlit as st

from logsentinel.ui.client import ApiConnectionError, DashboardApiClient
from logsentinel.ui.components.error_state import render_error_state
from logsentinel.ui.components.status_header import render_status_header
from logsentinel.ui.fixtures import get_bgl_demo_data, get_hdfs_demo_data
from logsentinel.ui.models import AppMode, ModelStatus
from logsentinel.ui.styles import get_theme_css
from logsentinel.ui.views import (
    render_diagnostics_view,
    render_onboarding_view,
    render_overview_view,
    render_pipeline_view,
    render_showcase_view,
)

WORKSPACE_OPTIONS: list[str] = [
    "🔬 Model Proof & Generalization Showcase",
    "1. What is happening? (Overview)",
    "2. Why was this flagged? (Pipeline)",
    "3. How is the model performing? (Diagnostics)",
    "4. How would my company use it? (Onboarding & Feedback)",
]
NAV_QUESTIONS: list[str] = WORKSPACE_OPTIONS


def main(
    api_url: str = "http://127.0.0.1:8000",
    default_env: str = "hdfs",
    default_mode: AppMode = AppMode.DEMO,
) -> None:
    """Main UI entrypoint for LogSentinel dashboard."""
    st.set_page_config(
        page_title="LogSentinel | Neural Anomaly Detection",
        page_icon="🛡️",
        layout="wide",
    )
    st.markdown(get_theme_css(), unsafe_allow_html=True)

    if "environment" not in st.session_state:
        st.session_state["environment"] = default_env
    if "mode" not in st.session_state:
        st.session_state["mode"] = default_mode
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = WORKSPACE_OPTIONS[0]

    with st.sidebar:
        st.markdown(
            "<div class='brand-header'>🛡️ LogSentinel</div>",
            unsafe_allow_html=True,
        )
        current_tab = st.session_state.get("active_tab", WORKSPACE_OPTIONS[0])
        tab_idx = (
            WORKSPACE_OPTIONS.index(current_tab)
            if current_tab in WORKSPACE_OPTIONS
            else 0
        )
        selected_tab = st.sidebar.selectbox(
            "Workspace",
            WORKSPACE_OPTIONS,
            index=tab_idx,
            key="nav_workspace_select",
        )
        if not isinstance(selected_tab, str):
            radio_val = st.radio(
                "Navigation",
                WORKSPACE_OPTIONS,
                index=tab_idx,
                key="nav_workspace_radio",
            )
            selected_tab = (
                radio_val if isinstance(radio_val, str) else WORKSPACE_OPTIONS[0]
            )

        st.session_state["active_tab"] = selected_tab
        st.markdown(
            "<div class='rail-footer'>"
            "LogSentinel v0.1.0<br>Zero-Leakage Neural Anomaly Detection"
            "</div>",
            unsafe_allow_html=True,
        )

    current_env = str(st.session_state.get("environment", default_env))
    raw_mode = st.session_state.get("mode", default_mode)
    current_mode = (
        AppMode.LIVE
        if (isinstance(raw_mode, str) and raw_mode.lower() == "live")
        or raw_mode == AppMode.LIVE
        else AppMode.DEMO
    )

    environments = ["hdfs", "bgl"]

    if current_mode == AppMode.LIVE:
        client = DashboardApiClient(api_url)
        status_error: Exception | None = None
        try:
            status = client.status(current_env)
        except (ApiConnectionError, Exception) as exc:
            status = ModelStatus(
                name=current_env,
                version="unavailable",
                model_kind="live-service",
                status="offline",
                threshold=0.50,
            )
            status_error = exc

        selected_env, selected_mode = render_status_header(
            status=status,
            current_env=current_env,
            current_mode=AppMode.LIVE,
            environments=environments,
        )
        st.session_state["environment"] = selected_env
        st.session_state["mode"] = selected_mode

        if status_error is not None:
            render_error_state(
                error=status_error,
                api_url=api_url,
                key_prefix="app_live_status_error",
            )
            return

        state: dict[str, Any] = {
            "mode": AppMode.LIVE,
            "environment": selected_env,
            "status": status,
            "timeline": [],
            "incidents": [],
        }
    else:
        demo_data = (
            get_hdfs_demo_data()
            if current_env == "hdfs"
            else get_bgl_demo_data()
        )
        status = demo_data.get("status") or ModelStatus(
            name=current_env,
            version="demo-v1",
            model_kind="hybrid-transformer",
            status="ready",
            threshold=0.80,
        )
        selected_env, selected_mode = render_status_header(
            status=status,
            current_env=current_env,
            current_mode=AppMode.DEMO,
            environments=environments,
        )
        st.session_state["environment"] = selected_env
        st.session_state["mode"] = selected_mode

        if selected_env != current_env:
            demo_data = (
                get_hdfs_demo_data()
                if selected_env == "hdfs"
                else get_bgl_demo_data()
            )
            current_env = selected_env

        state = demo_data
        client = None

    active_tab = st.session_state.get("active_tab", WORKSPACE_OPTIONS[0])
    target_env = st.session_state.get("environment", current_env)

    if (
        active_tab == "🔬 Model Proof & Generalization Showcase"
        or "Showcase" in str(active_tab)
    ):
        render_showcase_view(state=state, client=client, environment=selected_env)
    elif (
        active_tab == "1. What is happening? (Overview)"
        or active_tab == "What is happening?"
        or "Overview" in str(active_tab)
    ):
        render_overview_view(state=state, client=client, environment=target_env)
    elif (
        active_tab == "2. Why was this flagged? (Pipeline)"
        or active_tab == "Why was this flagged?"
        or "Pipeline" in str(active_tab)
    ):
        render_pipeline_view(state=state, client=client, environment=target_env)
    elif (
        active_tab == "3. How is the model performing? (Diagnostics)"
        or active_tab == "How is the model performing?"
        or "Diagnostics" in str(active_tab)
    ):
        render_diagnostics_view(state=state, client=client, environment=target_env)
    elif (
        active_tab == "4. How would my company use it? (Onboarding & Feedback)"
        or active_tab == "How would my company use it?"
        or "Onboarding" in str(active_tab)
    ):
        render_onboarding_view(state=state, client=client, environment=target_env)
    else:
        render_overview_view(state=state, client=client, environment=target_env)


if __name__ == "__main__":
    main()
