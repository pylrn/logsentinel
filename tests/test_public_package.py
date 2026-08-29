from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "build_public_package.py"
_SPEC = importlib.util.spec_from_file_location("build_public_package", _SCRIPT_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
is_public_path = _MODULE.is_public_path


def test_public_package_excludes_secrets_data_and_weights() -> None:
    assert not is_public_path(".streamlit/secrets.toml")
    assert not is_public_path(".logsentinel-storage/models/qwen/model.safetensors")
    assert not is_public_path("data/raw/hdfs.log")
    assert not is_public_path("Compiler_Design_Assessment.docx")


def test_public_package_keeps_source_docs_and_redacted_fixtures() -> None:
    assert is_public_path("src/logsentinel/api.py")
    assert is_public_path("README.md")
    assert is_public_path("showcase/assets/replay-data.js")
