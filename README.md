# LogSentinel

LogSentinel is a LogLLaMA-inspired research prototype for privacy-safe log anomaly detection. It combines deterministic log templates, statistical baselines, calibrated hybrid scores, optional DeepLog/Qwen model components, a FastAPI service, and a Streamlit operations dashboard.

It is designed for reproducible HDFS and BGL experiments. It is not an autonomous incident-response product and does not ship invented public benchmark results.

## Public demo and research lab

The **Static public showcase** in [`showcase/`](showcase/) is a portfolio-style explanation with an **illustrative replay**. It runs entirely in the visitor's browser, makes no network scoring calls, and never uploads or stores log data. It does not host model inference or claim benchmark results.

The **local Streamlit research lab** is the full Python dashboard used with versioned local artifacts. Run it from this checkout with `logsentinel dashboard --api-url http://127.0.0.1:8000`. The base model and environment adapters remain separate, optional downloads on the external SSD.

## What is implemented

- Streaming Hugging Face record adapters for `logfit-project/HDFS_v1` and `logfit-project/BGL`.
- Redaction before parsing or persistence, including IPs, block IDs, paths, emails, UUIDs, secrets, and long identifiers.
- Drain3 integration plus a deterministic, frozen event vocabulary.
- HDFS block sessions, BGL 60-second windows, and chronological 60/20/20 splits.
- Template rarity, PCA, Isolation Forest, DeepLog building blocks, Qwen2.5-1.5B QLoRA training/inference, and calibrated transformer-hybrid scoring.
- Immutable per-environment artifacts with checksums and parser/model isolation.
- CLI, FastAPI endpoints, and a Streamlit dashboard.
- Synthetic smoke data that is always labeled as illustrative and never presented as a public benchmark.

## Install

Python 3.11 or 3.12 is recommended for the complete ML stack.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[data,dashboard,dev]'
```

On this checkout, keep the virtual environment and every download on the external SSD:

```bash
cd /Volumes/MAC/Projects_devolopment/finetuned
python -m venv --system-site-packages .venv
source .venv/bin/activate
export LOGSENTINEL_STORAGE_ROOT="$PWD/.logsentinel-storage"
export PIP_CACHE_DIR="$LOGSENTINEL_STORAGE_ROOT/cache/pip"
python -m pip install -e '.[data,ml,dashboard,dev]'
logsentinel storage-status --storage-root "$LOGSENTINEL_STORAGE_ROOT"
```

The CLI overrides Hugging Face, Transformers, datasets, Torch, and pip cache variables so they point below the selected storage root. The checked-in `.env.example` lists the exact paths.

For CUDA QLoRA training, install the ML group on a supported Linux/Colab runtime:

```bash
python -m pip install -e '.[data,ml,dev]'
```

## Quick start

Run an offline synthetic smoke workflow. The generated report explicitly states that it is not a public benchmark:

```bash
logsentinel run-all --dataset hdfs --workspace demo --sample-count 240 --version sample-v1
```

Start the API with the resulting artifact:

```bash
logsentinel serve \
  --artifact-root demo/artifacts \
  --environment hdfs \
  --version sample-v1
```

In another terminal, start the dashboard:

```bash
logsentinel dashboard --api-url http://127.0.0.1:8000
```

## Public data workflow

Start with a bounded data pass before attempting full datasets:

```bash
logsentinel prepare \
  --dataset hdfs \
  --limit 100000 \
  --output data/processed/hdfs-100k.json

logsentinel train-baselines \
  --prepared data/processed/hdfs-100k.json \
  --output reports/generated/hdfs-baselines.json

logsentinel calibrate \
  --prepared data/processed/hdfs-100k.json \
  --artifact-root artifacts \
  --version hdfs-100k-v1

logsentinel evaluate \
  --prepared data/processed/hdfs-100k.json \
  --artifact-root artifacts \
  --environment hdfs \
  --version hdfs-100k-v1 \
  --output reports/generated/hdfs-hybrid.json
