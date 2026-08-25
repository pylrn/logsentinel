from __future__ import annotations

import html

import streamlit as st

from logsentinel.ui.styles import COLOR_BORDER, COLOR_MUTED, COLOR_SURFACE


def render_empty_state(
    title: str,
    message: str,
    action_label: str | None = None,
    icon: str = "ℹ️",
    key_prefix: str = "empty_state",
) -> bool:
    """Render an accessible, clean empty state callout box.

    Parameters
    ----------
    title : str
        Header text for the empty state.
    message : str
        Descriptive explanation or instructions.
    action_label : str | None
        Optional button label for call-to-action.
    icon : str
        Unicode icon or emoji to represent the state.
    key_prefix : str
        Unique prefix for Streamlit widget keys.

    Returns
    -------
    bool
        True if the action button was clicked, False otherwise.
    """
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    safe_icon = html.escape(icon)

    st.markdown(
        f"""
        <div style="
            background: {COLOR_SURFACE};
            border: 1px dashed {COLOR_BORDER};
            border-radius: 8px;
            padding: 32px 20px;
            text-align: center;
            margin: 12px 0;
        ">
            <div style="font-size: 32px; margin-bottom: 8px;">{safe_icon}</div>
            <div style="font-size: 16px; font-weight: 600; color: #142033; margin-bottom: 6px;">
                {safe_title}
            </div>
            <div style="font-size: 13px; color: {COLOR_MUTED};
                        max-width: 480px; margin: 0 auto 12px;">
                {safe_message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if action_label:
        col_l, col_btn, col_r = st.columns([2, 1.5, 2])
        with col_btn:
            return bool(st.button(action_label, key=f"{key_prefix}_action_btn", width="stretch"))

    return False
