# LogSentinel Visualization & Accessible UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular, accessible, production-grade visualization UI for LogSentinel structured around 4 question-oriented workspaces with strict Live vs. Demo mode separation, typed data models, and WCAG AA design system compliance.

**Architecture:** Refactor the monolithic `dashboard.py` into a clean package (`src/logsentinel/ui/`) containing typed data contracts (`models.py`), isolated fixtures (`fixtures/`), a strict zero-silent-fallback API client (`client.py`), reusable accessible components (`components/`), and 4 question-oriented views (`views/`).

**Tech Stack:** Python 3.11+, Streamlit, Plotly Express/Graph Objects, Pandas, Pydantic/Dataclasses, Pytest, Ruff.

---

### Task 1: Typed Data Contracts (`src/logsentinel/ui/models.py`)

**Files:**
- Create: `src/logsentinel/ui/__init__.py`
- Create: `src/logsentinel/ui/models.py`
- Test: `tests/test_ui_models.py`

- [ ] **Step 1: Write failing unit test for UI models**

```python
# tests/test_ui_models.py
from logsentinel.ui.models import (
    AnomalyTone,
    AppMode,
    BenchmarkEntry,
    DriftMetrics,
    Incident,
    ModelStatus,
    TenantOnboardingStep,
    TimelinePoint,
    score_tone,
)


def test_score_tone_mapping():
    assert score_tone(0.95) == AnomalyTone.HIGH
    assert score_tone(0.65) == AnomalyTone.MEDIUM
    assert score_tone(0.35) == AnomalyTone.LOW
    assert score_tone(0.15) == AnomalyTone.NORMAL


def test_incident_model_instantiation():
    incident = Incident(
        id="inc-1",
        time="2025-05-12T12:00:00Z",
        source="DataNode-3",
        score=0.96,
        tone=AnomalyTone.HIGH,
        signal="Template rarity",
        status="Active",
        environment="hdfs",
        raw_message_redacted="Received block <BLOCK_ID> from <IP>",
        template_id="E_4af1",
        template_text="Received block <*> from <*>",
        context_sequence=["E_1234", "E_5678"],
        expected_templates=["Block verification succeeded"],
        contributions={"Rarity": 0.42, "PCA": 0.31},
    )
    assert incident.score == 0.96
    assert incident.tone == AnomalyTone.HIGH
    assert incident.contributions["Rarity"] == 0.42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_models.py -v`  
Expected: FAIL (ModuleNotFoundError: No module named 'logsentinel.ui')

- [ ] **Step 3: Implement `models.py` and `__init__.py`**

```python
# src/logsentinel/ui/__init__.py
"""LogSentinel Modular Visualization UI package."""

# src/logsentinel/ui/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AppMode(str, Enum):
    LIVE = "live"
    DEMO = "demo"


class AnomalyTone(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NORMAL = "normal"


def score_tone(score: float) -> AnomalyTone:
    if score >= 0.8:
        return AnomalyTone.HIGH
    if score >= 0.5:
        return AnomalyTone.MEDIUM
    if score >= 0.3:
        return AnomalyTone.LOW
    return AnomalyTone.NORMAL


@dataclass(frozen=True)
class ModelStatus:
    name: str
    version: str
    model_kind: str
    status: str
    threshold: float
    events_indexed: int = 0
    vocabulary_size: int = 0


@dataclass(frozen=True)
class Incident:
    id: str
    time: str
    source: str
    score: float
    tone: AnomalyTone
    signal: str
    status: str
    environment: str
    raw_message_redacted: str
    template_id: str
    template_text: str
    context_sequence: list[str] = field(default_factory=list)
    expected_templates: list[str] = field(default_factory=list)
    contributions: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TimelinePoint:
    timestamp: str
    score: float
    tone: AnomalyTone
    incident_count: int = 1


@dataclass(frozen=True)
class DriftMetrics:
    unseen_templates_count: int
    unseen_rate_pct: float
    population_drift_score: float
    alert_volume_per_day: int


@dataclass(frozen=True)
class BenchmarkEntry:
    model: str
    pr_auc: float
    recall: float
    alerts: int


@dataclass(frozen=True)
class TenantOnboardingStep:
    step_index: int
    title: str
    description: str
    status: str
    isolation_boundary: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit Task 1**

```bash
git add src/logsentinel/ui/__init__.py src/logsentinel/ui/models.py tests/test_ui_models.py
git commit -m "feat(ui): add typed data contracts and models"
```

---

### Task 2: Labeled Demo Fixtures (`src/logsentinel/ui/fixtures/`)

**Files:**
- Create: `src/logsentinel/ui/fixtures/__init__.py`
- Create: `src/logsentinel/ui/fixtures/hdfs.py`
- Create: `src/logsentinel/ui/fixtures/bgl.py`
- Test: `tests/test_ui_fixtures.py`

- [ ] **Step 1: Write failing test for HDFS and BGL fixtures**

```python
# tests/test_ui_fixtures.py
from logsentinel.ui.fixtures.bgl import get_bgl_demo_data
from logsentinel.ui.fixtures.hdfs import get_hdfs_demo_data
from logsentinel.ui.models import AnomalyTone, AppMode


