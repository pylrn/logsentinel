from pathlib import Path

import pytest

from logsentinel.manifests import build_run_manifest, write_immutable_manifest
from logsentinel.schemas import DatasetName


def test_manifest_records_reproducibility_inputs_and_is_immutable(tmp_path: Path) -> None:
    source = tmp_path / "prepared.json"
    source.write_text('{"safe":"value"}', encoding="utf-8")
    manifest = build_run_manifest(
        dataset=DatasetName.HDFS,
        split_id="split-1",
        input_path=source,
        seed=42,
        artifacts={"model": "artifacts/hdfs/v1"},
    )
    assert manifest.input_checksum
    assert manifest.dependencies["logsentinel"] == "0.1.0"
    target = tmp_path / "manifest.json"
    write_immutable_manifest(manifest, target)
    with pytest.raises(FileExistsError):
        write_immutable_manifest(manifest, target)

