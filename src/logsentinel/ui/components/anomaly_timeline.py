from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from logsentinel.ui.models import AnomalyTone, TimelinePoint
from logsentinel.ui.styles import (
    COLOR_ANOMALY_HIGH,
    COLOR_ANOMALY_LOW,
    COLOR_ANOMALY_MED,
    COLOR_BORDER,
    COLOR_INK,
    COLOR_MUTED,
    COLOR_NORMAL,
)


def _get_tone_color(tone: AnomalyTone | str) -> str:
    key = tone.value.lower() if hasattr(tone, "value") else str(tone).lower()
    if key == "high":
        return COLOR_ANOMALY_HIGH
    if key in ("medium", "med"):
        return COLOR_ANOMALY_MED
    if key == "low":
        return COLOR_ANOMALY_LOW
    return COLOR_NORMAL


def create_anomaly_timeline_figure(timeline: list[TimelinePoint]) -> go.Figure:
    """Create a Plotly bar chart figure for the anomaly timeline with WCAG AA severity colors."""
    if not timeline:
        fig = go.Figure(data=[go.Bar(x=[], y=[])])
        fig.update_layout(
            height=280,
            margin=dict(l=20, r=20, t=30, b=30),
            xaxis=dict(showgrid=False, title="Time"),
            yaxis=dict(showgrid=True, range=[0, 1], title="Anomaly Score"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    timestamps = [point.timestamp for point in timeline]
    scores = [point.score for point in timeline]
    tones = [
        point.tone.value if hasattr(point.tone, "value") else str(point.tone)
        for point in timeline
    ]
    colors = [_get_tone_color(point.tone) for point in timeline]
    counts = [point.incident_count for point in timeline]

    hover_text = [
        f"<b>Time:</b> {t}<br>"
        f"<b>Anomaly Score:</b> {s:.3f}<br>"
        f"<b>Severity:</b> {tone.capitalize()}<br>"
        f"<b>Incidents:</b> {c}"
        for t, s, tone, c in zip(timestamps, scores, tones, counts, strict=False)
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=timestamps,
                y=scores,
                marker=dict(
                    color=colors,
                    line=dict(width=1, color=COLOR_BORDER),
                ),
                hovertext=hover_text,
                hoverinfo="text",
                name="Anomaly Score",
            )
        ]
    )

    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=25, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color=COLOR_INK,
            family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
        ),
        xaxis=dict(
            showgrid=False,
            color=COLOR_MUTED,
            tickangle=-25,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=COLOR_BORDER,
            color=COLOR_MUTED,
            range=[0, max(1.0, max(scores, default=1.0) * 1.05)],
            title="Anomaly Score",
        ),
        bargap=0.2,
    )
    return fig


def render_anomaly_timeline(timeline: list[TimelinePoint]) -> None:
    """Render the anomaly timeline Plotly component inside Streamlit."""
    fig = create_anomaly_timeline_figure(timeline)
    st.plotly_chart(fig, width="stretch")
