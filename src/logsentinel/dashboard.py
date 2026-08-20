from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from typing import Any


def score_tone(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.3:
        return "low"
    return "normal"


def dashboard_sample_data(environment: str) -> dict[str, Any]:
    start = datetime(2025, 5, 12, tzinfo=UTC)
    scores = [
        0.12,
        0.34,
        0.18,
        0.77,
        0.63,
        0.22,
        0.16,
        0.41,
        0.68,
        0.51,
        0.27,
        0.19,
        0.13,
        0.16,
        0.21,
        0.74,
        0.32,
        0.66,
        0.24,
        0.17,
        0.38,
        0.82,
        0.58,
        0.26,
    ]
    timeline = [
        {"timestamp": start + timedelta(hours=index), "score": score, "tone": score_tone(score)}
        for index, score in enumerate(scores)
    ]
    incidents = [
        {
            "id": f"sample-{index}",
            "time": (start + timedelta(hours=hour)).isoformat(),
            "source": source,
            "score": score,
            "signal": signal,
            "status": status,
            "environment": environment,
        }
        for index, (hour, source, score, signal, status) in enumerate(
            [
                (21, "DataNode-3", 0.96, "Template rarity", "New"),
                (15, "NameNode-1", 0.91, "Event burst", "Investigating"),
                (8, "DataNode-7", 0.82, "Sequence deviation", "New"),
                (17, "JournalNode-2", 0.78, "PCA reconstruction", "Acknowledged"),
                (4, "DataNode-5", 0.63, "Unseen template", "Investigating"),
                (2, "NameNode-1", 0.58, "Isolation Forest", "New"),
            ]
        )
    ]
    return {
        "sample_data": True,
        "benchmark_label": "Illustrative preview — not measured results",
        "environment": environment,
        "model_version": "sample-preview",
        "model_status": "preview",
        "timeline": timeline,
        "incidents": incidents,
        "benchmarks": [
            {"model": "PCA", "pr_auc": 0.61, "recall": 0.41, "alerts": 412},
            {"model": "Isolation Forest", "pr_auc": 0.68, "recall": 0.54, "alerts": 286},
            {"model": "DeepLog", "pr_auc": 0.73, "recall": 0.61, "alerts": 198},
            {"model": "Transformer", "pr_auc": 0.81, "recall": 0.71, "alerts": 156},
            {"model": "Hybrid", "pr_auc": 0.86, "recall": 0.78, "alerts": 142},
        ],
        "onboarding": [
            {"name": "Redact", "description": "Remove sensitive fields", "status": "Done"},
            {"name": "Parse", "description": "Extract templates", "status": "Done"},
            {"name": "Train adapter", "description": "Learn domain patterns", "status": "Done"},
            {"name": "Calibrate", "description": "Validate thresholds", "status": "In progress"},
            {"name": "Deploy", "description": "Enable monitoring", "status": "Pending"},
        ],
    }


class DashboardApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def status(self, environment: str) -> dict[str, Any]:
        import httpx

        response = httpx.get(
            f"{self.base_url}/v1/models/{environment}/status", timeout=5
        )
        response.raise_for_status()
        return response.json()

    def anomalies(self, environment: str) -> list[dict[str, Any]]:
        import httpx

        response = httpx.get(
            f"{self.base_url}/v1/anomalies",
            params={"environment": environment, "limit": 100},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()["items"]

    def score(self, environment: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        import httpx

        response = httpx.post(
            f"{self.base_url}/v1/score",
            json={"environment": environment, "events": events},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


def main() -> None:
    try:
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError(
            "Dashboard requires: pip install 'logsentinel[dashboard]'"
        ) from exc

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--api-url", default=os.getenv("LOGSENTINEL_API_URL", "http://127.0.0.1:8000")
    )
    args, _ = parser.parse_known_args()

    st.set_page_config(
        page_title="LogSentinel",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_DASHBOARD_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<div class='brand'>◇ LogSentinel</div>", unsafe_allow_html=True)
        section = st.radio(
            "Navigation",
            ["Overview", "Incidents", "Benchmarks", "Drift", "Onboarding"],
            label_visibility="collapsed",
        )
        st.markdown(
            "<div class='rail-footer'>Research preview<br>v0.1.0</div>",
            unsafe_allow_html=True,
        )

    header_environment, header_version, header_status = st.columns([1.3, 1, 1])
    with header_environment:
        environment = st.selectbox("Environment", ["hdfs", "bgl"], format_func=str.upper)

    use_preview = st.toggle("Use illustrative preview", value=True)
    state = dashboard_sample_data(environment)
    client = DashboardApiClient(args.api_url)
    if not use_preview:
        try:
            status_data = client.status(environment)
            live_incidents = client.anomalies(environment)
            state.update(
                sample_data=False,
                benchmark_label="No measured benchmark report loaded",
                model_version=status_data["version"],
                model_status=status_data["status"],
                incidents=live_incidents,
            )
        except Exception as exc:
            st.warning(f"API unavailable; showing illustrative preview. {exc}")

    with header_version:
        st.text_input("Model version", state["model_version"], disabled=True)
    with header_status:
        st.text_input("Model status", state["model_status"], disabled=True)

    if state["sample_data"]:
        st.caption(
            "Illustrative sample data. Values on this screen are not public benchmark results."
        )

    if section == "Overview":
        _render_overview(st, pd, px, go, state, client, environment)
    elif section == "Incidents":
        st.subheader("Incidents")
        st.dataframe(pd.DataFrame(state["incidents"]), width="stretch", hide_index=True)
    elif section == "Benchmarks":
        _render_benchmarks(st, pd, state)
    elif section == "Drift":
        _render_drift(st)
    else:
        _render_onboarding(st, state)


def _render_overview(st, pd, px, go, state, client, environment: str) -> None:
    timeline_column, detail_column = st.columns([3.2, 1.15], gap="medium")
    with timeline_column:
        action_title, replay, upload = st.columns([5, 1, 1.2])
        action_title.subheader("Anomaly timeline")
        if replay.button("Replay", width="stretch"):
            now = datetime.now(UTC).isoformat()
            try:
                client.score(
                    environment,
                    [
                        {
                            "timestamp": now,
                            "source": "sample-replay",
                            "host": "preview-host",
                            "severity": "WARN",
                            "message": "replica verification failed repeatedly",
                            "group_id": "preview-block",
                        }
                    ],
                )
                st.toast("Sample event scored")
            except Exception as exc:
                st.error(f"Replay failed: {exc}")
        uploaded = upload.file_uploader(
            "Upload logs", type=["jsonl"], label_visibility="collapsed"
        )
        if uploaded is not None:
            st.info("Upload received. Use the CLI for validated bulk preparation in this release.")

        timeline = pd.DataFrame(state["timeline"])
        colors = {
            "normal": "#DCE3EC",
            "low": "#F4BF24",
            "medium": "#FF8A00",
            "high": "#E3242B",
        }
        figure = px.bar(
            timeline,
            x="timestamp",
            y="score",
            color="tone",
            color_discrete_map=colors,
            category_orders={"tone": ["high", "medium", "low", "normal"]},
        )
        figure.update_layout(
            height=260,
            margin=dict(l=8, r=8, t=8, b=8),
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend_title_text="",
            yaxis_range=[0, 1],
        )
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
        severity = st.segmented_control(
            "Severity filter", ["All", "High", "Medium", "Low"], default="All"
        )
        incidents = pd.DataFrame(state["incidents"])
        if not incidents.empty and severity != "All":
            incidents = incidents[
                incidents["score"].map(score_tone) == severity.lower()
            ]
        st.markdown(f"### Top incidents ({len(incidents)})")
        st.dataframe(
            incidents[["time", "source", "score", "signal", "status"]]
            if not incidents.empty
            else incidents,
            width="stretch",
            hide_index=True,
        )

    incidents = state["incidents"]
    selected = incidents[0] if incidents else None
    with detail_column:
        st.subheader("Selected incident")
        if selected is None:
            st.info("No anomalies have been scored for this environment.")
        else:
            st.metric("Anomaly score", f"{float(selected['score']):.2f}")
            st.caption(f"{selected['source']} · {selected['time']}")
            st.markdown("**Observed template**")
            st.code("Received block <BLOCK_ID> from <IP>", language=None)
            st.markdown("**Recent event context**")
            st.code("E_4af1 → E_7cd2 → <UNK>", language=None)
            st.markdown("**Expected next templates**")
            st.write("1. Block verification succeeded")
            st.write("2. Block committed to storage")
            contribution = pd.DataFrame(
                {
                    "signal": ["Rarity", "PCA", "Isolation Forest", "Transformer"],
                    "contribution": [0.42, 0.31, 0.12, 0.06],
                }
            )
            chart = px.bar(
                contribution,
                x="contribution",
                y="signal",
                orientation="h",
                color="contribution",
                color_continuous_scale=["#0B6CFB", "#E3242B"],
            )
            chart.update_layout(
                height=230,
                margin=dict(l=0, r=0, t=5, b=0),
                coloraxis_showscale=False,
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})

    benchmark, threshold, drift, onboarding = st.columns([1.15, 1.25, 0.95, 1.1])
    with benchmark:
        _render_benchmarks(st, pd, state, compact=True)
    with threshold:
        st.markdown("### Threshold vs alert volume")
        threshold_value = st.slider("Anomaly threshold", 0.1, 1.0, 0.5, 0.05)
        alert_volume = max(10, int(950 * (1.05 - threshold_value)))
        st.line_chart(
            pd.DataFrame(
                {
                    "threshold": [0.1, 0.3, 0.5, 0.7, 0.9],
                    "alerts/day": [940, 700, 430, 210, 70],
                }
            ).set_index("threshold"),
            height=180,
        )
        st.caption(f"Illustrative alert volume: {alert_volume}/day")
    with drift:
        _render_drift(st, compact=True)
    with onboarding:
        _render_onboarding(st, state, compact=True)


def _render_benchmarks(st, pd, state, compact: bool = False) -> None:
    st.markdown("### Benchmark comparison")
    st.caption(state["benchmark_label"])
    frame = pd.DataFrame(state["benchmarks"])
    st.dataframe(frame, width="stretch", hide_index=True, height=220 if compact else 420)


def _render_drift(st, compact: bool = False) -> None:
    st.markdown("### Unseen templates / drift")
    st.metric("Unseen templates", "18", delta="6 vs previous window", delta_color="inverse")
    st.metric("Unseen rate", "2.7%", delta="0.9%", delta_color="inverse")
    st.metric("Population drift", "0.41", delta="Moderate", delta_color="off")
    if not compact:
        st.info("Retraining is recommended only after analyst review confirms persistent drift.")


def _render_onboarding(st, state, compact: bool = False) -> None:
    st.markdown("### New company onboarding")
    for index, step in enumerate(state["onboarding"], start=1):
        st.markdown(f"**{index}. {step['name']}** — {step['status']}")
        if not compact:
            st.caption(step["description"])


_DASHBOARD_CSS = """
<style>
:root {
  --canvas: #F7F9FC;
  --surface: #FFFFFF;
  --nav: #0B1728;
  --accent: #0B6CFB;
  --ink: #142033;
  --muted: #637083;
  --border: #DCE3EC;
}
.stApp { background: var(--canvas); color: var(--ink); }
[data-testid="stSidebar"] { background: var(--nav); border-right: 0; }
[data-testid="stSidebar"] * { color: #EAF1FA; }
.brand { font: 700 23px/1.2 Inter, system-ui, sans-serif; padding: 12px 8px 28px; }
.rail-footer { position: fixed; bottom: 24px; color: #96A5B9 !important; font-size: 12px; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius: 8px; padding: 8px 10px; margin-bottom: 4px;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: var(--accent);
}
[data-testid="stMetric"], [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
  background: var(--surface); border: 1px solid var(--border); border-radius: 9px; padding: 8px;
}
h1, h2, h3 { color: var(--ink); letter-spacing: -0.02em; }
.stButton button {
  border-radius: 8px; border-color: #BFD1E8; color: var(--accent); font-weight: 600;
}
[data-baseweb="select"] > div, .stTextInput input {
  border-radius: 8px; border-color: var(--border);
}
</style>
"""


if __name__ == "__main__":
    main()