def test_hdfs_fixtures():
    data = get_hdfs_demo_data()
    assert data["environment"] == "hdfs"
    assert data["mode"] == AppMode.DEMO
    assert len(data["timeline"]) == 24
    assert len(data["incidents"]) >= 6
    assert data["status"].model_kind == "hybrid-transformer"
    assert any(inc.tone == AnomalyTone.HIGH for inc in data["incidents"])


def test_bgl_fixtures():
    data = get_bgl_demo_data()
    assert data["environment"] == "bgl"
    assert data["mode"] == AppMode.DEMO
    assert len(data["timeline"]) == 24
    assert len(data["incidents"]) >= 6
    assert data["status"].model_kind == "hybrid-transformer"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_fixtures.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement fixtures in `hdfs.py` and `bgl.py`**

```python
# src/logsentinel/ui/fixtures/__init__.py
"""Tenant-isolated illustrative fixtures for demo mode."""

# src/logsentinel/ui/fixtures/hdfs.py
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from logsentinel.ui.models import (
    AnomalyTone,
    AppMode,
    BenchmarkEntry,
    DriftMetrics,
    Incident,
    ModelStatus,
    TenantOnboardingStep,
    TimelinePoint,
    score_tone,
)


def get_hdfs_demo_data() -> dict[str, Any]:
    start = datetime(2025, 5, 12, tzinfo=UTC)
    scores = [
        0.12, 0.34, 0.18, 0.77, 0.63, 0.22, 0.16, 0.41,
        0.68, 0.51, 0.27, 0.19, 0.13, 0.16, 0.21, 0.74,
        0.32, 0.66, 0.24, 0.17, 0.38, 0.96, 0.58, 0.26,
    ]
    timeline = [
        TimelinePoint(
            timestamp=(start + timedelta(hours=idx)).isoformat(),
            score=score,
            tone=score_tone(score),
        )
        for idx, score in enumerate(scores)
    ]
    incidents = [
        Incident(
            id="HDFS-INC-21",
            time=(start + timedelta(hours=21)).isoformat(),
            source="DataNode-3",
            score=0.96,
            tone=AnomalyTone.HIGH,
            signal="Template rarity",
            status="Active",
            environment="hdfs",
            raw_message_redacted="Received block <BLOCK_ID> from <IP> status: ERROR_CRC",
            template_id="E_4af1",
            template_text="Received block <*> from <*> status: <*>",
            context_sequence=["E_0012", "E_0045", "E_4af1"],
            expected_templates=["Block verification succeeded", "Block committed"],
            contributions={"Rarity": 0.42, "PCA": 0.31, "Isolation Forest": 0.15, "Transformer": 0.12},
        ),
        Incident(
            id="HDFS-INC-15",
            time=(start + timedelta(hours=15)).isoformat(),
            source="NameNode-1",
            score=0.91,
            tone=AnomalyTone.HIGH,
            signal="Event burst frequency",
            status="Investigating",
            environment="hdfs",
            raw_message_redacted="Verification failure on <BLOCK_ID>",
            template_id="E_7cd2",
            template_text="Verification failure on <*>",
            context_sequence=["E_0012", "E_7cd2"],
            expected_templates=["Replication completed"],
            contributions={"Rarity": 0.35, "PCA": 0.40, "Isolation Forest": 0.10, "Transformer": 0.15},
        ),
        Incident(
            id="HDFS-INC-08",
            time=(start + timedelta(hours=8)).isoformat(),
            source="DataNode-7",
            score=0.82,
            tone=AnomalyTone.HIGH,
            signal="Qwen next-event deviation",
            status="New",
            environment="hdfs",
            raw_message_redacted="Packet responder terminating for <BLOCK_ID>",
            template_id="E_99a1",
            template_text="Packet responder terminating for <*>",
            context_sequence=["E_0045", "E_99a1"],
            expected_templates=["Packet acknowledged"],
            contributions={"Rarity": 0.18, "PCA": 0.22, "Isolation Forest": 0.12, "Transformer": 0.48},
        ),
        Incident(
            id="HDFS-INC-17",
            time=(start + timedelta(hours=17)).isoformat(),
            source="JournalNode-2",
            score=0.78,
            tone=AnomalyTone.MEDIUM,
            signal="PCA reconstruction error",
            status="Acknowledged",
            environment="hdfs",
            raw_message_redacted="Sync journal transaction <TX_ID> timeout",
            template_id="E_11b3",
            template_text="Sync journal transaction <*> timeout",
            context_sequence=["E_0012", "E_11b3"],
            expected_templates=["Journal flush complete"],
            contributions={"Rarity": 0.20, "PCA": 0.50, "Isolation Forest": 0.18, "Transformer": 0.12},
        ),
        Incident(
            id="HDFS-INC-04",
            time=(start + timedelta(hours=4)).isoformat(),
            source="DataNode-5",
            score=0.63,
            tone=AnomalyTone.MEDIUM,
            signal="Unseen template",
            status="Investigating",
            environment="hdfs",
            raw_message_redacted="Disk volume mount check slow on <PATH>",
            template_id="E_55f2",
            template_text="Disk volume mount check slow on <*>",
            context_sequence=["E_0001", "E_55f2"],
            expected_templates=["Volume mounted ready"],
            contributions={"Rarity": 0.55, "PCA": 0.15, "Isolation Forest": 0.15, "Transformer": 0.15},
        ),
        Incident(
            id="HDFS-INC-02",
            time=(start + timedelta(hours=2)).isoformat(),
            source="NameNode-1",
            score=0.58,
            tone=AnomalyTone.MEDIUM,
            signal="Isolation Forest partition",
            status="New",
            environment="hdfs",
            raw_message_redacted="Heartbeat delayed from <IP>",
            template_id="E_03c9",
            template_text="Heartbeat delayed from <*>",
            context_sequence=["E_0002", "E_03c9"],
            expected_templates=["Heartbeat received"],
            contributions={"Rarity": 0.15, "PCA": 0.25, "Isolation Forest": 0.45, "Transformer": 0.15},
        ),
    ]
    status = ModelStatus(
        name="hdfs",
        version="hdfs-hybrid-v1",
        model_kind="hybrid-transformer",
        status="ready",
        threshold=0.82,
        events_indexed=482000,
        vocabulary_size=29,
    )
    drift = DriftMetrics(
        unseen_templates_count=18,
        unseen_rate_pct=2.7,
        population_drift_score=0.41,
        alert_volume_per_day=142,
    )
    benchmarks = [
        BenchmarkEntry(model="PCA", pr_auc=0.61, recall=0.41, alerts=412),
        BenchmarkEntry(model="Isolation Forest", pr_auc=0.68, recall=0.54, alerts=286),
        BenchmarkEntry(model="DeepLog", pr_auc=0.73, recall=0.61, alerts=198),
        BenchmarkEntry(model="Transformer (Qwen)", pr_auc=0.81, recall=0.71, alerts=156),
        BenchmarkEntry(model="Calibrated Hybrid", pr_auc=0.86, recall=0.78, alerts=142),
    ]
    onboarding = [
        TenantOnboardingStep(1, "Redact Sensitive Data", "Remove IPs, block IDs, paths, tokens", "Done", "Regex boundary"),
        TenantOnboardingStep(2, "Extract Deterministic Templates", "Drain parser template indexing", "Done", "Frozen vocabulary"),
        TenantOnboardingStep(3, "Train Qwen LoRA Adapter", "Learn normal event sequences", "Done", "Tenant-isolated adapter weights"),
        TenantOnboardingStep(4, "Calibrate Fusion Threshold", "Optimize precision-recall tradeoff", "Done", "Isotonic threshold curve"),
        TenantOnboardingStep(5, "Deploy & Serve", "Serve real-time inference via FastAPI", "Done", "Local zero-leakage serving"),
    ]
    return {
        "mode": AppMode.DEMO,
        "environment": "hdfs",
        "status": status,
        "timeline": timeline,
        "incidents": incidents,
        "drift": drift,
        "benchmarks": benchmarks,
        "onboarding": onboarding,
        "honesty_label": "Illustrative preview — not measured benchmark results",
    }


# src/logsentinel/ui/fixtures/bgl.py
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from logsentinel.ui.models import (
    AnomalyTone,
    AppMode,
    BenchmarkEntry,
    DriftMetrics,
    Incident,
    ModelStatus,
    TenantOnboardingStep,
    TimelinePoint,
    score_tone,
)


def get_bgl_demo_data() -> dict[str, Any]:
    start = datetime(2025, 5, 12, tzinfo=UTC)
    scores = [
        0.08, 0.15, 0.22, 0.45, 0.72, 0.31, 0.14, 0.28,
        0.88, 0.42, 0.25, 0.18, 0.11, 0.15, 0.33, 0.65,
        0.29, 0.81, 0.20, 0.14, 0.40, 0.94, 0.52, 0.21,
    ]
    timeline = [
        TimelinePoint(
            timestamp=(start + timedelta(hours=idx)).isoformat(),
            score=score,
            tone=score_tone(score),
        )
        for idx, score in enumerate(scores)
    ]
    incidents = [
        Incident(
            id="BGL-INC-21",
            time=(start + timedelta(hours=21)).isoformat(),
            source="R02-M1-N0-C:J12-U11",
            score=0.94,
            tone=AnomalyTone.HIGH,
            signal="Card error state transition",
            status="Active",
            environment="bgl",
            raw_message_redacted="CE sym <HEX> at <ADDR> mask <MASK>",
            template_id="BGL_0088",
            template_text="CE sym <*> at <*> mask <*>",
            context_sequence=["BGL_0001", "BGL_0014", "BGL_0088"],
            expected_templates=["DDR link operational", "Memory scrub completed"],
            contributions={"Rarity": 0.38, "PCA": 0.25, "Isolation Forest": 0.15, "Transformer": 0.22},
        ),
        Incident(
            id="BGL-INC-08",
            time=(start + timedelta(hours=8)).isoformat(),
            source="R14-M0-NC-C:J04-U01",
            score=0.88,
            tone=AnomalyTone.HIGH,
            signal="L3 cache correctable burst",
            status="Investigating",
            environment="bgl",
            raw_message_redacted="L3 major internal error detected on <NODE>",
            template_id="BGL_0102",
            template_text="L3 major internal error detected on <*>",
            context_sequence=["BGL_0002", "BGL_0102"],
            expected_templates=["Node heartbeat ok"],
            contributions={"Rarity": 0.45, "PCA": 0.20, "Isolation Forest": 0.20, "Transformer": 0.15},
        ),
        Incident(
            id="BGL-INC-17",
            time=(start + timedelta(hours=17)).isoformat(),
            source="R22-M1-N4-C:J08-U11",
            score=0.81,
            tone=AnomalyTone.HIGH,
            signal="Qwen next-event deviation",
            status="New",
            environment="bgl",
            raw_message_redacted="Tree network packet drop counter <COUNT>",
            template_id="BGL_0054",
            template_text="Tree network packet drop counter <*>",
            context_sequence=["BGL_0010", "BGL_0054"],
            expected_templates=["Tree packet routed ok"],
            contributions={"Rarity": 0.15, "PCA": 0.20, "Isolation Forest": 0.15, "Transformer": 0.50},
        ),
        Incident(
            id="BGL-INC-04",
            time=(start + timedelta(hours=4)).isoformat(),
            source="R04-M0-N8-C:J02-U01",
            score=0.72,
            tone=AnomalyTone.MEDIUM,
            signal="PCA reconstruction error",
            status="Acknowledged",
            environment="bgl",
            raw_message_redacted="Kernel panic sync buffer overflow",
            template_id="BGL_0019",
            template_text="Kernel panic sync buffer overflow",
            context_sequence=["BGL_0001", "BGL_0019"],
            expected_templates=["Kernel buffer cleared"],
            contributions={"Rarity": 0.25, "PCA": 0.45, "Isolation Forest": 0.15, "Transformer": 0.15},
        ),
        Incident(
            id="BGL-INC-15",
            time=(start + timedelta(hours=15)).isoformat(),
            source="R10-M1-N2-C:J10-U01",
            score=0.65,
            tone=AnomalyTone.MEDIUM,
            signal="Isolation Forest outlier",
            status="Investigating",
            environment="bgl",
            raw_message_redacted="Temperature warning sensor <SENSOR_ID>",
            template_id="BGL_0033",
            template_text="Temperature warning sensor <*>",
            context_sequence=["BGL_0005", "BGL_0033"],
            expected_templates=["Fan speed adjusted"],
            contributions={"Rarity": 0.20, "PCA": 0.20, "Isolation Forest": 0.45, "Transformer": 0.15},
        ),
        Incident(
            id="BGL-INC-22",
            time=(start + timedelta(hours=22)).isoformat(),
            source="R30-M0-NC-C:J00-U11",
            score=0.52,
            tone=AnomalyTone.MEDIUM,
            signal="Template rarity",
            status="New",
            environment="bgl",
            raw_message_redacted="Power supply unit voltage ripple",
            template_id="BGL_0071",
            template_text="Power supply unit voltage ripple",
            context_sequence=["BGL_0001", "BGL_0071"],
            expected_templates=["Voltage stabilized"],
            contributions={"Rarity": 0.50, "PCA": 0.20, "Isolation Forest": 0.15, "Transformer": 0.15},
        ),
    ]
    status = ModelStatus(
        name="bgl",
        version="bgl-hybrid-v1",
        model_kind="hybrid-transformer",
        status="ready",
        threshold=0.79,
        events_indexed=395000,
        vocabulary_size=384,
    )
    drift = DriftMetrics(
        unseen_templates_count=24,
        unseen_rate_pct=3.4,
        population_drift_score=0.48,
        alert_volume_per_day=176,
    )
    benchmarks = [
        BenchmarkEntry(model="PCA", pr_auc=0.58, recall=0.38, alerts=520),
        BenchmarkEntry(model="Isolation Forest", pr_auc=0.65, recall=0.51, alerts=340),
        BenchmarkEntry(model="DeepLog", pr_auc=0.71, recall=0.59, alerts=230),
        BenchmarkEntry(model="Transformer (Qwen)", pr_auc=0.79, recall=0.68, alerts=185),
        BenchmarkEntry(model="Calibrated Hybrid", pr_auc=0.84, recall=0.75, alerts=168),
    ]
    onboarding = [
        TenantOnboardingStep(1, "Redact Sensitive Data", "Remove IPs, node IDs, hex addresses", "Done", "Regex boundary"),
        TenantOnboardingStep(2, "Extract Deterministic Templates", "Drain parser template indexing", "Done", "Frozen vocabulary"),
        TenantOnboardingStep(3, "Train Qwen LoRA Adapter", "Learn supercomputer node event sequences", "Done", "Tenant-isolated adapter weights"),
        TenantOnboardingStep(4, "Calibrate Fusion Threshold", "Optimize precision-recall tradeoff", "Done", "Isotonic threshold curve"),
        TenantOnboardingStep(5, "Deploy & Serve", "Serve real-time inference via FastAPI", "Done", "Local zero-leakage serving"),
    ]
    return {
        "mode": AppMode.DEMO,
        "environment": "bgl",
        "status": status,
        "timeline": timeline,
        "incidents": incidents,
        "drift": drift,
        "benchmarks": benchmarks,
        "onboarding": onboarding,
        "honesty_label": "Illustrative preview — not measured benchmark results",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_fixtures.py -v`  
