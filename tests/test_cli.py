from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import logsentinel.cli as cli_module
from logsentinel.cli import app
from logsentinel.neural import TransformerSequenceScore, TransformerTrainingSummary

runner = CliRunner()


def test_cli_exposes_approved_workflow_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in (
        "prepare",
        "train-baselines",
        "train-transformer",
        "calibrate",
        "evaluate",
        "run-all",
        "serve",
        "dashboard",
        "storage-status",
        "download-model",
    ):
        assert command in result.stdout


def test_run_all_sample_creates_prepared_artifact_and_honest_report(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "run-all",
            "--dataset",
            "hdfs",
            "--workspace",
            str(tmp_path),
            "--sample-count",
            "180",
            "--version",
            "smoke-v1",
        ],
    )
    assert result.exit_code == 0, result.stdout
    prepared = tmp_path / "prepared" / "hdfs.json"
    artifact = tmp_path / "artifacts" / "hdfs" / "smoke-v1" / "integrity.json"
    report = tmp_path / "reports" / "hdfs-smoke-v1.json"
    manifest = tmp_path / "manifests" / "hdfs-smoke-v1.json"
    assert prepared.is_file()
    assert artifact.is_file()
    assert report.is_file()
    assert manifest.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["benchmark_scope"] == "synthetic-smoke-test"
    assert payload["not_a_public_benchmark"] is True
    assert {"precision", "recall", "f1", "pr_auc"} <= set(payload["hybrid"])
    assert "deep_log" in payload["baselines"]
    run = json.loads(manifest.read_text(encoding="utf-8"))
    assert run["dataset"] == "hdfs"
    assert run["split_id"] == payload["split_id"]
    assert run["input_checksum"]
    assert run["dependencies"]["logsentinel"] == "0.1.0"


def test_prepare_sample_is_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    for target in (first, second):
        result = runner.invoke(
            app,
            [
                "prepare",
                "--dataset",
                "bgl",
                "--sample",
                "--limit",
                "120",
                "--output",
                str(target),
            ],
        )
        assert result.exit_code == 0, result.stdout
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_train_transformer_dry_run_writes_no_fake_metrics(tmp_path: Path) -> None:
    prepared = tmp_path / "prepared.json"
    prep = runner.invoke(
        app,
        [
            "prepare",
            "--dataset",
            "hdfs",
            "--sample",
            "--limit",
            "120",
            "--output",
            str(prepared),
        ],
    )
    assert prep.exit_code == 0
    output = tmp_path / "transformer-plan.json"
    result = runner.invoke(
        app,
        [
            "train-transformer",
            "--prepared",
            str(prepared),
            "--output",
            str(output),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["base_model"] == "Qwen/Qwen2.5-1.5B"
    assert payload["status"] == "dry-run"
    assert "metrics" not in payload


def test_train_transformer_execute_calls_adapter_trainer(tmp_path: Path, monkeypatch) -> None:
    prepared = tmp_path / "prepared.json"
    prep = runner.invoke(
        app,
        [
            "prepare",
            "--dataset",
            "hdfs",
            "--sample",
            "--limit",
            "120",
            "--output",
            str(prepared),
        ],
    )
    assert prep.exit_code == 0
    called: dict[str, object] = {}

    def fake_train(**kwargs):
        called.update(kwargs)
        return TransformerTrainingSummary(
            output_dir=str(kwargs["output_dir"]),
            training_sequences=len(kwargs["sequences"]),
            event_vocabulary_size=len(kwargs["codec"].event_ids),
            base_model="Qwen/Qwen2.5-1.5B",
        )

    monkeypatch.setattr(cli_module, "train_qwen_adapter", fake_train)
    output = tmp_path / "training.json"
    adapter = tmp_path / "adapter"
    result = runner.invoke(
        app,
        [
            "train-transformer",
            "--prepared",
            str(prepared),
            "--output",
            str(output),
            "--adapter-output",
            str(adapter),
            "--no-dry-run",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert called["output_dir"] == adapter
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "trained"


def test_storage_status_reports_all_caches_under_external_root(tmp_path: Path) -> None:
    storage = tmp_path / "ssd"
    result = runner.invoke(
        app, ["storage-status", "--storage-root", str(storage)]
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["root"] == str(storage.resolve())
    assert all(
        Path(value).is_relative_to(storage)
        for value in payload["cache_environment"].values()
        if value.startswith("/")
    )


def test_calibrate_with_adapter_builds_transformer_hybrid(
    tmp_path: Path, monkeypatch
) -> None:
    prepared = tmp_path / "prepared.json"
    prep = runner.invoke(
        app,
        [
            "prepare",
            "--dataset",
            "hdfs",
            "--sample",
            "--limit",
            "180",
            "--output",
            str(prepared),
            "--storage-root",
            str(tmp_path / "storage"),
        ],
    )
    assert prep.exit_code == 0, prep.stdout
    adapter = tmp_path / "storage" / "adapters" / "hdfs-v1"
    adapter.mkdir(parents=True)
    (adapter / "logsentinel_adapter.json").write_text("{}", encoding="utf-8")

    class FakeScorer:
        def score(self, sequences):
            return [
                TransformerSequenceScore(
                    negative_log_likelihood=3.0 if row.label else 0.2,
                    mean_rank=4.0 if row.label else 1.0,
                    top_k_miss_rate=float(row.label),
                    entropy=2.0 if row.label else 0.3,
                    expected_event_ids=(row.event_ids[0],),
                )
                for row in sequences
            ]

    monkeypatch.setattr(
        cli_module.QwenAdapterScorer,
        "from_pretrained",
        lambda *args, **kwargs: FakeScorer(),
    )
    artifacts = tmp_path / "storage" / "artifacts"
    result = runner.invoke(
        app,
        [
            "calibrate",
            "--prepared",
            str(prepared),
            "--artifact-root",
            str(artifacts),
            "--version",
            "qwen-v1",
            "--adapter",
            str(adapter),
            "--storage-root",
            str(tmp_path / "storage"),
        ],
    )
    assert result.exit_code == 0, result.stdout
    metadata = json.loads(
        (artifacts / "hdfs" / "qwen-v1" / "metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["model_kind"] == "hybrid-transformer"
    assert (artifacts / "hdfs" / "qwen-v1" / "adapter").is_dir()
