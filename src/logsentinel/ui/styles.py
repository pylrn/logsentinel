from __future__ import annotations

import html
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logsentinel.ui.models import AnomalyTone

# WCAG AA Design Tokens
COLOR_CANVAS = "#F7F9FC"
COLOR_SURFACE = "#FFFFFF"
COLOR_NAV = "#0B1728"
COLOR_ACCENT = "#0B6CFB"
COLOR_INK = "#142033"
COLOR_MUTED = "#637083"
COLOR_BORDER = "#DCE3EC"

# Semantic Indicators
COLOR_ANOMALY_HIGH = "#E3242B"
COLOR_ANOMALY_MED = "#FF8A00"
COLOR_ANOMALY_LOW = "#F4BF24"
COLOR_NORMAL = "#DCE3EC"
COLOR_READY = "#10A66A"

# Tone Badge Configurations (WCAG AA Contrast Compliant)
_TONE_CONFIGS: dict[str, dict[str, str]] = {
    "high": {
        "symbol": "●",
        "label": "High",
        "bg": "#FDE8E8",
        "color": "#9B1C1C",
        "border": "#E3242B",
    },
    "medium": {
        "symbol": "▲",
        "label": "Medium",
        "bg": "#FFF4E5",
        "color": "#994B00",
        "border": "#FF8A00",
    },
    "med": {
        "symbol": "▲",
        "label": "Medium",
        "bg": "#FFF4E5",
        "color": "#994B00",
        "border": "#FF8A00",
    },
    "low": {
        "symbol": "◆",
        "label": "Low",
        "bg": "#FEF9E7",
        "color": "#7D6008",
        "border": "#F4BF24",
    },
    "normal": {
        "symbol": "✔",
        "label": "Normal",
        "bg": "#E8F8F0",
        "color": "#085E3B",
        "border": "#10A66A",
    },
}


def get_theme_css() -> str:
    """Generate global WCAG AA compliant theme CSS for the Streamlit UI."""
    return f"""
<style>
:root {{
  --canvas: {COLOR_CANVAS};
  --surface: {COLOR_SURFACE};
  --nav: {COLOR_NAV};
  --accent: {COLOR_ACCENT};
  --ink: {COLOR_INK};
  --muted: {COLOR_MUTED};
  --border: {COLOR_BORDER};
  --anomaly-high: {COLOR_ANOMALY_HIGH};
  --anomaly-med: {COLOR_ANOMALY_MED};
  --anomaly-low: {COLOR_ANOMALY_LOW};
  --ready: {COLOR_READY};
}}

.stApp {{
  background-color: var(--canvas) !important;
  color: var(--ink) !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}

/* Sidebar Navigation */
[data-testid="stSidebar"] {{
  background-color: var(--nav) !important;
  border-right: 1px solid #1C2B42 !important;
}}

[data-testid="stSidebar"] * {{
  color: #EAF1FA !important;
}}

[data-testid="stSidebar"] hr {{
  border-color: #1C2B42 !important;
}}

.brand-header {{
  font: 700 20px/1.3 Inter, system-ui, sans-serif;
  color: #FFFFFF !important;
  padding: 12px 8px 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}}

.rail-footer {{
  margin-top: 24px;
  padding-top: 12px;
  border-top: 1px solid #1C2B42;
  color: #7F91A8 !important;
  font-size: 11px;
}}

/* Banners */
.honesty-banner {{
  background: #FFF4E5 !important;
  border-left: 4px solid #FF8A00 !important;
  border-radius: 6px;
  padding: 10px 16px;
  margin-bottom: 16px;
  color: #994B00 !important;
  font-size: 13px;
  font-weight: 500;
}}

.error-banner {{
  background: #FDE8E8 !important;
  border-left: 4px solid #E3242B !important;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
  color: #9B1C1C !important;
}}

/* Metrics & Metric Cards - Strict High Contrast */
[data-testid="stMetric"] {{
  background-color: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  padding: 12px 16px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}}

[data-testid="stMetricLabel"] {{
  color: #4A5568 !important;
  font-weight: 600 !important;
  font-size: 13px !important;
}}

[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] span {{
  color: #4A5568 !important;
  font-weight: 600 !important;
}}

[data-testid="stMetricValue"] {{
  color: {COLOR_INK} !important;
  font-size: 24px !important;
  font-weight: 700 !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}}

[data-testid="stMetricValue"] div, [data-testid="stMetricValue"] span {{
  color: {COLOR_INK} !important;
}}

/* Headings & Typography */
h1, h2, h3, h4, h5, h6 {{
  color: {COLOR_INK} !important;
  letter-spacing: -0.02em;
  font-weight: 700 !important;
}}

p, span, div {{
  color: {COLOR_INK};
}}

/* Widgets & Labels */
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
label {{
  color: {COLOR_INK} !important;
  font-weight: 600 !important;
  font-size: 14px !important;
}}

/* Radio Group Options */
.stRadio [role="radiogroup"] label {{
  color: {COLOR_INK} !important;
}}

.stRadio [role="radiogroup"] label span p {{
  color: {COLOR_INK} !important;
  font-weight: 500 !important;
}}

/* Sliders */
.stSlider [data-baseweb="slider"] {{
  margin-top: 6px;
}}

.stSlider [data-testid="stThumbValue"] {{
  color: {COLOR_INK} !important;
  font-weight: 700 !important;
}}

/* Dataframe & Tables */
[data-testid="stDataFrame"] {{
  background-color: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}}

/* Buttons */
.stButton button {{
  border-radius: 8px;
  font-weight: 600;
  border: 1px solid var(--border);
}}
</style>
"""


def get_tone_badge_html(tone: AnomalyTone | str, score: float | None = None) -> str:
    """Return accessible HTML badge snippet with non-color indicator and text label.

    Uses high-contrast WCAG AA colors and non-color symbols (●, ▲, ◆, ✔)
    so users with color vision deficiencies can easily distinguish severity levels.
    """
    key = tone.value.lower() if hasattr(tone, "value") else str(tone).lower()
    config = _TONE_CONFIGS.get(
        key,
        {
            "symbol": "■",
            "label": str(tone).capitalize(),
            "bg": "#F0F4F8",
            "color": COLOR_INK,
            "border": COLOR_BORDER,
        },
    )

    label = config["label"]
    symbol = config["symbol"]
    bg = config["bg"]
    text_color = config["color"]
    border_color = config["border"]

    score_text = f" ({score:.2f})" if score is not None else ""
    safe_content = f"{html.escape(symbol)} {html.escape(label)}{html.escape(score_text)}"

    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f"padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;"
        f'background-color:{bg};color:{text_color};border:1px solid {border_color};" '
        f'aria-label="{html.escape(label)} severity">'
        f"{safe_content}"
        f"</span>"
    )
