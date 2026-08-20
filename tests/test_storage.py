from __future__ import annotations

from pathlib import Path

import pytest

from logsentinel.storage import configure_local_storage, prefetch_huggingface_model


def test_configure_local_storage_keeps_downloads_under_selected_root(
    tmp_path: Path, monkeypatch
) -> None:
    for name in (
        "HF_HOME",
        "HF_HUB_CACHE",
        "HF_DATASETS_CACHE",
        "TRANSFORMERS_CACHE",
        "TORCH_HOME",
        "PIP_CACHE_DIR",
    ):
        monkeypatch.delenv(name, raising=False)

    layout = configure_local_storage(tmp_path / "external-ssd")

    assert layout.root == (tmp_path / "external-ssd").resolve()
    assert layout.adapters.is_dir()
    assert layout.artifacts.is_dir()
    assert layout.datasets.is_dir()
    assert Path(layout.environment["HF_HOME"]).is_relative_to(layout.root)
    assert Path(layout.environment["HF_HUB_CACHE"]).is_relative_to(layout.root)
    assert Path(layout.environment["HF_DATASETS_CACHE"]).is_relative_to(layout.root)
    assert Path(layout.environment["TRANSFORMERS_CACHE"]).is_relative_to(layout.root)
    assert Path(layout.environment["TORCH_HOME"]).is_relative_to(layout.root)
    assert Path(layout.environment["PIP_CACHE_DIR"]).is_relative_to(layout.root)


def test_configure_local_storage_overrides_cache_paths_outside_selected_root(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HF_HOME", "/tmp/unwanted-cache")

    layout = configure_local_storage(tmp_path / "ssd")

    assert Path(layout.environment["HF_HOME"]).is_relative_to(layout.root)


def test_prefetch_huggingface_model_passes_ssd_cache_to_downloader(
    tmp_path: Path,
) -> None:
    calls = {}

    def fake_download(**kwargs):
        calls.update(kwargs)
        target = Path(kwargs["cache_dir"]) / "models--Qwen--Qwen2.5-1.5B"
        target.mkdir(parents=True)
        return str(target)

    storage = tmp_path / "ssd"
    path = prefetch_huggingface_model(
        "Qwen/Qwen2.5-1.5B", storage, downloader=fake_download
    )

    assert calls["repo_id"] == "Qwen/Qwen2.5-1.5B"
    assert Path(calls["cache_dir"]).is_relative_to(storage)
    assert path.is_relative_to(storage)


def test_prefetch_rejects_corrupt_hub_weight_blob(tmp_path: Path) -> None:
    storage = tmp_path / "ssd"

    def corrupt_download(**kwargs):
        model_root = Path(kwargs["cache_dir"]) / "models--Qwen--demo"
        blob = model_root / "blobs" / ("a" * 64)
        blob.parent.mkdir(parents=True)
        blob.write_bytes(b"not-the-expected-content")
        snapshot = model_root / "snapshots" / "revision"
        snapshot.mkdir(parents=True)
        (snapshot / "model.safetensors").symlink_to(blob)
        return str(snapshot)

    with pytest.raises(RuntimeError, match="checksum"):
        prefetch_huggingface_model(
            "Qwen/demo", storage, downloader=corrupt_download
        )
