# LogSentinel Visualization & Accessible UI Design Specification

**Date**: 2026-08-26  
**Status**: Approved / In Review  
**Target Package**: `src/logsentinel/ui/`  
**Reference Document**: `docs/design/dashboard-design-system.md`

---

## 1. Overview & Objectives

LogSentinel is an enterprise log anomaly detection research platform combining privacy-safe redaction, deterministic template parsing, and a hybrid detector architecture (statistical baselines + optional fine-tuned Qwen2.5-1.5B QLoRA next-event sequence modeling).

The goal of this UI design milestone is to replace the single-file prototype (`src/logsentinel/dashboard.py`) with a production-grade, modular, and highly accessible visual workspace.

### Core Objectives:
1. **Explain the Full Lifecycle**: Make every stage understandable—`Raw Log` $\rightarrow$ `Redaction` $\rightarrow$ `Template ID` $\rightarrow$ `Preceding Sequence` $\rightarrow$ `Expected Next Events` $\rightarrow$ `Component Scores` $\rightarrow$ `Calibrated Fusion Decision` $\rightarrow$ `Analyst Feedback`.
2. **Strict Mode Separation**:
   - **Live Mode**: Queries the running FastAPI backend exclusively. If the service is unreachable or errors occur, renders an explicit, informative `ErrorState` with diagnostic instructions. **Never silently fall back to sample fixtures.**
   - **Demo Mode**: Uses typed, labeled illustrative fixtures (`fixtures/hdfs.py`, `fixtures/bgl.py`) with a persistent top **Honesty Banner** stating data is illustrative and not a benchmark result.
3. **Simpler User-Facing Navigation**: Organize the visual experience around 4 core user questions rather than internal technical components:
   - *1. What is happening?* (Overview & Active Anomalies)
   - *2. Why was this flagged?* (Pipeline & Incident Explanation)
   - *3. How is the model performing?* (Diagnostics, Drift & Thresholds)
   - *4. How would my company use it?* (Tenant Onboarding & Feedback Loop)
4. **Accessibility & Design System**: Full WCAG AA contrast compliance, non-color anomaly cues, responsive fluid grids, and keyboard accessibility.

---

## 2. Package & Module Architecture

The UI is structured under `src/logsentinel/ui/`:

```
src/logsentinel/
├── ui/
│   ├── __init__.py
│   ├── app.py                      # Main entrypoint, sidebar navigation, top bar, routing
│   ├── client.py                   # Typed FastAPI client (timeouts, HTTP errors, status checks)
│   ├── models.py                   # Typed Pydantic / dataclass definitions for UI & API state
│   ├── state.py                    # Session state management and active environment context
│   ├── styles.py                   # WCAG AA design tokens, Swiss typography, CSS variables
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── hdfs.py                 # Typed illustrative fixtures for HDFS tenant demo
│   │   └── bgl.py                  # Typed illustrative fixtures for BGL tenant demo
│   ├── components/
│   │   ├── __init__.py
│   │   ├── status_header.py        # Environment picker, model badge, threshold, Live/Demo toggle
│   │   ├── anomaly_timeline.py     # Plotly 24h severity-toned anomaly timeline chart
│   │   ├── pipeline_stepper.py     # Step-by-step interactive transformation cards
│   │   ├── score_breakdown.py      # Horizontal bar attribution visualizer (Rarity, PCA, IF, Qwen)
│   │   ├── incident_inspector.py   # Persistent incident drilldown panel with raw/redacted templates
│   │   ├── empty_state.py          # Clean zero-data empty state container
│   │   └── error_state.py          # Structured error card with HTTP status and retry action
│   └── views/
│       ├── __init__.py
│       ├── overview.py             # Workspace 1: "What is happening?"
│       ├── pipeline.py             # Workspace 2: "Why was this flagged?"
│       ├── diagnostics.py          # Workspace 3: "How is the model performing?"
│       └── onboarding_feedback.py  # Workspace 4: "How would my company use it?"
└── dashboard.py                    # Backwards-compatible CLI wrapper calling `ui.app.main()`
```

---

## 3. Data Contracts & State Models (`models.py`)

```python
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


@dataclass(frozen=True)
class ModelStatus:
    name: str
    version: str
    model_kind: str  # "hybrid-transformer" | "hybrid-statistical"
    status: str      # "ready" | "preview" | "offline"
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
    context_sequence: list[str]
    expected_templates: list[str]
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
    status: str  # "Done" | "In progress" | "Pending"
    isolation_boundary: str
```

---

## 4. Workspaces & Detailed View Specifications

