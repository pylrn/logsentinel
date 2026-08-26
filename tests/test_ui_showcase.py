from __future__ import annotations

from unittest.mock import MagicMock, patch

from logsentinel.ui.views.showcase import render_showcase_view


def test_render_showcase_view_enterprise_security():
    with patch("streamlit.markdown") as mock_md, \
         patch("streamlit.selectbox") as mock_sel, \
         patch("streamlit.radio") as mock_radio, \
         patch("streamlit.dataframe") as mock_df, \
         patch("streamlit.plotly_chart") as mock_chart, \
         patch("streamlit.metric") as mock_metric, \
         patch("streamlit.columns") as mock_cols:
        mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_sel.side_effect = ["enterprise-security", 0]
        mock_radio.return_value = "All Records"
        render_showcase_view(state={}, environment="enterprise-security")
        assert mock_md.called
        assert mock_df.called
        assert mock_chart.called
        assert mock_metric.called


def test_render_showcase_view_hdfs():
    with patch("streamlit.markdown") as mock_md, \
         patch("streamlit.selectbox") as mock_sel, \
         patch("streamlit.radio") as mock_radio, \
         patch("streamlit.dataframe") as mock_df, \
         patch("streamlit.columns") as mock_cols:
        mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_sel.side_effect = ["hdfs", 0]
        mock_radio.return_value = "Train Normal (Past)"
        render_showcase_view(state={}, environment="hdfs")
        assert mock_md.called
        assert mock_df.called


def test_render_showcase_view_bgl():
    with patch("streamlit.markdown") as mock_md, \
         patch("streamlit.selectbox") as mock_sel, \
         patch("streamlit.radio") as mock_radio, \
         patch("streamlit.dataframe") as mock_df, \
         patch("streamlit.columns") as mock_cols:
        mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_sel.side_effect = ["bgl", 0]
        mock_radio.return_value = "Test Anomalies / Attacks (Future)"
        render_showcase_view(state={}, environment="bgl")
        assert mock_md.called
        assert mock_df.called


def test_render_showcase_view_fallback_environment():
    with patch("streamlit.markdown") as mock_md, \
         patch("streamlit.selectbox") as mock_sel, \
         patch("streamlit.radio") as mock_radio, \
         patch("streamlit.dataframe") as mock_df, \
         patch("streamlit.columns") as mock_cols:
        mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_sel.side_effect = ["non-existent-env", 0]
        mock_radio.return_value = "All Records"
        render_showcase_view(state={}, environment="non-existent-env")
        assert mock_md.called
        assert mock_df.called


def test_render_showcase_view_orchestration_calls():
    with (
        patch("streamlit.markdown") as mock_md,
        patch("streamlit.selectbox") as mock_sel,
        patch("logsentinel.ui.views.showcase.render_showcase_journey_stepper") as mock_stepper,
        patch("logsentinel.ui.views.showcase.render_partition_health_cards") as mock_health,
        patch("logsentinel.ui.views.showcase.render_showcase_log_table") as mock_tbl,
        patch("logsentinel.ui.views.showcase.render_showcase_explainer") as mock_exp,
    ):
        mock_sel.return_value = "enterprise-security"
        dummy_rec = MagicMock()
        mock_tbl.return_value = dummy_rec

        render_showcase_view(state={}, environment="enterprise-security")

        assert mock_md.called
        mock_stepper.assert_called_once()
        mock_health.assert_called_once()
        mock_tbl.assert_called_once()
        mock_exp.assert_called_once_with(dummy_rec, threshold=0.85)


def test_render_showcase_view_no_record_selected():
    with (
        patch("streamlit.markdown") as mock_md,
        patch("streamlit.selectbox") as mock_sel,
        patch("streamlit.info") as mock_info,
        patch("logsentinel.ui.views.showcase.render_showcase_journey_stepper") as mock_stepper,
        patch("logsentinel.ui.views.showcase.render_partition_health_cards") as mock_health,
        patch("logsentinel.ui.views.showcase.render_showcase_log_table") as mock_tbl,
        patch("logsentinel.ui.views.showcase.render_showcase_explainer") as mock_exp,
    ):
        mock_sel.return_value = "hdfs"
        mock_tbl.return_value = None

        render_showcase_view(state={}, environment="hdfs")

        assert mock_md.called
        mock_stepper.assert_called_once()
        mock_health.assert_called_once()
        mock_tbl.assert_called_once()
        assert not mock_exp.called
        assert mock_info.called
