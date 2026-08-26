from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

from logsentinel.ui.components.showcase_components import (
    create_attribution_figure,
    render_partition_health_cards,
    render_showcase_explainer,
    render_showcase_journey_stepper,
    render_showcase_log_table,
)
from logsentinel.ui.showcase_engine import load_showcase_profile


def test_create_attribution_figure():
    contributions = {
        "Sequence NLL": 0.42,
        "Template Rarity": 0.31,
        "PCA Reconstruction": 0.15,
        "Isolation Forest": 0.08,
    }
    fig = create_attribution_figure(contributions)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert list(fig.data[0].y) == list(contributions.keys())[::-1]


def test_create_attribution_figure_empty():
    fig = create_attribution_figure({})
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1


def test_render_partition_health_cards():
    profile = load_showcase_profile("enterprise-security")
    with patch("streamlit.columns") as mock_cols, patch("streamlit.metric") as mock_metric:
        mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        render_partition_health_cards(profile)
        assert mock_cols.called
        assert mock_metric.called


def test_render_showcase_explainer():
    profile = load_showcase_profile("enterprise-security")
    record = profile.records[0]
    with (
        patch("streamlit.markdown") as mock_md,
        patch("streamlit.plotly_chart") as mock_chart,
        patch("streamlit.columns") as mock_cols,
    ):
        mock_cols.return_value = [MagicMock(), MagicMock()]
        render_showcase_explainer(record, threshold=profile.threshold)
        assert mock_md.called
        assert mock_chart.called


def test_render_showcase_explainer_anomaly_record():
    profile = load_showcase_profile("enterprise-security")
    anomaly_record = next(r for r in profile.records if r.ground_truth == 1)
    with (
        patch("streamlit.markdown") as mock_md,
        patch("streamlit.plotly_chart") as mock_chart,
        patch("streamlit.columns") as mock_cols,
    ):
        mock_cols.return_value = [MagicMock(), MagicMock()]
        render_showcase_explainer(anomaly_record, threshold=profile.threshold)
        assert mock_md.called
        assert mock_chart.called


def test_render_showcase_journey_stepper():
    with patch("streamlit.markdown") as mock_md:
        render_showcase_journey_stepper()
        assert mock_md.called


def test_render_showcase_log_table():
    profile = load_showcase_profile("enterprise-security")
    with (
        patch("streamlit.radio") as mock_radio,
        patch("streamlit.dataframe") as mock_df,
        patch("streamlit.selectbox") as mock_sel,
        patch("streamlit.columns") as mock_cols,
    ):
        mock_radio.return_value = "All Records"
        mock_sel.return_value = 0
        mock_cols.return_value = [MagicMock(), MagicMock()]
        selected = render_showcase_log_table(profile.records, key_prefix="test_table")
        assert selected is not None
        assert mock_df.called


def test_render_showcase_log_table_filters():
    profile = load_showcase_profile("enterprise-security")
    filters = [
        "Train Normal (Past)",
        "Validation (Calibration)",
        "Test Normal (Future)",
        "Test Anomalies / Attacks (Future)",
    ]
    for filt in filters:
        with (
            patch("streamlit.radio") as mock_radio,
            patch("streamlit.dataframe") as mock_df,
            patch("streamlit.selectbox") as mock_sel,
            patch("streamlit.columns") as mock_cols,
        ):
            mock_radio.return_value = filt
            mock_sel.return_value = 0
            mock_cols.return_value = [MagicMock(), MagicMock()]
            selected = render_showcase_log_table(profile.records, key_prefix="test_table")
            assert selected is not None
            assert mock_df.called


def test_render_showcase_log_table_empty():
    with patch("streamlit.info") as mock_info:
        res = render_showcase_log_table([], key_prefix="test_empty")
        assert res is None
        assert mock_info.called
