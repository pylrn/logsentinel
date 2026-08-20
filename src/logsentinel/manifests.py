from __future__ import annotations

import hashlib
import platform
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from logsentinel.schemas import DatasetName


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset: DatasetName
    split_id: str
    input_checksum: str
    seed: int
    dependencies: dict[str, str]
    artifacts: dict[str, str]
    python_version: str
    platform: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def build_run_manifest(
    *,
    dataset: DatasetName,
    split_id: str,
    input_path: Path | str,
    seed: int,
    artifacts: dict[str, str],
) -> RunManifest:
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    packages = (
        "logsentinel",
        "numpy",
        "scikit-learn",
        "torch",
        "transformers",
        "datasets",
        "peft",
        "drain3",
        "fastapi",
        "streamlit",
    )
    versions = {}
    for package in packages:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return RunManifest(
        dataset=dataset,
        split_id=split_id,
        input_checksum=_sha256(path),
        seed=seed,
        dependencies=versions,
        artifacts=artifacts,
        python_version=platform.python_version(),
        platform=platform.platform(),
    )


def write_immutable_manifest(manifest: RunManifest, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(manifest.model_dump_json(indent=2))
            handle.write("\n")
    except FileExistsError:
        raise FileExistsError(f"immutable run manifest already exists: {target}") from None
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

