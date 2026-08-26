from __future__ import annotations

from unittest.mock import MagicMock, patch

from logsentinel.ui.client import ApiConnectionError, DashboardApiClient
from logsentinel.ui.fixtures import get_bgl_demo_data, get_hdfs_demo_data
from logsentinel.ui.models import (
    AnomalyTone,
    AppMode,
    BenchmarkEntry,
    DriftMetrics,
    Incident,
    ModelStatus,
)
from logsentinel.ui.views import (
    render_diagnostics_view,
    render_onboarding_view,
    render_overview_view,
    render_pipeline_view,
)


def _mock_columns_side_effect(spec, *args, **kwargs):
    count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
    return [MagicMock() for _ in range(count)]


# ==========================================
# 1. Overview View Tests ("What is happening?")
# ==========================================

def test_render_overview_view_demo_mode_with_incidents():
    state = get_hdfs_demo_data()

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.dataframe") as mock_dataframe, \
         patch("streamlit.selectbox", return_value=state["incidents"][0].id) as mock_selectbox, \
         patch("streamlit.file_uploader") as mock_uploader, \
         patch("logsentinel.ui.views.overview.render_anomaly_timeline") as mock_timeline, \
         patch("logsentinel.ui.views.overview.render_incident_inspector") as mock_inspector, \
         patch("logsentinel.ui.views.overview.render_empty_state") as mock_empty:

        render_overview_view(state=state, client=None, environment="hdfs")

        mock_timeline.assert_called_once_with(state["timeline"])
        mock_inspector.assert_called_once()
        passed_incident = (
            mock_inspector.call_args.kwargs.get("incident")
            or (mock_inspector.call_args.args[0] if mock_inspector.call_args.args else None)
        )
        assert passed_incident is not None
        assert passed_incident.id == state["incidents"][0].id
        assert not mock_empty.called
        assert mock_dataframe.called or mock_selectbox.called
        mock_uploader.assert_called()


def test_render_overview_view_empty_state():
    state = {
        "mode": AppMode.DEMO,
        "environment": "hdfs",
        "timeline": [],
        "incidents": [],
    }

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.file_uploader"), \
         patch("logsentinel.ui.views.overview.render_empty_state") as mock_empty:

        render_overview_view(state=state, client=None, environment="hdfs")

        mock_empty.assert_called()


def test_render_overview_view_live_mode_client_fetch():
    mock_client = MagicMock(spec=DashboardApiClient)
    mock_client.base_url = "http://127.0.0.1:8000"
    incidents = [
        Incident(
            id="LIVE-01",
            time="2025-05-12T12:00:00Z",
            source="Node-1",
            score=0.88,
            tone=AnomalyTone.HIGH,
            signal="Unseen template",
            status="Active",
            environment="hdfs",
            raw_message_redacted="Test log message",
            template_id="E_01",
            template_text="Test log message",
        )
    ]
    mock_client.anomalies.return_value = incidents
    state = {"mode": AppMode.LIVE, "environment": "hdfs"}

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.selectbox", return_value="LIVE-01"), \
         patch("streamlit.file_uploader"), \
         patch("logsentinel.ui.views.overview.render_incident_inspector") as mock_inspector:

        render_overview_view(state=state, client=mock_client, environment="hdfs")

        mock_client.anomalies.assert_called_with("hdfs", limit=100)
        mock_inspector.assert_called_once()


def test_render_overview_view_live_mode_client_error():
    mock_client = MagicMock(spec=DashboardApiClient)
    mock_client.base_url = "http://127.0.0.1:8000"
    mock_client.anomalies.side_effect = ApiConnectionError("Connection refused")
    state = {"mode": AppMode.LIVE, "environment": "hdfs"}

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("logsentinel.ui.views.overview.render_error_state") as mock_error:

        render_overview_view(state=state, client=mock_client, environment="hdfs")

        mock_error.assert_called_once()


def test_render_overview_view_event_replay():
    mock_client = MagicMock(spec=DashboardApiClient)
    mock_client.base_url = "http://127.0.0.1:8000"
    mock_client.score_events.return_value = {
        "status": "success",
        "results": [{"score": 0.92, "explanation": "Novel template"}],
    }
    state = {"mode": AppMode.LIVE, "environment": "hdfs", "incidents": []}

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.file_uploader", return_value=None), \
         patch("streamlit.text_area", return_value="CRITICAL disk failure"), \
         patch("streamlit.button", return_value=True), \
         patch("streamlit.json") as mock_json:

        render_overview_view(state=state, client=mock_client, environment="hdfs")

        mock_client.score_events.assert_called()
        mock_json.assert_called()


# ==========================================
# 2. Pipeline View Tests ("Why was this flagged?")
# ==========================================

def test_render_pipeline_view_demo_sample():
    state = get_hdfs_demo_data()

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.selectbox", return_value=0), \
         patch("logsentinel.ui.views.pipeline.render_log_pipeline_journey") as mock_journey:

        render_pipeline_view(state=state, client=None, environment="hdfs")

        mock_journey.assert_called_once()
        assert mock_journey.called


def test_render_pipeline_view_custom_log_input():
    state = get_bgl_demo_data()
    sample_text = "FATAL 192.168.1.50 kernel buffer overrun blk_-12345"

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.selectbox", return_value="Custom Raw Log Input"), \
         patch("streamlit.text_area", return_value=sample_text), \
         patch("logsentinel.ui.views.pipeline.render_log_pipeline_journey") as mock_journey:

        render_pipeline_view(state=state, client=None, environment="bgl")

        mock_journey.assert_called_once()
        call_kwargs = mock_journey.call_args[1] if mock_journey.call_args[1] else {}
        if not call_kwargs:
            call_args = mock_journey.call_args[0]
            redacted = call_args[1]
        else:
            redacted = call_kwargs["redacted_log"]
        assert "<IP>" in redacted or "<BLOCK_ID>" in redacted


