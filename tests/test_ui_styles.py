from __future__ import annotations

import pytest

from logsentinel.ui.models import AnomalyTone
from logsentinel.ui.styles import (
    COLOR_ACCENT,
    COLOR_ANOMALY_HIGH,
    COLOR_ANOMALY_LOW,
    COLOR_ANOMALY_MED,
    COLOR_BORDER,
    COLOR_CANVAS,
    COLOR_INK,
    COLOR_MUTED,
    COLOR_NAV,
    COLOR_NORMAL,
    COLOR_READY,
    COLOR_SURFACE,
    get_theme_css,
    get_tone_badge_html,
)


def test_theme_tokens():
    assert COLOR_CANVAS == "#F7F9FC"
    assert COLOR_SURFACE == "#FFFFFF"
    assert COLOR_NAV == "#0B1728"
    assert COLOR_ACCENT == "#0B6CFB"
    assert COLOR_INK == "#142033"
    assert COLOR_MUTED == "#637083"
    assert COLOR_BORDER == "#DCE3EC"


def test_semantic_colors():
    assert COLOR_ANOMALY_HIGH == "#E3242B"
    assert COLOR_ANOMALY_MED == "#FF8A00"
    assert COLOR_ANOMALY_LOW == "#F4BF24"
    assert COLOR_NORMAL == "#DCE3EC"
    assert COLOR_READY == "#10A66A"


def test_theme_css_generation():
    css = get_theme_css()
    assert ":root" in css
    assert f"--canvas: {COLOR_CANVAS}" in css
    assert f"--nav: {COLOR_NAV}" in css
    assert f"--surface: {COLOR_SURFACE}" in css
    assert f"--accent: {COLOR_ACCENT}" in css
    assert f"--ink: {COLOR_INK}" in css
    assert f"--muted: {COLOR_MUTED}" in css
    assert f"--border: {COLOR_BORDER}" in css
    assert f"--anomaly-high: {COLOR_ANOMALY_HIGH}" in css
    assert f"--anomaly-med: {COLOR_ANOMALY_MED}" in css
    assert f"--anomaly-low: {COLOR_ANOMALY_LOW}" in css
    assert f"--ready: {COLOR_READY}" in css
    assert '[data-testid="stSidebar"]' in css
    assert ".honesty-banner" in css
    assert ".error-banner" in css
    assert '[data-testid="stMetric"]' in css
    assert ".stButton button" in css
    assert "p, span, div" not in css
    assert ".provenance-badge" in css


@pytest.mark.parametrize(
    ("tone", "symbol", "expected_label"),
    [
        (AnomalyTone.HIGH, "●", "High"),
        (AnomalyTone.MEDIUM, "▲", "Medium"),
        (AnomalyTone.LOW, "◆", "Low"),
        (AnomalyTone.NORMAL, "✔", "Normal"),
        ("high", "●", "High"),
        ("med", "▲", "Medium"),
        ("medium", "▲", "Medium"),
        ("low", "◆", "Low"),
        ("normal", "✔", "Normal"),
    ],
)
def test_tone_badge_html_symbols_and_labels(tone, symbol, expected_label):
    html = get_tone_badge_html(tone)
    assert symbol in html
    assert expected_label in html
    assert "span" in html or "div" in html


def test_tone_badge_html_with_score():
    html_with_score = get_tone_badge_html(AnomalyTone.HIGH, score=0.96)
    assert "●" in html_with_score
    assert "High" in html_with_score
    assert "0.96" in html_with_score


def test_tone_badge_html_unknown_fallback():
    html = get_tone_badge_html("custom_status")
    assert "custom_status" in html.lower() or "Custom_status" in html
