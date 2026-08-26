"""Workspace view for LogSentinel Model Proof & Generalization Showcase.

Empirically demonstrates zero temporal data leakage, multi-domain generalization,
and causal operational impact across enterprise security, HDFS, and BGL environments.
"""

from __future__ import annotations

import html
import textwrap
from typing import TYPE_CHECKING, Any

import streamlit as st

from logsentinel.ui.components.showcase_components import (
    render_partition_health_cards,
    render_showcase_explainer,
    render_showcase_journey_stepper,
    render_showcase_log_table,
)
from logsentinel.ui.showcase_engine import load_showcase_profile
from logsentinel.ui.styles import COLOR_INK, COLOR_MUTED

if TYPE_CHECKING:
    from logsentinel.ui.client import DashboardApiClient

ENV_OPTIONS: list[tuple[str, str]] = [
    (
        "enterprise-security",
        "🏢 Enterprise Security (Simulated Testbed — AIT-LDS / CAM-LDS ATT&CK)",
    ),
    ("hdfs", "☁️ HDFS Cloud Storage (Public Loghub Benchmark — 11.18M Lines)"),
    ("bgl", "🖥️ BGL Supercomputing (Public Loghub Benchmark — 4.75M Lines)"),
]

ENV_DISPLAY_MAP: dict[str, str] = dict(ENV_OPTIONS)
ENV_KEY_MAP: dict[str, str] = {v: k for k, v in ENV_OPTIONS}
for k, _ in ENV_OPTIONS:
    ENV_KEY_MAP[k] = k


def render_showcase_view(
    state: dict[str, Any],
    client: DashboardApiClient | None = None,
    environment: str = "enterprise-security",
) -> None:
    """Render the Model Proof & Generalization Showcase workspace view."""
    # 1. Workspace Header
    header_html = textwrap.dedent(f"""
<div style="margin-bottom: 20px;">
    <h2 style="margin-bottom: 6px; font-weight: 700; color: {COLOR_INK};">
        🔬 Model Proof & Generalization Showcase
    </h2>
    <div style="color: {COLOR_MUTED}; font-size: 14px; line-height: 1.5;">
        Empirical proof of zero temporal data leakage, multi-domain generalization,
        and causal business impact across enterprise security, cloud storage,
        and supercomputing environments.
    </div>
</div>
    """).strip()
    st.markdown(header_html, unsafe_allow_html=True)

    # 2. Dataset Selector & Provenance Banner
    options = [k for k, _ in ENV_OPTIONS]
    default_idx = options.index(environment) if environment in options else 0

    selected_choice = st.selectbox(
        "Select Environment / Benchmark Profile",
        options=options,
        index=default_idx,
        format_func=lambda x: ENV_DISPLAY_MAP.get(x, x),
        key="showcase_env_selector",
    )

    env_id = ENV_KEY_MAP.get(selected_choice, selected_choice)
    try:
        profile = load_showcase_profile(env_id)
    except ValueError:
        profile = load_showcase_profile("enterprise-security")
        env_id = "enterprise-security"

    safe_provenance = html.escape(profile.provenance_note)
    safe_desc = html.escape(profile.description)
    provenance_html = textwrap.dedent(f"""
<div style="background:#FFF4E5;border:1px solid #FF8A00;border-left:4px solid #FF8A00;"""
        f"""border-radius:6px;padding:12px 16px;margin-top:8px;margin-bottom:20px;">
<div style="font-size:13px;font-weight:700;color:#994B00;margin-bottom:4px;">
📌 Dataset Provenance & Attribution: {safe_provenance}
</div>
<div style="font-size:12px;color:{COLOR_INK};line-height:1.45;">
{safe_desc}
</div>
</div>
    """).strip()
    st.markdown(provenance_html, unsafe_allow_html=True)

    # 3. 4-Stage Chronological Journey Stepper
    st.markdown(
        f"<div style='font-size:15px;font-weight:700;color:{COLOR_INK};"
        f"margin-top:10px;margin-bottom:10px;'>"
        f"1. Zero-Leakage Chronological Pipeline Journey</div>",
        unsafe_allow_html=True,
    )
    render_showcase_journey_stepper()

    # 4. Partition Health & Empirical Evaluation Cards
    st.markdown(
        f"<div style='font-size:15px;font-weight:700;color:{COLOR_INK};"
        f"margin-top:20px;margin-bottom:10px;'>"
        f"2. Partition Health & Empirical Evaluation Metrics</div>",
        unsafe_allow_html=True,
    )
    render_partition_health_cards(profile)

    # 5. Interactive Train vs. Test Log Explorer Table
    st.markdown(
        f"<div style='font-size:15px;font-weight:700;color:{COLOR_INK};"
        f"margin-top:24px;margin-bottom:10px;'>"
        f"3. Interactive Train vs. Test Log Explorer Table</div>",
        unsafe_allow_html=True,
    )
    selected_record = render_showcase_log_table(
        profile.records,
        key_prefix=f"showcase_{env_id}",
    )

    # 6. Deep Causal Explainer & Operational Business Impact
    st.markdown(
        f"<div style='font-size:15px;font-weight:700;color:{COLOR_INK};"
        f"margin-top:24px;margin-bottom:10px;'>"
        f"4. Deep Causal Explainer & Operational Business Impact</div>",
        unsafe_allow_html=True,
    )
    if selected_record is not None:
        render_showcase_explainer(selected_record, threshold=profile.threshold)
    else:
        st.info("Select a log record from the table above to inspect its causal attribution.")