Expected: PASS

- [ ] **Step 5: Commit Task 2**

```bash
git add src/logsentinel/ui/fixtures/ tests/test_ui_fixtures.py
git commit -m "feat(ui): add typed demo fixtures for HDFS and BGL tenants"
```

---

### Task 3: WCAG AA Design Tokens & Styles (`src/logsentinel/ui/styles.py`)

**Files:**
- Create: `src/logsentinel/ui/styles.py`
- Test: `tests/test_ui_styles.py`

- [ ] **Step 1: Write test for styles and CSS injection**

```python
# tests/test_ui_styles.py
from logsentinel.ui.styles import (
    COLOR_ANOMALY_HIGH,
    COLOR_CANVAS,
    COLOR_NAV,
    COLOR_READY,
    get_theme_css,
)


def test_theme_tokens():
    assert COLOR_NAV == "#0B1728"
    assert COLOR_CANVAS == "#F7F9FC"
    assert COLOR_ANOMALY_HIGH == "#E3242B"
    assert COLOR_READY == "#10A66A"


def test_theme_css_generation():
    css = get_theme_css()
    assert ":root" in css
    assert "--canvas: #F7F9FC" in css
    assert "--nav: #0B1728" in css
    assert "data-testid=\"stSidebar\"" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_styles.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement `styles.py`**

```python
# src/logsentinel/ui/styles.py
from __future__ import annotations

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


