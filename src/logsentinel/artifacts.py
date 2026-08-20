from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import joblib
from pydantic import BaseModel, ConfigDict, Field, field_validator

from logsentinel.parsing import DeterministicTemplateMiner
from logsentinel.pipeline import HybridDetector
from logsentinel.schemas import DatasetName


class ArtifactIntegrityError(RuntimeError):
    pass


class ArtifactMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    environment: DatasetName
    version: str = Field(min_length=1, max_length=80)
    threshold: float = Field(ge=0)
    split_id: str = Field(min_length=1, max_length=128)
    model_kind: str = "hybrid-statistical"
    base_model: str = "Qwen/Qwen2.5-1.5B"
    adapter_version: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("version", "split_id")
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            raise ValueError("identifier contains unsafe path characters")
        return value


@dataclass(frozen=True)
class EnvironmentArtifact:
    metadata: ArtifactMetadata
    detector: HybridDetector
    parser: DeterministicTemplateMiner = field(default_factory=DeterministicTemplateMiner)
    adapter_path: Path | None = None


class ArtifactStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def save(self, artifact: EnvironmentArtifact) -> Path:
        transformer_mode = artifact.metadata.model_kind == "hybrid-transformer"
        if transformer_mode != artifact.detector.uses_transformer:
            raise ValueError("artifact metadata and detector mode do not match")
        if transformer_mode != (artifact.adapter_path is not None):
            raise ValueError("artifact metadata and adapter presence do not match")
        target = self._path(artifact.metadata.environment, artifact.metadata.version)
        if target.exists():
            raise FileExistsError(f"immutable artifact already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".building-", dir=target.parent))
        try:
            metadata_path = temporary / "metadata.json"
            model_path = temporary / "model.joblib"
            parser_path = temporary / "parser.json"
            metadata_path.write_text(
                artifact.metadata.model_dump_json(indent=2), encoding="utf-8"
            )
            joblib.dump(artifact.detector, model_path)
            parser_path.write_text(
                json.dumps(artifact.parser.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            if artifact.adapter_path is not None:
                adapter_source = Path(artifact.adapter_path)
                if not adapter_source.is_dir():
                    raise FileNotFoundError(f"adapter directory not found: {adapter_source}")
                shutil.copytree(adapter_source, temporary / "adapter")
            elif artifact.metadata.model_kind == "hybrid-transformer":
                raise ValueError("hybrid-transformer artifacts require an adapter directory")
            integrity = {
                str(path.relative_to(temporary)): _sha256(path)
                for path in sorted(temporary.rglob("*"))
                if path.is_file()
            }
            (temporary / "integrity.json").write_text(
                json.dumps(integrity, indent=2, sort_keys=True), encoding="utf-8"
            )
            os.replace(temporary, target)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return target

    def load(self, environment: DatasetName, version: str) -> EnvironmentArtifact:
        target = self._path(environment, version)
        if not target.is_dir():
            raise FileNotFoundError(f"artifact not found: {target}")
        integrity_path = target / "integrity.json"
        try:
            integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError("artifact integrity manifest is unreadable") from exc
        for filename in ("metadata.json", "model.joblib", "parser.json"):
            if filename not in integrity:
                raise ArtifactIntegrityError(f"checksum mismatch for {filename}")
        for filename, expected in integrity.items():
            relative = Path(filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ArtifactIntegrityError("artifact integrity manifest contains unsafe paths")
            path = target / relative
            if not expected or not path.is_file() or _sha256(path) != expected:
                raise ArtifactIntegrityError(f"checksum mismatch for {filename}")
        metadata = ArtifactMetadata.model_validate_json(
            (target / "metadata.json").read_text(encoding="utf-8")
        )
        if metadata.environment is not DatasetName(environment) or metadata.version != version:
            raise ArtifactIntegrityError("artifact identity does not match lookup path")
        try:
            detector = joblib.load(target / "model.joblib")
        except Exception as exc:
            raise ArtifactIntegrityError("trusted model artifact could not be loaded") from exc
        if not isinstance(detector, HybridDetector):
            raise ArtifactIntegrityError("artifact contains an unexpected model type")
        if (metadata.model_kind == "hybrid-transformer") != detector.uses_transformer:
            raise ArtifactIntegrityError("artifact metadata and detector mode do not match")
        try:
            parser_state = json.loads((target / "parser.json").read_text(encoding="utf-8"))
            parser = DeterministicTemplateMiner.from_dict(parser_state)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise ArtifactIntegrityError("parser artifact could not be loaded") from exc
        adapter_path = target / "adapter"
        if metadata.model_kind == "hybrid-transformer" and not adapter_path.is_dir():
            raise ArtifactIntegrityError("transformer artifact is missing its adapter")
        return EnvironmentArtifact(
            metadata=metadata,
            detector=detector,
            parser=parser,
            adapter_path=adapter_path if adapter_path.is_dir() else None,
        )

    def _path(self, environment: DatasetName, version: str) -> Path:
        safe = ArtifactMetadata.safe_identifier(version)
        return self.root / DatasetName(environment).value / safe


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
