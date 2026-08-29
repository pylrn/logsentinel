# LogSentinel Public Showcase and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Publish an evidence-first LogSentinel portfolio site on Vercel, repair Streamlit visual/claim issues, package the reproducible prototype, and publish reviewed source to GitHub.

**Architecture:** A static showcase directory hosts the public story and deterministic redacted replay. Streamlit remains the separate research lab. Provenance labels prevent fixtures or unavailable artifacts being described as live or measured. GitHub contains source and small fixtures only; Vercel serves no models or raw telemetry.

**Tech Stack:** Static HTML/CSS/JavaScript, Streamlit, FastAPI, Pytest, Ruff, Hatchling, GitHub CLI, Vercel CLI.

---

## File structure

- Create: showcase/index.html — semantic landing page and replay controls.
- Create: showcase/assets/styles.css — responsive visual system, contrast and focus rules.
- Create: showcase/assets/replay-data.js — deterministic redacted illustrative fixtures.
- Create: showcase/assets/app.js — replay rendering, selection state, provenance labels.
- Create: showcase/README.md and showcase/404.html.
- Create: tests/test_showcase_static.py — structural and claim-safety checks.
- Create: scripts/build_public_package.py and tests/test_public_package.py — public source builder and exclusion tests.
- Modify: .gitignore, src/logsentinel/ui/styles.py, src/logsentinel/ui/views/journey.py, README.md, MODEL_CARD.md, DATASET_CARD.md, plus focused tests.

## Task 1: Establish a clean public-release boundary

**Files:**
- Modify: .gitignore
- Create: tests/test_public_package.py
- Create: scripts/build_public_package.py

- [ ] **Step 1: Write the failing package-boundary tests**

    from scripts.build_public_package import is_public_path

    def test_public_package_excludes_secrets_data_and_weights() -> None:
        assert not is_public_path(".streamlit/secrets.toml")
        assert not is_public_path(".logsentinel-storage/models/qwen/model.safetensors")
        assert not is_public_path("data/raw/hdfs.log")
        assert not is_public_path("Compiler_Design_Assessment.docx")

    def test_public_package_keeps_source_docs_and_redacted_fixtures() -> None:
        assert is_public_path("src/logsentinel/api.py")
        assert is_public_path("README.md")
        assert is_public_path("showcase/assets/replay-data.js")

- [ ] **Step 2: Run the focused test to prove it fails**

Run: uv run pytest tests/test_public_package.py -v

Expected: FAIL because scripts.build_public_package does not exist.

- [ ] **Step 3: Implement the allowlisted package builder**

Use these exact policies:

    PUBLIC_TOP_LEVEL = {"src", "tests", "docs", "showcase", "scripts"}
    PUBLIC_FILES = {"README.md", "MODEL_CARD.md", "DATASET_CARD.md", "SECURITY.md", "pyproject.toml", "uv.lock", "LICENSE"}
    DENIED_PARTS = {".streamlit", ".logsentinel-storage", ".venv", "data", "artifacts", "dist", "build", "__pycache__"}
    DENIED_SUFFIXES = {".docx", ".pdf", ".safetensors", ".bin", ".pt", ".ckpt"}

Implement is_public_path(relative_path: str) and create dist/logsentinel-public-source-0.1.0.tar.gz strictly from allowed files, printing SHA-256. Ignore secrets, local caches, raw data, artifacts, distributions, virtual environments, and personal Office/PDF files.

- [ ] **Step 4: Verify the boundary**

Run: uv run pytest tests/test_public_package.py -v && uv run python scripts/build_public_package.py --output /tmp/logsentinel-public-source.tar.gz

Expected: PASS; the archive prints a checksum and contains no denied path.

- [ ] **Step 5: Commit**

Run:
    git add .gitignore scripts/build_public_package.py tests/test_public_package.py
    git commit -m "build: add safe public source package boundary"

## Task 2: Correct Streamlit claims and contrast

**Files:**
- Modify: src/logsentinel/ui/styles.py
- Modify: src/logsentinel/ui/views/journey.py
- Modify: tests/test_ui_journey.py and tests/test_ui_styles.py

- [ ] **Step 1: Write failing provenance and contrast tests**

    def test_journey_marks_examples_as_illustrative() -> None:
        source = Path("src/logsentinel/ui/views/journey.py").read_text()
        assert "Illustrative replay" in source
        assert "1.2ms" not in source
        assert "$50,000" not in source

    def test_theme_does_not_set_colour_on_every_div_and_span() -> None:
        css = get_theme_css()
        assert "p, span, div" not in css
        assert ".provenance-badge" in css

- [ ] **Step 2: Verify the tests fail**

Run: uv run pytest tests/test_ui_journey.py tests/test_ui_styles.py -v

Expected: FAIL because the current journey contains unmeasured claims and the theme has an over-broad selector.