def get_theme_css() -> str:
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
  background: var(--canvas);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}

[data-testid="stSidebar"] {{
  background: var(--nav);
  border-right: 1px solid #1C2B42;
}}

[data-testid="stSidebar"] * {{
  color: #EAF1FA !important;
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

.honesty-banner {{
  background: #FFF4E5;
  border-left: 4px solid #FF8A00;
  border-radius: 6px;
  padding: 8px 16px;
  margin-bottom: 16px;
  color: #994B00;
  font-size: 13px;
  font-weight: 500;
}}

.error-banner {{
  background: #FDE8E8;
  border-left: 4px solid #E3242B;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
  color: #9B1C1C;
}}

[data-testid="stMetric"], [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 10px;
}}

h1, h2, h3 {{
  color: var(--ink);
  letter-spacing: -0.02em;
}}

.stButton button {{
  border-radius: 8px;
  font-weight: 600;
}}
</style>
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_styles.py -v`  
Expected: PASS

- [ ] **Step 5: Commit Task 3**

```bash
git add src/logsentinel/ui/styles.py tests/test_ui_styles.py
git commit -m "feat(ui): add WCAG AA design system tokens and styling"
```

---

### Task 4: Strict Live API Client (`src/logsentinel/ui/client.py`)

**Files:**
- Create: `src/logsentinel/ui/client.py`
- Test: `tests/test_ui_client.py`

- [ ] **Step 1: Write test for strict API client**

```python
# tests/test_ui_client.py
import pytest
from logsentinel.ui.client import ApiConnectionError, DashboardApiClient
from logsentinel.ui.models import AnomalyTone, ModelStatus


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_client_status_parsing(monkeypatch):
    client = DashboardApiClient("http://mock-api")
    monkeypatch.setattr(
        "httpx.get",
        lambda *args, **kwargs: MockResponse({
            "environment": "hdfs",
            "version": "v1",
            "model_kind": "hybrid-transformer",
            "status": "ready",
            "threshold": 0.82,
            "events_indexed": 100,
            "vocabulary_size": 25,
        }),
    )
    status = client.status("hdfs")
    assert isinstance(status, ModelStatus)
    assert status.version == "v1"
    assert status.threshold == 0.82


def test_client_strict_error_raising(monkeypatch):
    client = DashboardApiClient("http://unreachable-api")

    def raise_conn_err(*args, **kwargs):
        raise ConnectionError("Connection refused")

    monkeypatch.setattr("httpx.get", raise_conn_err)
    with pytest.raises(ApiConnectionError):
        client.status("hdfs")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_client.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement `client.py`**

```python
# src/logsentinel/ui/client.py
from __future__ import annotations

from typing import Any

from logsentinel.ui.models import AnomalyTone, Incident, ModelStatus, score_tone


class ApiConnectionError(Exception):
    """Raised when Live API connection fails without silent fallback."""


class DashboardApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> dict[str, Any]:
        import httpx

        try:
            response = httpx.get(f"{self.base_url}/health", timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ApiConnectionError(f"Health check failed at {self.base_url}: {exc}") from exc

    def status(self, environment: str) -> ModelStatus:
        import httpx

        try:
            response = httpx.get(
                f"{self.base_url}/v1/models/{environment}/status", timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return ModelStatus(
                name=environment,
                version=data.get("version", "unknown"),
                model_kind=data.get("model_kind", "hybrid-statistical"),
                status=data.get("status", "ready"),
                threshold=float(data.get("threshold", 0.5)),
                events_indexed=int(data.get("events_indexed", 0)),
                vocabulary_size=int(data.get("vocabulary_size", 0)),
            )
        except Exception as exc:
            raise ApiConnectionError(
                f"Failed to query model status for '{environment}' from {self.base_url}: {exc}"
            ) from exc

    def anomalies(self, environment: str, limit: int = 100) -> list[Incident]:
        import httpx

        try:
            response = httpx.get(
                f"{self.base_url}/v1/anomalies",
                params={"environment": environment, "limit": limit},
                timeout=5,
            )
            response.raise_for_status()
            raw_items = response.json().get("items", [])
            incidents = []
            for item in raw_items:
                score = float(item.get("score", 0.0))
                incidents.append(
                    Incident(
                        id=str(item.get("id", "alert")),
                        time=str(item.get("timestamp") or item.get("time", "")),
                        source=str(item.get("source", "unknown")),
                        score=score,
                        tone=score_tone(score),
                        signal=str(item.get("signal", "Anomaly detection")),
                        status=str(item.get("status", "Active")),
                        environment=environment,
                        raw_message_redacted=str(item.get("message", "")),
                        template_id=str(item.get("template_id", "E_UNK")),
                        template_text=str(item.get("template", "")),
                        context_sequence=list(item.get("context_sequence", [])),
                        expected_templates=list(item.get("expected_templates", [])),
                        contributions=dict(item.get("contributions", {})),
                    )
                )
            return incidents
        except Exception as exc:
            raise ApiConnectionError(
                f"Failed to fetch anomalies for '{environment}' from {self.base_url}: {exc}"
            ) from exc

    def score_events(
        self, environment: str, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        import httpx

        try:
            response = httpx.post(
                f"{self.base_url}/v1/score",
                json={"environment": environment, "events": events},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ApiConnectionError(
                f"Scoring request failed at {self.base_url}: {exc}"
            ) from exc

    def submit_feedback(
        self,
        environment: str,
        incident_id: str,
        feedback: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        import httpx

        try:
            response = httpx.post(
                f"{self.base_url}/v1/feedback",
                json={
                    "environment": environment,
                    "incident_id": incident_id,
                    "feedback": feedback,
                    "reason": reason,
                },
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ApiConnectionError(
                f"Failed to submit feedback to {self.base_url}: {exc}"
            ) from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_client.py -v`  
Expected: PASS

- [ ] **Step 5: Commit Task 4**

```bash
git add src/logsentinel/ui/client.py tests/test_ui_client.py
git commit -m "feat(ui): implement strict zero-silent-fallback API client"
```

---

### Task 5: Reusable UI Components (`src/logsentinel/ui/components/`)

**Files:**
- Create: `src/logsentinel/ui/components/__init__.py`
- Create: `src/logsentinel/ui/components/status_header.py`
- Create: `src/logsentinel/ui/components/anomaly_timeline.py`
- Create: `src/logsentinel/ui/components/score_breakdown.py`
- Create: `src/logsentinel/ui/components/incident_inspector.py`
- Create: `src/logsentinel/ui/components/pipeline_stepper.py`
- Create: `src/logsentinel/ui/components/empty_state.py`
- Create: `src/logsentinel/ui/components/error_state.py`
- Test: `tests/test_ui_components.py`

- [ ] **Step 1: Write tests for UI component functions**

```python
# tests/test_ui_components.py
from logsentinel.ui.components.empty_state import render_empty_state
from logsentinel.ui.components.error_state import render_error_state
from logsentinel.ui.models import AnomalyTone, Incident


def test_incident_component_properties():
    inc = Incident(
        id="test-1",
        time="2025-05-12T12:00:00Z",
        source="host-1",
        score=0.95,
        tone=AnomalyTone.HIGH,
        signal="Rarity",
        status="New",
        environment="hdfs",
        raw_message_redacted="log message",
        template_id="E_0001",
        template_text="template text",
        contributions={"Rarity": 0.6, "PCA": 0.4},
    )
    assert inc.score == 0.95
```

- [ ] **Step 2: Implement components in `src/logsentinel/ui/components/`**
  - Implement `status_header.py` (environment selectbox, model version, threshold, Live/Demo toggle).
  - Implement `anomaly_timeline.py` (Plotly 24h bar timeline with severity tone colors).
  - Implement `score_breakdown.py` (horizontal component attribution bar chart).
  - Implement `incident_inspector.py` (selected incident details, template code box, feedback buttons).
  - Implement `pipeline_stepper.py` (6-step visual pipeline journey).
  - Implement `empty_state.py` (zero data info callout).
  - Implement `error_state.py` (API failure banner and troubleshooting instructions).

- [ ] **Step 3: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_components.py -v`  
Expected: PASS

- [ ] **Step 4: Commit Task 5**

```bash
git add src/logsentinel/ui/components/ tests/test_ui_components.py
git commit -m "feat(ui): add reusable UI components and dedicated failure states"
```

---

### Task 6: The 4 Question-Oriented Workspaces (`src/logsentinel/ui/views/`)

**Files:**
- Create: `src/logsentinel/ui/views/__init__.py`
- Create: `src/logsentinel/ui/views/overview.py`
- Create: `src/logsentinel/ui/views/pipeline.py`
- Create: `src/logsentinel/ui/views/diagnostics.py`
- Create: `src/logsentinel/ui/views/onboarding_feedback.py`
- Test: `tests/test_ui_views.py`

- [ ] **Step 1: Write integration tests with Streamlit `AppTest`**

```python
# tests/test_ui_views.py
from streamlit.testing.v1 import AppTest


def test_overview_view_demo_mode():
    at = AppTest.from_file("src/logsentinel/dashboard.py")
    at.run()
    assert not at.exception
```

- [ ] **Step 2: Implement view modules**
  - `views/overview.py`: Timeline, incident table with severity filter, persistent incident inspector.
  - `views/pipeline.py`: Step-by-step visual log pipeline explainer + interactive log tester.
  - `views/diagnostics.py`: Qwen top-k distribution, entropy curves, threshold vs alert volume simulation slider, benchmarks.
  - `views/onboarding_feedback.py`: Tenant isolation checklist and analyst feedback loop.

- [ ] **Step 3: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_views.py -v`  
Expected: PASS

- [ ] **Step 4: Commit Task 6**

```bash
git add src/logsentinel/ui/views/ tests/test_ui_views.py
git commit -m "feat(ui): implement 4 question-oriented workspaces"
```

---

### Task 7: Main UI Entrypoint & Backwards-Compatible Shim (`src/logsentinel/ui/app.py`, `dashboard.py`)

**Files:**
- Create: `src/logsentinel/ui/app.py`
- Modify: `src/logsentinel/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write app entrypoint and dashboard delegation**
  - Connect navigation sidebar (1. What is happening? 2. Why was this flagged? 3. Model Performance 4. Tenant Operations).
  - Enforce explicit Live / Demo state routing.
  - Ensure `dashboard.py` imports and runs `ui.app.main()`.

- [ ] **Step 2: Run all dashboard regression tests**

Run: `.venv/bin/python -m pytest tests/test_dashboard.py -v`  
Expected: PASS

- [ ] **Step 3: Commit Task 7**

```bash
git add src/logsentinel/ui/app.py src/logsentinel/dashboard.py tests/test_dashboard.py
git commit -m "feat(ui): connect main app routing and backwards-compatible dashboard shim"
```

---

### Task 8: Full Regression Suite, Linting & Build Verification

- [ ] **Step 1: Run complete test suite**

Run: `.venv/bin/python -m pytest -q`  
Expected: All tests pass (75+ passing tests)

- [ ] **Step 2: Run Ruff lint check**

Run: `ruff check .`  
Expected: All checks passed!

- [ ] **Step 3: Build wheel package**

Run: `.venv/bin/python -m build --wheel --no-isolation`  
Expected: Successfully built logsentinel wheel

- [ ] **Step 4: Commit and finalize**

```bash
git add .
git commit -m "chore(ui): complete LogSentinel modular visualization milestone"
```