```

The public mirrors retain LogHub provenance. Review their dataset cards and original terms before redistribution:

- [HDFS_v1](https://huggingface.co/datasets/logfit-project/HDFS_v1)
- [BGL](https://huggingface.co/datasets/logfit-project/BGL)
- [LogHub](https://github.com/logpai/loghub)

## Transformer workflow

Validate the adapter configuration without downloading a model:

```bash
logsentinel train-transformer \
  --prepared data/processed/hdfs-100k.json \
  --output reports/generated/hdfs-transformer-plan.json \
  --dry-run
```

The default model is `Qwen/Qwen2.5-1.5B`, with 4-bit NF4 loading, all-linear LoRA targets, trainable event embeddings/LM head, and gradient checkpointing. Full adapter training should be run from the supplied project on a CUDA/Colab environment; measured results must be generated from the locked temporal test partition.

### Free local inference with the fine-tuned adapter

No hosted inference API is required. Cache the shared base model once on the SSD:

```bash
export LOGSENTINEL_STORAGE_ROOT=/Volumes/MAC/Projects_devolopment/finetuned/.logsentinel-storage
logsentinel download-model \
  --model-id Qwen/Qwen2.5-1.5B \
  --storage-root "$LOGSENTINEL_STORAGE_ROOT"
```

Train on a free Colab CUDA runtime, writing the adapter into mounted persistent storage:

```bash
logsentinel train-transformer \
  --prepared data/processed/hdfs-100k.json \
  --output reports/generated/hdfs-qwen-training.json \
  --adapter-output "$LOGSENTINEL_STORAGE_ROOT/adapters/hdfs-qwen-v1" \
  --storage-root "$LOGSENTINEL_STORAGE_ROOT" \
  --no-dry-run
```

Then calibrate the complete hybrid. This computes Qwen NLL, rank, top-k miss, and entropy for train/validation sequences and snapshots the adapter into the immutable environment artifact:

```bash
logsentinel calibrate \
  --prepared data/processed/hdfs-100k.json \
  --artifact-root "$LOGSENTINEL_STORAGE_ROOT/artifacts" \
  --adapter "$LOGSENTINEL_STORAGE_ROOT/adapters/hdfs-qwen-v1" \
  --storage-root "$LOGSENTINEL_STORAGE_ROOT" \
  --version hdfs-qwen-v1
```

Serve it locally on CPU, Apple Silicon MPS, or CUDA. The API lazily loads the packaged environment adapter, reuses the SSD-cached base model, and returns the four Qwen signals alongside rarity, PCA, and Isolation Forest:

```bash
logsentinel serve \
  --artifact-root "$LOGSENTINEL_STORAGE_ROOT/artifacts" \
  --environment hdfs \
  --version hdfs-qwen-v1 \
  --storage-root "$LOGSENTINEL_STORAGE_ROOT"
```

The statistical-only path remains available by omitting `--adapter` during calibration. That fallback is useful for smoke tests, but it is not represented as transformer inference.

## API

- `POST /v1/score`
- `GET /v1/anomalies`
- `GET /v1/models/{environment}/status`
- `POST /v1/feedback`
- `GET /healthz`

Raw messages are redacted before template matching. Responses contain redacted templates and event IDs, not the submitted raw message.

## Security and limitations

- Artifact files use `joblib` and must only be loaded from trusted local training output. Checksums detect corruption; they do not make untrusted pickle content safe.
- Each environment has an isolated parser, detector, threshold, event vocabulary, adapter snapshot, and version path.
- Validation labels calibrate the fusion model. They are not used in normal-only next-event training.
- The current local prepared JSON format is suitable for bounded experiments. Multi-million-sequence full runs should use a sharded/columnar prepared store rather than a single JSON document.
- Public-log detection delay is only a proxy for enterprise MTTD because the datasets do not include complete incident-ticket timelines.

## Development

```bash
python -m pytest -q
ruff check .
```

The approved implementation plan is in `docs/superpowers/plans/2026-08-20-logsentinel-implementation.md`. The dashboard design reference and extracted tokens are in `docs/design/`.