def test_render_pipeline_view_live_mode():
    mock_client = MagicMock(spec=DashboardApiClient)
    mock_client.base_url = "http://127.0.0.1:8000"
    state = {"mode": AppMode.LIVE, "environment": "hdfs"}

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.selectbox", return_value="Custom Raw Log Input"), \
         patch("streamlit.text_area", return_value="10.0.0.1 DataNode volume failed"), \
         patch("logsentinel.ui.views.pipeline.render_log_pipeline_journey") as mock_journey:

        render_pipeline_view(state=state, client=mock_client, environment="hdfs")

        mock_journey.assert_called_once()


# ==========================================
# 3. Diagnostics View Tests ("How is the model performing?")
# ==========================================

def test_render_diagnostics_view_demo_mode():
    state = get_hdfs_demo_data()

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.slider", return_value=0.82) as mock_slider, \
         patch("streamlit.metric") as mock_metric, \
         patch("streamlit.dataframe") as mock_dataframe:

        render_diagnostics_view(state=state, client=None, environment="hdfs")

        # Persistent honesty banner in demo mode
        rendered_texts = [call[0][0] for call in mock_markdown.call_args_list if call[0]]
        assert any("Illustrative preview" in t or "honesty-banner" in t for t in rendered_texts)

        # Threshold slider
        mock_slider.assert_called_once()

        # 4 drift metrics
        assert mock_metric.call_count >= 4

        # Benchmark comparison table
        mock_dataframe.assert_called_once()


def test_render_diagnostics_view_live_mode():
    drift = DriftMetrics(
        unseen_templates_count=12,
        unseen_rate_pct=1.8,
        population_drift_score=0.25,
        alert_volume_per_day=95,
    )
    benchmarks = [
        BenchmarkEntry(model="PCA", pr_auc=0.60, recall=0.40, alerts=300),
        BenchmarkEntry(model="Calibrated Hybrid", pr_auc=0.88, recall=0.80, alerts=95),
    ]
    status = ModelStatus(
        name="hdfs",
        version="v1.0",
        model_kind="hybrid-transformer",
        status="ready",
        threshold=0.80,
    )
    state = {
        "mode": AppMode.LIVE,
        "environment": "hdfs",
        "status": status,
        "drift": drift,
        "benchmarks": benchmarks,
    }

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.slider", return_value=0.80), \
         patch("streamlit.metric") as mock_metric, \
         patch("streamlit.dataframe") as mock_dataframe:

        render_diagnostics_view(state=state, client=None, environment="hdfs")

        # No honesty banner in live mode
        rendered_texts = [call[0][0] for call in mock_markdown.call_args_list if call[0]]
        assert not any("Illustrative preview" in t for t in rendered_texts)

        assert mock_metric.call_count >= 4
        mock_dataframe.assert_called_once()


# ==========================================
# 4. Onboarding & Feedback Tests ("How would my company use it?")
# ==========================================

def test_render_onboarding_view_demo_mode():
    state = get_hdfs_demo_data()

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.text_input", return_value="HDFS-INC-21"), \
         patch("streamlit.selectbox", return_value="False Positive"), \
         patch("streamlit.text_area", return_value="Scheduled maintenance window"), \
         patch("streamlit.button", return_value=True), \
         patch("streamlit.download_button") as mock_download, \
         patch("streamlit.toast") as mock_toast, \
         patch("logsentinel.ui.views.onboarding_feedback.render_pipeline_stepper") as mock_stepper:

        render_onboarding_view(state=state, client=None, environment="hdfs")

        mock_stepper.assert_called_once()
        mock_toast.assert_called_once()
        mock_download.assert_called_once()

        # Tenant isolation boundary descriptions
        rendered = " ".join([call[0][0] for call in mock_markdown.call_args_list if call[0]])
        has_boundary = (
            "Tenant-isolated" in rendered
            or "Regex boundary" in rendered
            or "Frozen vocabulary" in rendered
        )
        assert has_boundary


def test_render_onboarding_view_live_mode_feedback_submission():
    mock_client = MagicMock(spec=DashboardApiClient)
    mock_client.base_url = "http://127.0.0.1:8000"
    mock_client.submit_feedback.return_value = {"status": "success"}
    state = {"mode": AppMode.LIVE, "environment": "hdfs"}

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.markdown"), \
         patch("streamlit.text_input", return_value="LIVE-INC-01"), \
         patch("streamlit.selectbox", return_value="True Anomaly"), \
         patch("streamlit.text_area", return_value="Verified hardware fault"), \
         patch("streamlit.button", return_value=True), \
         patch("streamlit.download_button"), \
         patch("streamlit.toast") as mock_toast:

        render_onboarding_view(state=state, client=mock_client, environment="hdfs")

        mock_client.submit_feedback.assert_called_once_with(
            environment="hdfs",
            incident_id="LIVE-INC-01",
            feedback="True Anomaly",
            reason="Verified hardware fault",
        )
        mock_toast.assert_called_once()


# ==========================================
# 5. Package Exports Test
# ==========================================

def test_ui_views_exports():
    from logsentinel.ui.views import (
        render_diagnostics_view,
        render_onboarding_view,
        render_overview_view,
        render_pipeline_view,
        render_showcase_view,
    )

    assert callable(render_overview_view)
    assert callable(render_pipeline_view)
    assert callable(render_diagnostics_view)
    assert callable(render_onboarding_view)
    assert callable(render_showcase_view)
