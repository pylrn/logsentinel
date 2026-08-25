from __future__ import annotations

from unittest.mock import MagicMock, patch

from logsentinel.ui.components import (
    create_anomaly_timeline_figure,
    create_score_breakdown_figure,
    render_anomaly_timeline,
    render_empty_state,
    render_error_state,
    render_incident_inspector,
    render_log_pipeline_journey,
    render_pipeline_stepper,
    render_score_breakdown,
    render_status_header,
)
from logsentinel.ui.models import (
    AnomalyTone,
    AppMode,
    Incident,
    ModelStatus,
    TimelinePoint,
)
from logsentinel.ui.styles import (
    COLOR_ANOMALY_HIGH,
    COLOR_ANOMALY_LOW,
    COLOR_ANOMALY_MED,
    COLOR_NORMAL,
)


def _mock_columns_side_effect(spec, *args, **kwargs):
    count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
    return [MagicMock() for _ in range(count)]


# ==========================================
# 1. Status Header Tests
# ==========================================

def test_render_status_header_live_mode():
    status = ModelStatus(
        name="LogSentinel-HDFS",
        version="v1.2.0",
        model_kind="hybrid-drain3-neural",
        status="ready",
        threshold=0.75,
        events_indexed=154200,
        vocabulary_size=42,
    )
    environments = ["hdfs", "bgl"]

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.selectbox", return_value="bgl") as mock_selectbox, \
         patch("streamlit.radio", return_value="Live") as mock_radio, \
         patch("streamlit.markdown") as mock_markdown:

        env, mode = render_status_header(
            status=status,
            current_env="hdfs",
            current_mode=AppMode.LIVE,
            environments=environments,
        )

        assert env == "bgl"
        assert mode == AppMode.LIVE
        mock_selectbox.assert_called_once()
        mock_radio.assert_called_once()
        assert mock_markdown.called


def test_render_status_header_demo_mode():
    status = ModelStatus(
        name="LogSentinel-BGL",
        version="v0.9.0",
        model_kind="drain3-baseline",
        status="degraded",
        threshold=0.60,
        events_indexed=5000,
        vocabulary_size=18,
    )

    with patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.selectbox", return_value="hdfs"), \
         patch("streamlit.radio", return_value="Demo"):

        env, mode = render_status_header(
            status=status,
            current_env="bgl",
            current_mode=AppMode.DEMO,
            environments=["hdfs", "bgl"],
        )

        assert env == "hdfs"
        assert mode == AppMode.DEMO


# ==========================================
# 2. Anomaly Timeline Tests
# ==========================================

def test_create_anomaly_timeline_figure_data_and_colors():
    points = [
        TimelinePoint(
            timestamp="2025-05-12T10:00:00Z",
            score=0.15,
            tone=AnomalyTone.NORMAL,
            incident_count=0,
        ),
        TimelinePoint(
            timestamp="2025-05-12T11:00:00Z",
            score=0.45,
            tone=AnomalyTone.LOW,
            incident_count=1,
        ),
        TimelinePoint(
            timestamp="2025-05-12T12:00:00Z",
            score=0.72,
            tone=AnomalyTone.MEDIUM,
            incident_count=3,
        ),
        TimelinePoint(
            timestamp="2025-05-12T13:00:00Z",
            score=0.95,
            tone=AnomalyTone.HIGH,
            incident_count=5,
        ),
    ]

    fig = create_anomaly_timeline_figure(points)

    assert fig is not None
    assert len(fig.data) == 1
    bar_trace = fig.data[0]
    expected_x = [
        "2025-05-12T10:00:00Z",
        "2025-05-12T11:00:00Z",
        "2025-05-12T12:00:00Z",
        "2025-05-12T13:00:00Z",
    ]
    assert list(bar_trace.x) == expected_x
    assert list(bar_trace.y) == [0.15, 0.45, 0.72, 0.95]

    colors = bar_trace.marker.color
    assert colors[0] == COLOR_NORMAL
    assert colors[1] == COLOR_ANOMALY_LOW
    assert colors[2] == COLOR_ANOMALY_MED
    assert colors[3] == COLOR_ANOMALY_HIGH


def test_create_anomaly_timeline_figure_empty():
    fig = create_anomaly_timeline_figure([])
    assert fig is not None
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 0


def test_render_anomaly_timeline():
    points = [
        TimelinePoint(
            timestamp="2025-05-12T10:00:00Z",
            score=0.88,
            tone=AnomalyTone.HIGH,
            incident_count=2,
        )
    ]
    with patch("streamlit.plotly_chart") as mock_plotly:
        render_anomaly_timeline(points)
        mock_plotly.assert_called_once()


# ==========================================
# 3. Score Breakdown Tests
# ==========================================