- [ ] **Step 3: Implement the correction**

Replace the global p, span, div colour rule with scoped Streamlit content rules. Add journey-hero, journey-eyebrow, journey-copy, provenance-badge, provenance-illustrative, provenance-measured, and provenance-unavailable classes with explicit WCAG-AA foreground/background/border colours and visible focus styles.

Replace direct inline hero markup in journey.py with those classes. Label fixture content “Illustrative replay”; say neural signals are optional unless an adapter artifact is loaded; replace causal MITRE attribution with rule-based analyst guidance; and use the actual ScoreRequest fields from api.py. Remove unmeasured latency, cost, benchmark, and zero-day claims.

- [ ] **Step 4: Verify focused UI tests**

Run: uv run pytest tests/test_ui_journey.py tests/test_ui_styles.py tests/test_dashboard.py -v

Expected: PASS.

- [ ] **Step 5: Commit**

Run:
    git add src/logsentinel/ui/styles.py src/logsentinel/ui/views/journey.py tests/test_ui_journey.py tests/test_ui_styles.py
    git commit -m "fix(ui): scope contrast styles and label illustrative journey"

## Task 3: Build the Screentune-inspired public page

**Files:**
- Create: showcase/index.html, showcase/assets/styles.css, showcase/404.html, showcase/README.md
- Create: tests/test_showcase_static.py

- [ ] **Step 1: Write failing structure and claim tests**

    def test_showcase_has_required_evidence_sections() -> None:
        page = Path("showcase/index.html").read_text()
        for marker in ("How it works", "Sample replay", "Evidence & limits", "Onboard an environment", "Run it yourself"):
            assert marker in page
        assert 'id="replay"' in page

    def test_showcase_never_claims_hosted_inference() -> None:
        content = "\n".join(
            path.read_text() for path in Path("showcase").rglob("*.*")
            if path.suffix in {".html", ".css", ".js"}
        )
        assert "live model" not in content.lower()
        assert "zero-day" not in content.lower()

- [ ] **Step 2: Verify they fail**

Run: uv run pytest tests/test_showcase_static.py -v

Expected: FAIL because showcase is absent.

- [ ] **Step 3: Implement the static shell**

Use semantic landmarks:

    <a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header">...</header>
    <main id="main">
      <section class="hero" aria-labelledby="hero-title">...</section>
      <section id="workflow" aria-labelledby="workflow-title">...</section>
      <section id="replay" aria-labelledby="replay-title">...</section>
      <section id="evidence" aria-labelledby="evidence-title">...</section>
      <section id="onboarding" aria-labelledby="onboarding-title">...</section>
      <section id="run" aria-labelledby="run-title">...</section>
    </main>

Use calm off-white content, near-black hero, one electric-blue accent, severity colours paired with text/icons, large display type, compact eyebrow, subtle borders, no copied branding. At 700px or narrower, stack cards, make controls full width, and respect prefers-reduced-motion.

- [ ] **Step 4: Verify static tests**

Run: uv run pytest tests/test_showcase_static.py -v

Expected: PASS.

- [ ] **Step 5: Commit**

Run:
    git add showcase/index.html showcase/assets/styles.css showcase/404.html showcase/README.md tests/test_showcase_static.py
    git commit -m "feat(showcase): add evidence-first public landing page"

## Task 4: Implement the deterministic browser replay

**Files:**
- Create: showcase/assets/replay-data.js and showcase/assets/app.js
- Modify: showcase/index.html and tests/test_showcase_static.py

- [ ] **Step 1: Write failing replay-safety tests**

    def test_replay_uses_redacted_deterministic_fixtures() -> None:
        fixture = Path("showcase/assets/replay-data.js").read_text()
        assert "<IP>" in fixture
        assert "<USER_ID>" in fixture
        assert "illustrative" in fixture.lower()
        assert "198.51.100.42" not in fixture

    def test_replay_has_no_external_api_call() -> None:
        app = Path("showcase/assets/app.js").read_text()
        assert "fetch(" not in app

- [ ] **Step 2: Verify tests fail**

Run: uv run pytest tests/test_showcase_static.py -v

Expected: FAIL because replay files do not exist.

- [ ] **Step 3: Implement replay data and behavior**

Define REPLAY_ENVIRONMENTS containing hdfs, bgl, and security-demo. Each has label, provenance, status: "illustrative", and 5–8 redacted events. Every event includes template, score, threshold, ordered component contributions, expected templates, and rule-based explanation.

Render an environment selector, event list, selected-event inspector, contribution bars with text values, and expected/observed comparison. JavaScript must only read local fixture data, use textContent, maintain aria-pressed/selected state, never call fetch, never persist logs, and never call results measured.

- [ ] **Step 4: Verify and exercise every branch**

Run: uv run pytest tests/test_showcase_static.py -v

