from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from logsentinel.dashboard import (
    DashboardApiClient as LegacyDashboardApiClient,
)
from logsentinel.dashboard import (
    main as dashboard_main,
)
from logsentinel.ui.client import ApiConnectionError, DashboardApiClient
from logsentinel.ui.models import AppMode, ModelStatus


def _mock_columns_side_effect(spec, *args, **kwargs):
    count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
    return [MagicMock() for _ in range(count)]


class MockSessionState(dict):
    """Dict-like mock for streamlit.session_state."""

    pass


@pytest.fixture
def mock_session_state():
    return MockSessionState()


def test_app_demo_mode_initialization_and_overview_dispatch(mock_session_state):
    from logsentinel.ui.app import main

    with (
        patch("streamlit.session_state", mock_session_state),
        patch("streamlit.set_page_config") as mock_set_page_config,
        patch("streamlit.markdown") as mock_markdown,
        patch("streamlit.sidebar") as mock_sidebar,
        patch("streamlit.radio", return_value="What is happening?"),
        patch(
            "logsentinel.ui.app.render_status_header",
            return_value=("hdfs", AppMode.DEMO),
        ) as mock_header,
        patch("logsentinel.ui.app.render_overview_view") as mock_overview,
        patch(
            "logsentinel.ui.app.get_theme_css",
            return_value="<style>/* test */</style>",
        ) as mock_theme,
    ):
        mock_sidebar.__enter__ = MagicMock(return_value=mock_sidebar)
        mock_sidebar.__exit__ = MagicMock(return_value=None)

        main(api_url="http://127.0.0.1:8000", default_env="hdfs", default_mode=AppMode.DEMO)

        mock_set_page_config.assert_called_once_with(
            page_title="LogSentinel | Neural Anomaly Detection",
            page_icon="🛡️",
            layout="wide",
        )
        mock_theme.assert_called_once()
        assert mock_markdown.called
        assert mock_session_state["environment"] == "hdfs"
        assert mock_session_state["mode"] == AppMode.DEMO
        assert mock_session_state["active_tab"] == "What is happening?"

        mock_header.assert_called_once()
        call_args = mock_header.call_args
        status_arg = call_args[0][0] if call_args[0] else call_args.kwargs["status"]
        assert isinstance(status_arg, ModelStatus)

        mock_overview.assert_called_once()
        assert mock_overview.call_args.kwargs["environment"] == "hdfs"
        assert mock_overview.call_args.kwargs["client"] is None


@pytest.mark.parametrize(
    ("tab_name", "view_mock_name"),
    [
        ("What is happening?", "render_overview_view"),
        ("Why was this flagged?", "render_pipeline_view"),
        ("How is the model performing?", "render_diagnostics_view"),
        ("How would my company use it?", "render_onboarding_view"),
    ],
)
def test_app_demo_mode_view_dispatch_all_tabs(mock_session_state, tab_name, view_mock_name):
    from logsentinel.ui.app import main

    with (
        patch("streamlit.session_state", mock_session_state),
        patch("streamlit.set_page_config"),
        patch("streamlit.markdown"),
        patch("streamlit.sidebar") as mock_sidebar,
        patch("streamlit.radio", return_value=tab_name),
        patch("logsentinel.ui.app.render_status_header", return_value=("hdfs", AppMode.DEMO)),
        patch("logsentinel.ui.app.render_overview_view") as mock_overview,
        patch("logsentinel.ui.app.render_pipeline_view") as mock_pipeline,
        patch("logsentinel.ui.app.render_diagnostics_view") as mock_diagnostics,
        patch("logsentinel.ui.app.render_onboarding_view") as mock_onboarding,
    ):
        mock_sidebar.__enter__ = MagicMock(return_value=mock_sidebar)
        mock_sidebar.__exit__ = MagicMock(return_value=None)

        main(api_url="http://127.0.0.1:8000", default_env="hdfs", default_mode=AppMode.DEMO)

        views = {
            "render_overview_view": mock_overview,
            "render_pipeline_view": mock_pipeline,
            "render_diagnostics_view": mock_diagnostics,
            "render_onboarding_view": mock_onboarding,
        }

        for name, mock_view in views.items():
            if name == view_mock_name:
                mock_view.assert_called_once()
            else:
                mock_view.assert_not_called()