def test_create_score_breakdown_figure():
    contributions = {
        "Sequence deviation": 0.45,
        "Template rarity": 0.35,
        "PCA reconstruction": 0.20,
    }

    fig = create_score_breakdown_figure(contributions)
    assert fig is not None
    assert len(fig.data) == 1
    bar_trace = fig.data[0]
    assert bar_trace.orientation == "h"
    assert "Sequence deviation" in bar_trace.y
    assert "Template rarity" in bar_trace.y
    assert "PCA reconstruction" in bar_trace.y
    assert 0.45 in bar_trace.x


def test_create_score_breakdown_figure_empty():
    fig = create_score_breakdown_figure({})
    assert fig is not None
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 0


def test_render_score_breakdown():
    contributions = {"Drain3 Template": 0.6, "DeepLog Transformer": 0.4}
    with patch("streamlit.plotly_chart") as mock_plotly, \
         patch("streamlit.markdown") as mock_markdown:
        render_score_breakdown(contributions)
        mock_plotly.assert_called_once()
        assert mock_markdown.called


def test_render_score_breakdown_empty():
    with patch("streamlit.info") as mock_info:
        render_score_breakdown({})
        mock_info.assert_called_once()


# ==========================================
# 4. Incident Inspector Tests
# ==========================================

def test_render_incident_inspector_none():
    with patch("logsentinel.ui.components.incident_inspector.render_empty_state") as mock_empty:
        render_incident_inspector(None)
        mock_empty.assert_called_once()


def test_render_incident_inspector_with_data_and_feedback():
    incident = Incident(
        id="inc-9921",
        time="2025-05-12T14:32:00Z",
        source="DataNode-04",
        score=0.92,
        tone=AnomalyTone.HIGH,
        signal="Unseen sequence transition",
        status="Investigating",
        environment="hdfs",
        raw_message_redacted=(
            "BLOCK* NameSystem.allocateBlock: /user/data/<REDACTED_IP> blk_-<REDACTED_NUM>"
        ),
        template_id="E42",
        template_text="BLOCK* NameSystem.allocateBlock: <*> blk_*",
        context_sequence=["E12", "E12", "E30"],
        expected_templates=["E22", "E15"],
        contributions={"Sequence deviation": 0.65, "Isolation Forest": 0.27},
    )

    feedback_cb = MagicMock()

    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.code") as mock_code, \
         patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.button", side_effect=[True, False, False]):

        render_incident_inspector(incident, on_feedback_callback=feedback_cb)

        assert mock_markdown.called
        assert mock_code.called
        feedback_cb.assert_called_once_with("inc-9921", "acknowledge")


# ==========================================
# 5. Pipeline Stepper Tests
# ==========================================

def test_render_pipeline_stepper_custom_steps():
    steps = [
        {"title": "Ingestion", "status": "completed", "details": "1000 events processed"},
        {"title": "Redaction", "status": "completed", "details": "PII scrubbed"},
        {"title": "Scoring", "status": "in_progress", "details": "Transformer inference"},
    ]

    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.columns", side_effect=_mock_columns_side_effect):

        render_pipeline_stepper(steps)
        assert mock_markdown.called


def test_render_log_pipeline_journey():
    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.expander") as mock_expander:

        render_log_pipeline_journey(
            raw_log="10.0.0.1 Received block blk_1234 of size 67108864",
            redacted_log="<IP> Received block <*> of size <NUM>",
            template_id="E10",
            template_text="<IP> Received block <*> of size <NUM>",
            context=["E01", "E05"],
            predictions=["E10", "E11"],
            contributions={"Sequence": 0.8},
            fused_score=0.88,
        )

        assert mock_markdown.called
        assert mock_expander.called


# ==========================================
# 6. Empty State Tests
# ==========================================

def test_render_empty_state_without_action():
    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.button") as mock_button:

        clicked = render_empty_state(
            title="No Incidents Found",
            message="All clear across selected time range.",
        )

        assert clicked is False
        assert mock_markdown.called
        mock_button.assert_not_called()


def test_render_empty_state_with_action():
    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.button", return_value=True) as mock_button:

        clicked = render_empty_state(
            title="No Data",
            message="No logs available for preview.",
            action_label="Load Demo Data",
        )

        assert clicked is True
        assert mock_markdown.called
        mock_button.assert_called_once()


# ==========================================
# 7. Error State Tests
# ==========================================

def test_render_error_state_with_string():
    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.expander") as mock_expander, \
         patch("streamlit.columns", side_effect=_mock_columns_side_effect):

        render_error_state(
            error="Connection refused on port 8000",
            api_url="http://127.0.0.1:8000",
        )

        assert mock_markdown.called
        assert mock_expander.called


def test_render_error_state_with_exception_and_retry():
    retry_cb = MagicMock()
    test_exc = ConnectionError("Failed to reach API gateway")

    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.columns", side_effect=_mock_columns_side_effect), \
         patch("streamlit.button", return_value=True) as mock_button:

        clicked = render_error_state(
            error=test_exc,
            api_url="http://localhost:8000",
            retry_callback=retry_cb,
        )

        assert clicked is True
        assert mock_markdown.called
        mock_button.assert_called_once()
        retry_cb.assert_called_once()
