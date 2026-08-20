# LogSentinel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible HDFS/BGL anomaly-detection research prototype with privacy-safe preprocessing, hybrid models, API, CLI, dashboard, and verification.

**Architecture:** Raw public records are validated and redacted before deterministic template mining. Dataset-specific sequences feed statistical baselines and optional DeepLog/Qwen adapters; calibrated component scores are packaged into isolated environment artifacts and served through FastAPI and Streamlit.

**Tech Stack:** Python 3.11–3.13, Pydantic, Drain3, scikit-learn, PyTorch, Transformers/PEFT, FastAPI, Typer, Streamlit, pytest.

---

### Task 1: Reproducible project foundation

- [ ] Add packaging, dependency groups, CI-friendly test configuration, ignore rules, and architecture documentation.
- [ ] Verify the empty baseline and create failing core-domain tests.

### Task 2: Privacy-safe data domain

- [ ] Test and implement canonical event validation, deterministic host/group hashing, redaction, template IDs, HDFS grouping, BGL windows, and chronological splits.
- [ ] Confirm secrets cannot appear in cached normalized records.

### Task 3: Detection and evaluation core

- [ ] Test and implement statistical feature extraction, rarity/PCA/iForest baselines, logistic fusion, normal-only calibration, metrics, confidence intervals, and versioned artifacts.
- [ ] Confirm all train-fitted state rejects or safely handles unknown templates.

### Task 4: Neural training interfaces

- [ ] Test and implement DeepLog datasets/model, Qwen event-token serialization, QLoRA configuration, next-event scores, and lazy optional-dependency failures.
- [ ] Add sample-mode workflow and Colab entrypoint; never invent full-data benchmark output.

### Task 5: Product interfaces

- [ ] Test and implement prepare/train/calibrate/evaluate/run-all/serve CLI commands.
- [ ] Test and implement scoring, anomaly query, model status, feedback and health APIs.
- [ ] Implement the Streamlit replay, anomaly, benchmark, threshold, drift and onboarding views.

### Task 6: Verification and handoff

- [ ] Run unit, integration, API, adversarial, lint, sample-pipeline, and packaging checks.
- [ ] Document dataset provenance, full-data commands, limitations, security posture, model card, dataset card, and honest benchmark-report behavior.

