from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from logsentinel.ui.styles import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_INK,
    COLOR_MUTED,
)


def create_score_breakdown_figure(contributions: dict[str, float]) -> go.Figure:
    """Create a horizontal attribution bar chart for ensemble feature/signal contributions."""
    if not contributions:
        fig = go.Figure(data=[go.Bar(x=[], y=[], orientation="h")])
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis=dict(showgrid=False, range=[0, 1]),
            yaxis=dict(showgrid=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # Order keys for display
    keys = list(contributions.keys())
    values = [contributions[k] for k in keys]

    # Calculate percentages
    total = sum(values) if sum(values) > 0 else 1.0
    text_labels = [f"{v:.2f} ({v / total * 100:.1f}%)" for v in values]

    fig = go.Figure(
        data=[
            go.Bar(
                x=values,
                y=keys,
                orientation="h",
                text=text_labels,
                textposition="auto",
                marker=dict(
                    color=COLOR_ACCENT,
                    line=dict(width=1, color=COLOR_BORDER),
                ),
                hoverinfo="x+y",
            )
        ]
    )

    fig.update_layout(
        height=max(180, len(keys) * 45),
        margin=dict(l=10, r=20, t=15, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color=COLOR_INK,
            family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=COLOR_BORDER,
            color=COLOR_MUTED,
            range=[0, max(1.0, max(values, default=1.0) * 1.15)],
            title="Attribution Weight",
        ),
        yaxis=dict(
            showgrid=False,
            color=COLOR_INK,
            autorange="reversed",
        ),
    )
    return fig


def render_score_breakdown(contributions: dict[str, float]) -> None:
    """Render the score attribution breakdown horizontal bar chart and details."""
    if not contributions:
        st.info("No attribution breakdown available.")
        return

    st.markdown(
        "<div style='font-size: 14px; font-weight: 600; margin-bottom: 6px; color: #142033;'>"
        "Signal Attribution Breakdown"
        "</div>",
        unsafe_allow_html=True,
    )
    fig = create_score_breakdown_figure(contributions)
    st.plotly_chart(fig, width="stretch")
