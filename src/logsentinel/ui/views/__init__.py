"""Question-Oriented Workspace Views for LogSentinel UI."""

from __future__ import annotations

from logsentinel.ui.views.diagnostics import render_diagnostics_view
from logsentinel.ui.views.onboarding_feedback import render_onboarding_view
from logsentinel.ui.views.overview import render_overview_view
from logsentinel.ui.views.pipeline import render_pipeline_view

__all__ = [
    "render_diagnostics_view",
    "render_onboarding_view",
    "render_overview_view",
    "render_pipeline_view",
]
