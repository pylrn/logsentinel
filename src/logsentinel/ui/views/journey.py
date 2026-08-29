# ruff: noqa: E501
"""A concise, evidence-first introduction to the LogSentinel research lab."""

from __future__ import annotations

import json

import streamlit as st

_SAMPLE_EVENT = {
    "timestamp": "2025-05-12T12:04:18Z",
    "source": "auth-srv",
    "host": "auth-srv",
    "severity": "WARNING",
    "message": "sshd: PAM <*> authentication failures; rhost=<IP> user=<USER_ID>",
    "group_id": "demo-auth-session",
}


def _card(title: str, copy: str, tone: str) -> str:
    return (
        f'<section style="border-left:4px solid {tone};background:#FFFFFF;border-radius:8px;'
        'border-top:1px solid #DCE3EC;border-right:1px solid #DCE3EC;border-bottom:1px solid #DCE3EC;'
        'padding:16px 18px;height:100%;box-sizing:border-box;">'
        f'<h3 style="font-size:15px;margin:0 0 6px;">{title}</h3>'
        f'<p style="color:#526174;margin:0;line-height:1.55;font-size:13px;">{copy}</p></section>'
    )


def render_journey_view() -> None:
    """Render the explanatory starting point for the local research prototype."""
    st.markdown(
        """
        <section class="journey-hero">
          <p class="journey-eyebrow">Log anomaly detection research prototype</p>
          <h1 style="font-size:clamp(2rem,4vw,3.7rem);line-height:1.04;margin:10px 0 16px;">Learn normal. Surface the unexpected.</h1>
          <p class="journey-copy">LogSentinel redacts and templates log events, learns patterns from earlier normal behaviour, then explains why a later sequence was unusual. It is designed to make experiments inspectable—not to automate incident response.</p>
          <span class="provenance-badge provenance-illustrative">● Illustrative replay · no hosted inference</span>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## How it works")
    st.caption("A small, auditable path from raw telemetry to an analyst-reviewable alert.")
    columns = st.columns(4, gap="small")
    steps = (
        ("01 · REDACT", "Sensitive values become typed placeholders before parsing.", "#10A66A"),
        ("02 · SEQUENCE", "HDFS groups block events; BGL uses time windows.", "#0B6CFB"),
        ("03 · SCORE", "Rarity and model signals form an anomaly score.", "#FF8A00"),
        ("04 · EXPLAIN", "Context and component scores support human review.", "#E3242B"),
    )
    for column, (title, copy, tone) in zip(columns, steps, strict=True):
        with column:
            st.markdown(_card(title, copy, tone), unsafe_allow_html=True)

    st.markdown("## One event, three useful views")
    ingress, contract, review = st.tabs(("Redaction", "Score contract", "Analyst review"))
    with ingress:
        left, right = st.columns(2, gap="medium")
        with left:
            st.caption("Incoming message (sensitive values shown only in this local explanation)")
            st.code(
                "sshd: PAM 8 authentication failures; rhost=198.51.100.42 user=admin",
                language="text",
            )
        with right:
            st.caption("Redacted template retained by the feature pipeline")
            st.code(_SAMPLE_EVENT["message"], language="text")
        st.markdown(
            '<p class="provenance-badge provenance-illustrative">● Illustrative replay</p> '
            "The redactor replaces sensitive fields before parsing or feature extraction.",
            unsafe_allow_html=True,
        )
    with contract:
        st.caption("The displayed fields match the local POST /v1/score request contract.")
        st.code(json.dumps({"environment": "hdfs", "events": [_SAMPLE_EVENT]}, indent=2), language="json")
        st.info("A response contains threshold, version metadata, and one or more scored sequence results.")
    with review:
        review_columns = st.columns((1.2, 1), gap="medium")
        with review_columns[0]:
            st.markdown("**Observed template**")
            st.code(_SAMPLE_EVENT["message"], language="text")
            st.markdown("**Expected next templates**")
            st.write("• authentication accepted\n\n• session closed")
        with review_columns[1]:
            st.markdown("**Rule-based guidance**")
            st.write(
                "Repeated authentication failures are unusual in this short demo sequence. "
                "An analyst should validate host context and rate limits before escalating."
            )
            st.markdown(
                '<span class="provenance-badge provenance-unavailable">■ Adapter signal unavailable in sample</span>',
                unsafe_allow_html=True,
            )

    st.markdown("## What is measured, and what is a demonstration")
    measured, illustrative, unavailable = st.columns(3, gap="small")
    with measured:
        st.markdown(_card("Measured", "Only versioned artifacts with their dataset, split and seed metadata belong here.", "#10A66A"), unsafe_allow_html=True)
    with illustrative:
        st.markdown(_card("Illustrative", "This walkthrough uses deterministic redacted examples to explain the flow.", "#FF8A00"), unsafe_allow_html=True)
    with unavailable:
        st.markdown(_card("Unavailable", "No benchmark, model, or latency result is shown until the matching artifact exists.", "#64748B"), unsafe_allow_html=True)

    st.markdown("## Run the research lab locally")
    st.code("logsentinel dashboard --api-url http://127.0.0.1:8000", language="bash")
    st.caption("The public showcase is a static explanation and local replay. It does not upload logs or run a model in the browser.")
