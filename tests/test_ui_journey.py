from pathlib import Path
from unittest.mock import MagicMock, patch

from logsentinel.ui.views.journey import render_journey_view


def _mock_cols_side_effect(spec, *args, **kwargs):
    count = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
    return [MagicMock() for _ in range(count)]


def test_render_journey_view_basic():
    with patch("streamlit.markdown") as mock_md, \
         patch("streamlit.tabs") as mock_tabs, \
         patch("streamlit.columns", side_effect=_mock_cols_side_effect) as mock_cols:
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]
        render_journey_view()
        assert mock_md.called
        assert mock_tabs.called
        assert mock_cols.called


def test_journey_marks_examples_as_illustrative() -> None:
    source = Path("src/logsentinel/ui/views/journey.py").read_text()
    assert "Illustrative replay" in source
    assert "1.2ms" not in source
    assert "$50,000" not in source
