from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import numpy as np
import typer

from logsentinel.artifacts import ArtifactStore
from logsentinel.data import iter_public_records
from logsentinel.detection import (
    IsolationForestDetector,
    PCADetector,
    RarityDetector,
)
from logsentinel.evaluation import classification_report
from logsentinel.manifests import build_run_manifest, write_immutable_manifest
from logsentinel.neural import DeepLogDetector, EventTokenCodec, QLoRASettings, train_qwen_adapter
from logsentinel.pipeline import select_f1_threshold
from logsentinel.schemas import DatasetName
from logsentinel.workflow import (
    PreparedDataset,
    prepare_events,
    sample_events,
    train_hybrid_artifact,
)

app = typer.Typer(
    name="logsentinel",
    help="Privacy-safe log anomaly detection research and demonstration toolkit.",
    no_args_is_help=True,
)


@app.command()
def prepare(
    dataset: Annotated[DatasetName, typer.Option()],
    output: Annotated[Path, typer.Option()],
    limit: Annotated[int | None, typer.Option(min=20)] = None,
    sample: Annotated[bool, typer.Option(help="Use deterministic synthetic smoke data.")] = False,
) -> None:
    """Redact, parse, sequence and temporally split HDFS or BGL events."""
    if sample:
        events = sample_events(dataset, count=limit or 240)
    else:
        events = list(iter_public_records(dataset, limit=limit))
    prepared = prepare_events(events, dataset=dataset)
    prepared.save(output)
    typer.echo(
        f"Prepared {dataset.value}: train={len(prepared.train)} "
        f"validation={len(prepared.validation)} test={len(prepared.test)} "
        f"split={prepared.split_id}"
    )