### Workspace 1: "What is happening?" (`views/overview.py`)
- **Header**: Environment dropdown (`HDFS` / `BGL`), Model status pill, Threshold indicator, and explicit `Live API` / `Demo Mode` selector.
- **Top Row**: 24-hour Anomaly Score Timeline powered by Plotly with color-coded severity bars (Graphite/Blue normal, Amber low, Orange medium, Crimson red high) and clickable time slices.
- **Left Main Pane**: Ranked Anomalies Table with severity filter tabs (`All`, `High`, `Medium`, `Low`), displaying Incident ID, Timestamp, Node/Source, Fused Score, Dominant Signal, and Lifecycle Status.
- **Right Persistent Inspector**: Displays the selected incident's redacted observed template, preceding event context window, expected next-event templates, and horizontal score contribution bar chart.

### Workspace 2: "Why was this flagged?" (`views/pipeline.py`)
- **Visual Pipeline Stepper**:
  1. *Raw Ingestion*: Displays original raw log string.
  2. *Privacy Redaction*: Shows regex token replacements (`<IP>`, `<BLOCK_ID>`, `<USER>`).
  3. *Template Extraction*: Maps to canonical template ID and regex signature.
  4. *Sequence Context*: Shows sliding context window of preceding events ($E_1, E_2, \dots$).
  5. *Next-Event Neural Expectation*: Displays Qwen top-k predicted event IDs vs actual observed event.
  6. *Component Score Fusion*: Visualizes individual weights (Rarity, PCA, Isolation Forest, Transformer NLL) combined into the calibrated score.
- **Interactive Log Tester**: Allows operators/researchers to paste a raw log line, score it through the pipeline, and inspect intermediate outputs.

### Workspace 3: "How is the model performing?" (`views/diagnostics.py`)
- **Neural Diagnostics**: Qwen next-event rank distribution, token sequence perplexity, sequence entropy curves.
- **Statistical Baselines**: PCA reconstruction error distribution, Isolation Forest anomaly densities, and Drain template rarity frequencies.
- **Drift & Alert Volume Simulation**: Interactive threshold slider showing real-time simulated alert volume curves (alerts/day vs threshold) and unseen template velocity counters.
- **Benchmark Registry**: Table of baseline comparisons with explicit provenance labels.

### Workspace 4: "How would my company use it?" (`views/onboarding_feedback.py`)
- **Tenant Isolation Verification**: Explains how separate adapters, template vocabularies, thresholds, and artifacts guarantee zero cross-tenant data leakage between environments.
- **Interactive Onboarding Checklist**: Step-by-step tenant provisioning pipeline (`Redact` $\rightarrow$ `Parse` $\rightarrow$ `Train Adapter` $\rightarrow$ `Calibrate Threshold` $\rightarrow$ `Deploy Monitoring`).
- **Analyst Feedback Registry**: UI to review flagged incidents, submit operator feedback (*Confirmed Threat* vs *False Positive*), and record annotations for downstream active learning.

---

## 5. Failure Handling & Dedicated States

1. **`error_state.py`**:
   - Rendered in Live mode when FastAPI connection fails (Connection Refused, Timeout, HTTP 500/404).
   - Shows connection target URL (`http://127.0.0.1:8000`), status code, error details, and a "Retry Connection" button.
   - Explicitly instructs the user on how to launch the backend server (`logsentinel serve --env hdfs`).
2. **`empty_state.py`**:
   - Rendered when an environment has zero scored events.
   - Provides quick actions: "Replay Sample Event" or "Upload Logs".

---

## 6. Accessibility & Visual Design Tokens (`styles.py`)

- **Canvas Background**: Cool near-white `#F7F9FC`
- **Surface Cards**: Pure white `#FFFFFF` with 1px border `#DCE3EC` and 8px corner radius
- **Sidebar Rail**: Graphite Navy `#0B1728` with `#EAF1FA` text and `#0B6CFB` active accent
- **Semantic Indicators**:
  - High Anomaly: `#E3242B` (Crimson) + `●` High label
  - Medium Anomaly: `#FF8A00` (Amber/Orange) + `▲` Med label
  - Low Anomaly: `#F4BF24` (Yellow) + `◆` Low label
  - Normal/Healthy: `#10A66A` (Emerald) + `✔` Ready label
- **Non-Color Dependence**: Every metric, chart element, and table row pairs colors with distinct icons and explicit textual labels.

---

## 7. Verification & Testing Plan

1. **Unit Tests**:
   - `tests/test_ui_models.py`: Test dataclass serialization and type conversions.
   - `tests/test_ui_client.py`: Test FastAPI client connection handling, error parsing, and strict rejection of silent fallbacks.
   - `tests/test_ui_fixtures.py`: Test HDFS and BGL fixture integrity and schema compliance.
2. **Streamlit Component & View Integration Tests**:
   - `tests/test_ui_views.py`: Use Streamlit `AppTest` to verify that all 4 workspaces render cleanly without exceptions.
   - Verify Demo mode renders the honesty banner.
   - Verify Live mode renders `ErrorState` when API is down.
3. **CLI & Backwards Compatibility**:
   - `tests/test_dashboard.py`: Verify that `src/logsentinel/dashboard.py` and `logsentinel dashboard` continue to operate as seamless entry points.
   - `ruff check .` passes with zero lint issues.
   - Wheel build succeeds.