def test_app_live_mode_successful_status_and_dispatch(mock_session_state):
    from logsentinel.ui.app import main

    live_status = ModelStatus(
        name="hdfs",
        version="live-v1",
        model_kind="hybrid-transformer",
        status="ready",
        threshold=0.85,
        events_indexed=100000,
        vocabulary_size=32,
    )

    with (
        patch("streamlit.session_state", mock_session_state),
        patch("streamlit.set_page_config"),
        patch("streamlit.markdown"),
        patch("streamlit.sidebar") as mock_sidebar,
        patch("streamlit.radio", return_value="What is happening?"),
        patch.object(DashboardApiClient, "status", return_value=live_status) as mock_status_query,
        patch(
            "logsentinel.ui.app.render_status_header",
            return_value=("hdfs", AppMode.LIVE),
        ) as mock_header,
        patch("logsentinel.ui.app.render_overview_view") as mock_overview,
        patch("logsentinel.ui.app.render_error_state") as mock_error,
    ):
        mock_sidebar.__enter__ = MagicMock(return_value=mock_sidebar)
        mock_sidebar.__exit__ = MagicMock(return_value=None)

        main(api_url="http://127.0.0.1:8000", default_env="hdfs", default_mode=AppMode.LIVE)

        mock_status_query.assert_called_once_with("hdfs")
        mock_header.assert_called_once()
        call_args = mock_header.call_args
        status_arg = call_args[0][0] if call_args[0] else call_args.kwargs["status"]
        assert status_arg.version == "live-v1"

        mock_error.assert_not_called()
        mock_overview.assert_called_once()
        assert mock_overview.call_args.kwargs["client"] is not None
        assert mock_overview.call_args.kwargs["state"]["mode"] == AppMode.LIVE


def test_app_live_mode_api_connection_error_zero_silent_fallback(mock_session_state):
    from logsentinel.ui.app import main

    with (
        patch("streamlit.session_state", mock_session_state),
        patch("streamlit.set_page_config"),
        patch("streamlit.markdown"),
        patch("streamlit.sidebar") as mock_sidebar,
        patch("streamlit.radio", return_value="What is happening?"),
        patch.object(
            DashboardApiClient,
            "status",
            side_effect=ApiConnectionError("Connection refused"),
        ) as mock_status_query,
        patch("logsentinel.ui.app.render_status_header", return_value=("hdfs", AppMode.LIVE)),
        patch("logsentinel.ui.app.render_error_state") as mock_error,
        patch("logsentinel.ui.app.render_overview_view") as mock_overview,
        patch("logsentinel.ui.app.get_hdfs_demo_data") as mock_hdfs_fixtures,
        patch("logsentinel.ui.app.get_bgl_demo_data") as mock_bgl_fixtures,
    ):
        mock_sidebar.__enter__ = MagicMock(return_value=mock_sidebar)
        mock_sidebar.__exit__ = MagicMock(return_value=None)

        main(api_url="http://127.0.0.1:8000", default_env="hdfs", default_mode=AppMode.LIVE)

        mock_status_query.assert_called_once_with("hdfs")
        mock_error.assert_called_once()
        # Zero silent fallback: must NOT call demo fixtures or dispatch views
        mock_hdfs_fixtures.assert_not_called()
        mock_bgl_fixtures.assert_not_called()
        mock_overview.assert_not_called()


def test_app_environment_switching_in_demo_mode(mock_session_state):
    from logsentinel.ui.app import main

    with (
        patch("streamlit.session_state", mock_session_state),
        patch("streamlit.set_page_config"),
        patch("streamlit.markdown"),
        patch("streamlit.sidebar") as mock_sidebar,
        patch("streamlit.radio", return_value="What is happening?"),
        patch("logsentinel.ui.app.render_status_header", return_value=("bgl", AppMode.DEMO)),
        patch("logsentinel.ui.app.render_overview_view") as mock_overview,
    ):
        mock_sidebar.__enter__ = MagicMock(return_value=mock_sidebar)
        mock_sidebar.__exit__ = MagicMock(return_value=None)

        main(api_url="http://127.0.0.1:8000", default_env="bgl", default_mode=AppMode.DEMO)

        assert mock_session_state["environment"] == "bgl"
        mock_overview.assert_called_once()
        state_arg = mock_overview.call_args.kwargs["state"]
        assert state_arg["environment"] == "bgl"


def test_dashboard_main_delegates_to_ui_app():
    cli_args = ["dashboard.py", "--api-url", "http://10.0.0.1:8000", "--env", "bgl", "--demo"]
    with patch("sys.argv", cli_args), patch("logsentinel.ui.app.main") as mock_ui_main:
        dashboard_main()

        mock_ui_main.assert_called_once_with(
            api_url="http://10.0.0.1:8000",
            default_env="bgl",
            default_mode=AppMode.DEMO,
        )


def test_legacy_dashboard_api_client():
    client = LegacyDashboardApiClient("http://test-server:8000")
    assert client.base_url == "http://test-server:8000"

    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"version": "v1", "status": "ready", "items": [{"id": "1"}]},
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "scored", "results": []},
        )

        status = client.status("hdfs")
        assert status["status"] == "ready"

        anomalies = client.anomalies("hdfs")
        assert len(anomalies) == 1

        score_res = client.score("hdfs", [{"message": "test"}])
        assert score_res["status"] == "scored"