@app.command("train-baselines")
def train_baselines(
    prepared: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Train and evaluate rarity, PCA and Isolation Forest baselines."""
    dataset = PreparedDataset.load(prepared)
    report = _baseline_report(dataset)
    _write_json(output, report)
    typer.echo(f"Baseline report written to {output}")


@app.command("train-transformer")
def train_transformer(
    prepared: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()],
    adapter_output: Annotated[Path | None, typer.Option()] = None,
    dry_run: Annotated[bool, typer.Option()] = True,
) -> None:
    """Validate or execute the Qwen2.5 QLoRA adapter-training configuration."""
    dataset = PreparedDataset.load(prepared)
    codec = EventTokenCodec.fit([row.event_ids for row in dataset.train])
    settings = QLoRASettings()
    payload = {
        "status": "dry-run" if dry_run else "training",
        "dataset": dataset.dataset.value,
        "base_model": settings.base_model,
        "load_in_4bit": settings.load_in_4bit,
        "target_modules": settings.target_modules,
        "gradient_checkpointing": settings.gradient_checkpointing,
        "max_length": settings.max_length,
        "training_sequences": len(dataset.train),
        "event_vocabulary_size": len(codec.event_ids),
        "added_tokens": len(codec.added_tokens),
    }
    if not dry_run:
        target = adapter_output or output.with_suffix("")
        summary = train_qwen_adapter(
            codec=codec,
            sequences=[row.event_ids for row in dataset.train],
            output_dir=target,
            settings=settings,
        )
        payload.update(
            status="trained",
            adapter_output=summary.output_dir,
        )
    _write_json(output, payload)
    typer.echo(f"Transformer configuration written to {output}")


@app.command()
def calibrate(
    prepared: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    artifact_root: Annotated[Path, typer.Option()],
    version: Annotated[str, typer.Option()] = "v1",
) -> None:
    """Fit calibrated hybrid scoring and save an immutable environment artifact."""
    dataset = PreparedDataset.load(prepared)
    artifact = train_hybrid_artifact(
        dataset, version=version, artifact_root=artifact_root
    )
    typer.echo(
        f"Saved {artifact.metadata.environment.value}/{version} "
        f"threshold={artifact.metadata.threshold:.6f}"
    )


@app.command()
def evaluate(
    prepared: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    artifact_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    environment: Annotated[DatasetName, typer.Option()],
    version: Annotated[str, typer.Option()],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Evaluate a locked artifact on the prepared temporal test partition."""
    dataset = PreparedDataset.load(prepared)
    artifact = ArtifactStore(artifact_root).load(environment, version)
    scores = np.asarray(
        [item.anomaly_score for item in artifact.detector.score(list(dataset.test))]
    )
    labels = np.asarray([item.label for item in dataset.test])
    report = classification_report(
        labels=labels, scores=scores, threshold=artifact.metadata.threshold
    )
    _write_json(output, report)
    typer.echo(f"Evaluation report written to {output}")


@app.command("run-all")
def run_all(
    dataset: Annotated[DatasetName, typer.Option()],
    workspace: Annotated[Path, typer.Option()] = Path("."),
    sample_count: Annotated[int, typer.Option(min=20)] = 240,
    version: Annotated[str, typer.Option()] = "sample-v1",
) -> None:
    """Run a deterministic local smoke workflow without claiming public benchmarks."""
    prepared = prepare_events(sample_events(dataset, count=sample_count), dataset=dataset)
    prepared_path = workspace / "prepared" / f"{dataset.value}.json"
    prepared.save(prepared_path)
    artifact = train_hybrid_artifact(
        prepared,
        version=version,
        artifact_root=workspace / "artifacts",
    )
    scores = np.asarray(
        [item.anomaly_score for item in artifact.detector.score(list(prepared.test))]
    )
    labels = np.asarray([item.label for item in prepared.test])
    hybrid = classification_report(
        labels=labels, scores=scores, threshold=artifact.metadata.threshold
    )
    report = {
        "benchmark_scope": "synthetic-smoke-test",
        "not_a_public_benchmark": True,
        "dataset_shape": {
            "train": len(prepared.train),
            "validation": len(prepared.validation),
            "test": len(prepared.test),
        },
        "split_id": prepared.split_id,
        "hybrid": hybrid,
        "baselines": _baseline_report(prepared),
    }
    report_path = workspace / "reports" / f"{dataset.value}-{version}.json"
    _write_json(report_path, report)
    manifest = build_run_manifest(
        dataset=dataset,
        split_id=prepared.split_id,
        input_path=prepared_path,
        seed=42,
        artifacts={
            "prepared": str(prepared_path),
            "model": str(workspace / "artifacts" / dataset.value / version),
            "report": str(report_path),
        },
    )
    write_immutable_manifest(
        manifest, workspace / "manifests" / f"{dataset.value}-{version}.json"
    )
    typer.echo(f"Smoke workflow complete. Report: {report_path}")


@app.command()
def serve(
    artifact_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    environment: Annotated[list[DatasetName], typer.Option()],
    version: Annotated[list[str], typer.Option()],
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option(min=1, max=65535)] = 8000,
) -> None:
    """Serve one or more isolated model artifacts with FastAPI."""
    if len(environment) != len(version):
        raise typer.BadParameter("provide one --version for each --environment")
    import uvicorn

    from logsentinel.api import ModelRegistry, create_app

    store = ArtifactStore(artifact_root)
    registry = ModelRegistry(
        [
            store.load(selected, release)
            for selected, release in zip(environment, version, strict=True)
        ]
    )
    uvicorn.run(create_app(registry), host=host, port=port)


@app.command()
def dashboard(
    api_url: Annotated[str, typer.Option()] = "http://127.0.0.1:8000",
) -> None:
    """Launch the Streamlit dashboard against a running LogSentinel API."""
    try:
        from streamlit.web import cli as streamlit_cli
    except ImportError as exc:
        raise typer.BadParameter(
            "dashboard requires: pip install 'logsentinel[dashboard]'"
        ) from exc
    import sys

    from logsentinel import dashboard as dashboard_module

    sys.argv = [
        "streamlit",
        "run",
        str(Path(dashboard_module.__file__).resolve()),
        "--",
        "--api-url",
        api_url,
    ]
    raise typer.Exit(streamlit_cli.main())


def _baseline_report(dataset: PreparedDataset) -> dict[str, dict[str, float]]:
    report = {}
    labels_validation = np.asarray([item.label for item in dataset.validation])
    labels_test = np.asarray([item.label for item in dataset.test])
    detectors = {
        "rarity": RarityDetector(),
        "pca": PCADetector(),
        "isolation_forest": IsolationForestDetector(random_state=42),
        "deep_log": DeepLogDetector(
            context_size=16,
            embedding_dim=16,
            hidden_dim=32,
            layers=1,
            epochs=1,
            batch_size=64,
            random_state=42,
        ),
    }
    for name, detector in detectors.items():
        detector.fit(list(dataset.train))
        validation_scores = detector.score(list(dataset.validation))
        threshold = select_f1_threshold(labels_validation, validation_scores)
        scores = detector.score(list(dataset.test))
        report[name] = classification_report(
            labels=labels_test, scores=scores, threshold=threshold
        )
    return report


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    app()
