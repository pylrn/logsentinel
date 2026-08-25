from __future__ import annotations

import html
from typing import TYPE_CHECKING

import streamlit as st

from logsentinel.ui.styles import COLOR_ANOMALY_HIGH

if TYPE_CHECKING:
    from collections.abc import Callable


def render_error_state(
    error: Exception | str,
    api_url: str = "http://127.0.0.1:8000",
    retry_callback: Callable[[], None] | None = None,
    key_prefix: str = "error_state",
) -> bool:
    """Render a prominent, accessible error state banner with connection troubleshooting guidance.

    Parameters
    ----------
    error : Exception | str
        Error instance or descriptive error message string.
    api_url : str
        Target API URL where the connection failed or encountered error.
    retry_callback : Callable[[], None] | None
        Optional callback triggered when the user clicks 'Retry Connection'.
    key_prefix : str
        Unique prefix for Streamlit widget keys.

    Returns
    -------
    bool
        True if the retry action button was clicked, False otherwise.
    """
    error_message = str(error)
    safe_error = html.escape(error_message)
    safe_url = html.escape(api_url)

    st.markdown(
        f"""
        <div class="error-banner" style="
            background: #FDE8E8;
            border-left: 4px solid {COLOR_ANOMALY_HIGH};
            border-radius: 6px;
            padding: 16px 20px;
            margin-bottom: 16px;
            color: #9B1C1C;
        ">
            <div style="font-size: 15px; font-weight: 700; display: flex;
                        align-items: center; gap: 8px; margin-bottom: 6px;">
                <span>⚠️ Connection / Operational Error</span>
            </div>
            <div style="font-size: 13px; line-height: 1.5; color: #771D1D;">
                Failed to communicate with LogSentinel API at <code>{safe_url}</code>.
            </div>
            <div style="font-size: 12px; margin-top: 8px; font-family: monospace;
                        background: #FBD5D5; padding: 6px 10px; border-radius: 4px;">
                {safe_error}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🛠️ Connection Troubleshooting Steps", expanded=False):
        st.markdown(
            f"""
            1. **Verify Backend Server is Running:**
               ```bash
               # Run FastAPI backend locally
               uvicorn logsentinel.api:app --host 127.0.0.1 --port 8000
               ```
            2. **Check Target API URL:** Current URL is `{safe_url}`.
               Adjust `--api-url` or `LOGSENTINEL_API_URL` if server is on a different port/host.
            3. **Health Check Endpoint:** Verify `curl {safe_url}/v1/health` returns `200 OK`.
            4. **Switch to Demo Mode:** Toggle to 'Demo Mode' in the status bar to inspect
               historical benchmark traces and precomputed offline fixtures.
            """
        )

    clicked = False
    col_retry, _col_spacer = st.columns([1.5, 4])
    with col_retry:
        if st.button("🔄 Retry Connection", key=f"{key_prefix}_retry_btn", width="stretch"):
            clicked = True
            if retry_callback is not None:
                retry_callback()

    return clicked
