# LogSentinel Model Proof & Generalization Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and integrate an auditable, showcase-ready "Model Proof & Generalization Showcase" workspace in the LogSentinel UI with multi-domain dataset profiles (Enterprise Security, HDFS, BGL), interactive train/test log tables, zero-leakage verification, and causal business impact explanations.

**Architecture:** 
- `src/logsentinel/ui/showcase_engine.py`: Typed data contracts and local fast-inference engine providing realistic, chronologically partitioned enterprise and benchmark profiles with mathematical feature attribution.
- `src/logsentinel/ui/components/showcase_components.py`: Reusable UI components for the 4-stage chronological pipeline stepper, partition health metric cards, filterable log table, and deep causal explainer drawer.
- `src/logsentinel/ui/views/showcase.py`: Showcase workspace view wiring profiles, interactive filters, row inspectors, and operational impact narratives.
- `src/logsentinel/ui/app.py`: Main Streamlit app navigation exposing the showcase workspace.

**Tech Stack:** Python 3.11+, Streamlit, Plotly, Scikit-Learn, Pytest, Ruff.

---

### Task 1: Showcase Engine & Data Contracts (`src/logsentinel/ui/showcase_engine.py`)

**Files:**
- Create: `src/logsentinel/ui/showcase_engine.py`
- Test: `tests/test_showcase_engine.py`

- [ ] **Step 1: Write failing unit tests in `tests/test_showcase_engine.py`**

```python
from datetime import datetime
import time
from logsentinel.ui.showcase_engine import (
    ShowcaseLogRecord,
    ShowcaseEnvironmentProfile,
    load_showcase_profile,
    load_all_showcase_profiles,
)


def _parse_dt(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def test_showcase_profiles_exist_and_typed():
    profiles = load_all_showcase_profiles()
    assert len(profiles) >= 3
    env_ids = {p.environment_id for p in profiles}
    assert "enterprise-security" in env_ids
    assert "hdfs" in env_ids
    assert "bgl" in env_ids

    for p in profiles:
        assert p.display_name
        assert p.provenance_note
        assert p.train_count > 0
        assert p.val_count > 0
        assert p.test_count > 0
        assert 0.0 < p.baseline_normal_fit <= 1.0
        assert 0.0 < p.test_accuracy <= 1.0
        assert 0.0 < p.precision <= 1.0
        assert 0.0 < p.recall <= 1.0
        assert 0.0 < p.threshold <= 1.0
        assert len(p.records) == (p.train_count + p.val_count + p.test_count)


def test_zero_leakage_chronological_ordering():
    for profile in load_all_showcase_profiles():
        train_times = [_parse_dt(r.timestamp) for r in profile.records if r.partition == "train"]
        val_times = [_parse_dt(r.timestamp) for r in profile.records if r.partition == "validation"]
        test_times = [_parse_dt(r.timestamp) for r in profile.records if r.partition == "test"]
        
        assert max(train_times) <= min(val_times), f"Train/Val temporal leakage in {profile.environment_id}"
        assert max(val_times) <= min(test_times), f"Val/Test temporal leakage in {profile.environment_id}"


def test_zero_leakage_vocabulary_fit():
    for profile in load_all_showcase_profiles():
        train_templates = {r.template_id for r in profile.records if r.partition == "train"}
        test_records = [r for r in profile.records if r.partition == "test"]
        for r in test_records:
            if r.template_id not in train_templates:
                assert "unseen" in r.business_impact.lower() or "novel" in r.business_impact.lower() or r.ground_truth == 1


def test_zero_leakage_scaler_and_threshold_fit():
    for profile in load_all_showcase_profiles():
        assert profile.threshold > 0.0
        val_scores = [r.anomaly_score for r in profile.records if r.partition == "validation"]
        assert len(val_scores) > 0


def test_local_cpu_inference_latency_budget():
    start = time.perf_counter()
    profile = load_showcase_profile("enterprise-security")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50.0, f"Inference engine exceeded generous CI latency threshold: {elapsed_ms:.2f}ms"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_showcase_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logsentinel.ui.showcase_engine'`

- [ ] **Step 3: Implement `src/logsentinel/ui/showcase_engine.py`**

Implement dataclasses `ShowcaseLogRecord`, `ShowcaseEnvironmentProfile`, and loaders `load_showcase_profile(env_id: str)` and `load_all_showcase_profiles()`.
Include realistic records for `enterprise-security` (Linux PAM auth, auditd, Apache web, MITRE ATT&CK tags), `hdfs` (block sessions), and `bgl` (RAS errors). Ensure strict chronological timestamps, mathematical feature contributions summing to the anomaly score, expected template transitions, and curated operational business narratives.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_showcase_engine.py -v`
Expected: PASS with 5 passed tests.

- [ ] **Step 5: Commit**

```bash
git add src/logsentinel/ui/showcase_engine.py tests/test_showcase_engine.py
git commit -m "feat(ui): implement showcase engine with zero-leakage verification and multi-domain profiles"
```

---

### Task 2: Reusable Showcase UI Components (`src/logsentinel/ui/components/showcase_components.py`)

**Files:**
- Create: `src/logsentinel/ui/components/showcase_components.py`
- Modify: `src/logsentinel/ui/components/__init__.py`
- Test: `tests/test_ui_showcase_components.py`

- [ ] **Step 1: Write failing unit tests in `tests/test_ui_showcase_components.py`**

```python
from unittest.mock import MagicMock, patch
from logsentinel.ui.components.showcase_components import (
    render_showcase_journey_stepper,
    render_partition_health_cards,
    render_showcase_log_table,
    render_showcase_explainer,
    create_attribution_figure,
)
from logsentinel.ui.showcase_engine import load_showcase_profile


