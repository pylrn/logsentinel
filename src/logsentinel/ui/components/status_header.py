from __future__ import annotations

import streamlit as st

from logsentinel.ui.models import AppMode, ModelStatus
from logsentinel.ui.styles import COLOR_READY


def render_status_header(
    status: ModelStatus,
    current_env: str,
    current_mode: AppMode,
    environments: list[str],
) -> tuple[str, AppMode]:
    """Render top-level operational status bar and environment/mode selector controls.

    Parameters
    ----------
    status : ModelStatus
        Current status metadata for the selected model/environment.
    current_env : str
        Currently active environment (e.g. 'hdfs' or 'bgl').
    current_mode : AppMode
        Current operational mode (Live or Demo).
    environments : list[str]
        List of selectable environment identifiers.

    Returns
    -------
    tuple[str, AppMode]
        The newly selected (or retained) environment string and AppMode.
    """
    env_index = environments.index(current_env) if current_env in environments else 0
    mode_index = 0 if current_mode == AppMode.LIVE else 1

    col_env, col_mode, col_info, col_metrics = st.columns(
        [1.2, 1.2, 2.0, 2.0], gap="medium"
    )

    with col_env:
        selected_env = st.selectbox(
            "Environment",
            environments,
            index=env_index,
            format_func=str.upper,
            key="status_header_env_select",
        )

    with col_mode:
        selected_mode_str = st.radio(
            "Operation Mode",
            ["Live", "Demo"],
            index=mode_index,
            horizontal=True,
            key="status_header_mode_radio",
        )
        selected_mode = (
            AppMode.LIVE if selected_mode_str.lower() == "live" else AppMode.DEMO
        )

    with col_info:
        is_ready = status.status.lower() in ("ready", "active", "online")
        status_color = COLOR_READY if is_ready else "#FF8A00"
        status_badge = (
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background-color:{status_color};margin-right:6px;"></span>'
            f"<strong>{status.status.upper()}</strong>"
        )
        st.markdown(
            f"<div style='font-size: 13px; line-height: 1.6; padding-top: 4px;'>"
            f"<div><strong>Model:</strong> {status.name} ({status.version})</div>"
            f"<div><strong>Kind:</strong> {status.model_kind} | {status_badge}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_metrics:
        st.markdown(
            f"<div style='font-size: 13px; line-height: 1.6; padding-top: 4px;'>"
            f"<div><strong>Threshold:</strong> {status.threshold:.2f}</div>"
            f"<div><strong>Events Indexed:</strong> {status.events_indexed:,} | "
            f"<strong>Vocab:</strong> {status.vocabulary_size}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    return selected_env, selected_mode
