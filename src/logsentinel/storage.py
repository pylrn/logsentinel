from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / ".logsentinel-storage"


@dataclass(frozen=True)
class StorageLayout:
    root: Path
    adapters: Path
    artifacts: Path
    datasets: Path
    environment: dict[str, str]


def configure_local_storage(root: Path | str | None = None) -> StorageLayout:
    """Route all download/cache locations into one explicitly selected directory."""
    selected = Path(
        root or os.environ.get("LOGSENTINEL_STORAGE_ROOT", DEFAULT_STORAGE_ROOT)
    ).expanduser().resolve()
    cache = selected / "cache"
    paths = {
        "HF_HOME": cache / "huggingface",
        "HF_HUB_CACHE": cache / "huggingface" / "hub",
        "HF_DATASETS_CACHE": cache / "huggingface" / "datasets",
        "TRANSFORMERS_CACHE": cache / "huggingface" / "transformers",
        "TORCH_HOME": cache / "torch",
        "PIP_CACHE_DIR": cache / "pip",
    }
    adapters = selected / "adapters"
    artifacts = selected / "artifacts"
    datasets = selected / "datasets"
    for path in (*paths.values(), adapters, artifacts, datasets):
        path.mkdir(parents=True, exist_ok=True)
    environment = {name: str(path) for name, path in paths.items()}
    environment["LOGSENTINEL_STORAGE_ROOT"] = str(selected)
    os.environ.update(environment)
    return StorageLayout(
        root=selected,
        adapters=adapters,
        artifacts=artifacts,
        datasets=datasets,
        environment=environment,
    )


def prefetch_huggingface_model(
    model_id: str,
    root: Path | str | None = None,
    *,
    downloader: Callable[..., Any] | None = None,
) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", model_id):
        raise ValueError("model_id must be a Hugging Face repository identifier")
    layout = configure_local_storage(root)
    if downloader is None:
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise RuntimeError(
                "model download requires huggingface-hub or the LogSentinel ML extra"
            ) from exc
        downloader = snapshot_download
    downloaded = downloader(
        repo_id=model_id,
        repo_type="model",
        cache_dir=layout.environment["HF_HUB_CACHE"],
    )
    path = Path(downloaded).resolve()
    if not path.is_relative_to(layout.root):
        raise RuntimeError("model downloader returned a path outside configured storage")
    for weight in path.glob("*.safetensors"):
        blob = weight.resolve()
        if not blob.is_relative_to(layout.root):
            raise RuntimeError("model snapshot references weights outside configured storage")
        if re.fullmatch(r"[0-9a-f]{64}", blob.name) and _sha256(blob) != blob.name:
            raise RuntimeError(f"model weight checksum mismatch: {weight.name}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