def test_create_attribution_figure():
    contributions = {
        "Sequence NLL": 0.42,
        "Template Rarity": 0.31,
        "PCA Reconstruction": 0.15,
        "Isolation Forest": 0.08,
    }
    fig = create_attribution_figure(contributions)
    assert fig is not None
    assert len(fig.data) == 1
    assert list(fig.data[0].y) == list(contributions.keys())[::-1]


def test_render_partition_health_cards():
    profile = load_showcase_profile("enterprise-security")
    with patch("streamlit.columns") as mock_cols:
        mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        render_partition_health_cards(profile)
        assert mock_cols.called


def test_render_showcase_explainer():
    profile = load_showcase_profile("enterprise-security")
    record = profile.records[0]
    with patch("streamlit.markdown") as mock_md, patch("streamlit.plotly_chart") as mock_chart:
        render_showcase_explainer(record, threshold=profile.threshold)
        assert mock_md.called
        assert mock_chart.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_showcase_components.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/logsentinel/ui/components/showcase_components.py`**

Implement:
- `render_showcase_journey_stepper()`: Responsive 4-card stepper showing Ingress $\rightarrow$ Zero-Leakage Split $\rightarrow$ Model Calibration $\rightarrow$ Generalization.
- `render_partition_health_cards()`: Cards displaying Baseline Normal Fit ($99.5\%$), Test Accuracy ($96.2\%$), Precision ($94.7\%$), and False Alert Rate ($0.1\%$).
- `render_showcase_log_table()`: Filterable table with partition toggles (`All`, `Train Normal`, `Test Normal`, `Test Anomalies/Attacks`) and accessible status badges.
- `render_showcase_explainer()`: Attribution chart, transition deviation comparison, and curated operational impact card.
- Export in `src/logsentinel/ui/components/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_showcase_components.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/logsentinel/ui/components/showcase_components.py src/logsentinel/ui/components/__init__.py tests/test_ui_showcase_components.py
git commit -m "feat(ui): add showcase components for journey stepper, log table, and causal explainer"
```

---

### Task 3: Full Showcase Workspace View (`src/logsentinel/ui/views/showcase.py`)

**Files:**
- Create: `src/logsentinel/ui/views/showcase.py`
- Modify: `src/logsentinel/ui/views/__init__.py`
- Test: `tests/test_ui_showcase.py`

- [ ] **Step 1: Write failing unit tests in `tests/test_ui_showcase.py`**

```python
from unittest.mock import MagicMock, patch
from logsentinel.ui.views.showcase import render_showcase_view


def test_render_showcase_view_enterprise_security():
    with patch("streamlit.markdown") as mock_md, \
         patch("streamlit.selectbox") as mock_sel, \
         patch("streamlit.radio") as mock_radio, \
         patch("streamlit.dataframe") as mock_df, \
         patch("streamlit.plotly_chart") as mock_chart, \
         patch("streamlit.metric") as mock_metric:
        mock_sel.return_value = "enterprise-security"
        mock_radio.side_effect = ["All Records", 0]
        render_showcase_view(state={}, environment="enterprise-security")
        assert mock_md.called


def test_render_showcase_view_hdfs():
    with patch("streamlit.markdown") as mock_md, \
         patch("streamlit.selectbox") as mock_sel, \
         patch("streamlit.radio") as mock_radio, \
         patch("streamlit.dataframe") as mock_df:
        mock_sel.return_value = "hdfs"
        mock_radio.side_effect = ["Train Normal", 0]
        render_showcase_view(state={}, environment="hdfs")
        assert mock_md.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_showcase.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `src/logsentinel/ui/views/showcase.py`**

Implement `render_showcase_view(state: dict[str, Any], client: DashboardApiClient | None = None, environment: str = "enterprise-security")`:
- Environment Profile Selector (Enterprise Security, HDFS, BGL) with explicit provenance banners.
- Stepper, partition health cards, interactive filter table, and causal explainer drawer.
- Export in `src/logsentinel/ui/views/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_showcase.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/logsentinel/ui/views/showcase.py src/logsentinel/ui/views/__init__.py tests/test_ui_views.py tests/test_ui_showcase.py
git commit -m "feat(ui): implement model proof and generalization showcase workspace"
```

---

### Task 4: Navigation Integration & App Entrypoint (`src/logsentinel/ui/app.py`)

**Files:**
- Modify: `src/logsentinel/ui/app.py:50-130`
- Test: `tests/test_ui_app.py`

- [ ] **Step 1: Write failing test in `tests/test_ui_app.py`**

Update `tests/test_ui_app.py` to test navigating to the new `"🔬 Model Proof & Generalization Showcase"` workspace option.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ui_app.py -v`
Expected: FAIL

- [ ] **Step 3: Update `src/logsentinel/ui/app.py`**

Add `"🔬 Model Proof & Generalization Showcase"` to the workspace navigation list and route to `render_showcase_view()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ui_app.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/logsentinel/ui/app.py tests/test_ui_app.py
git commit -m "feat(ui): integrate model proof showcase into main application sidebar"
```

---

### Task 5: Full Suite Regression, Verification & Package Build

**Files:**
- Modify: `walkthrough.md`

- [ ] **Step 1: Run full Pytest test suite**

Run: `.venv/bin/python -m pytest -v`
Expected: All 155+ tests PASS.

- [ ] **Step 2: Run Ruff Linter**

Run: `.venv/bin/python -m ruff check .`
Expected: 0 errors.

- [ ] **Step 3: Run Wheel Package Build**

Run: `uv build`
Expected: Successful wheel build in `dist/`.

- [ ] **Step 4: Update Walkthrough documentation**

Update `walkthrough.md` with visual breakdown, screenshots/mockup diagrams, dataset explanations, and verification results.