Expected: PASS. Serve locally, select every environment/event, and confirm each badge remains “Illustrative replay.”

- [ ] **Step 5: Commit**

Run:
    git add showcase/index.html showcase/assets/replay-data.js showcase/assets/app.js tests/test_showcase_static.py
    git commit -m "feat(showcase): add local redacted anomaly replay"

## Task 5: Reconcile documentation and distribution metadata

**Files:**
- Modify: README.md, MODEL_CARD.md, DATASET_CARD.md, tests/test_packaging.py

- [ ] **Step 1: Write failing documentation test**

    def test_readme_distinguishes_showcase_from_local_lab() -> None:
        readme = Path("README.md").read_text()
        assert "Static public showcase" in readme
        assert "local Streamlit research lab" in readme
        assert "illustrative replay" in readme.lower()

- [ ] **Step 2: Verify it fails**

Run: uv run pytest tests/test_packaging.py -v

Expected: FAIL until README describes the release boundary.

- [ ] **Step 3: Update written artifacts**

Add “Public demo and research lab” near the README start. Explain static demo has no hosted inference; retain SSD storage guidance; distinguish static replay, local lab, artifact generation, and optional QLoRA training. In cards, mark results as generated artifacts, fixtures, or unavailable, and remove numbers without committed manifests.

- [ ] **Step 4: Build and inspect distributions**

Run: uv build && uv run pytest tests/test_packaging.py -v && tar -tzf /tmp/logsentinel-public-source.tar.gz | rg 'secrets|safetensors|data/raw'

Expected: wheel/source builds, test passes, final command emits nothing.

- [ ] **Step 5: Commit**

Run:
    git add README.md MODEL_CARD.md DATASET_CARD.md tests/test_packaging.py
    git commit -m "docs: clarify public demo and artifact boundary"

## Task 6: Functional, visual, and accessibility verification

**Files:**
- Modify only files from Tasks 2–5 if focused verification shows a defect.

- [ ] **Step 1: Start local surfaces**

Run Streamlit with:
    uv run streamlit run dashboard.py --server.port 8501

Run the static site with:
    python -m http.server 4173 --directory showcase

Expected: Streamlit responds on 8501 and static page on 4173.

- [ ] **Step 2: Validate actual API contract**

Run: uv run pytest tests/test_live_contract_integration.py tests/test_api.py -v

Expected: PASS. If example copy differs from the endpoint schema, correct copy/test only; do not invent fields.

- [ ] **Step 3: Screenshot desktop output**

Capture 1440px screenshots of both local URLs with browser controls. Inspect hero contrast, sidebar/control contrast, clipped labels, focus visibility, textual severity labels, empty and error states.

- [ ] **Step 4: Screenshot mobile output**

Capture the same URLs at 390px. Verify no horizontal scroll, clipped navigation/controls, unreadable detail, or undersized touch targets. Keep screenshots in /tmp or a gitignored report directory.

- [ ] **Step 5: Run release gates**

Run: uv run ruff check . && uv run pytest -q && uv build

Expected: all checks pass. Record actual totals, never historical counts.

- [ ] **Step 6: Commit only focused QA fixes**

Run:
    git add showcase src/logsentinel/ui README.md MODEL_CARD.md DATASET_CARD.md tests .gitignore scripts
    git commit -m "fix: polish public showcase after visual QA"

## Task 7: Deploy Vercel and publish GitHub

**Files:**
- Create: vercel.json only if Vercel requires it.
- Modify: showcase/README.md and README.md only after production URL verification.

- [ ] **Step 1: Audit publish scope**

Run: git status --short && git diff --cached --name-only && git ls-files | rg '(^|/)(secrets\.toml|.*\.safetensors|.*\.docx|.*\.pdf)$'

Expected: secrets, weights, personal docs, and raw data are neither tracked nor staged. Stop and remove any offending index entry before publishing.

- [ ] **Step 2: Deploy only static showcase**

Run: npx vercel --cwd showcase

Expected: preview build returns a URL and uses no server function, model upload, or secret. If Vercel presents new terms or requests credentials, hand off that exact screen. After preview visual checks, run:
    npx vercel --cwd showcase --prod

- [ ] **Step 3: Verify the production URL**

Hard-refresh, exercise replay, test source/local-lab links, and capture desktop/mobile screenshots.

- [ ] **Step 4: Create and push GitHub repository**

First run gh repo view pylrn/logsentinel. If absent:
    gh repo create logsentinel --public --source=. --remote=origin --push

If present, configure the known remote and push without force. Add verified Vercel URL to README, commit, and push that small change.

- [ ] **Step 5: Final release check**

Run: git status --short && gh repo view --web=false && uv run python scripts/build_public_package.py --output /tmp/logsentinel-public-source.tar.gz

Expected: only deliberately preserved user changes remain; public repo resolves; public source package prints checksum and respects exclusions.
