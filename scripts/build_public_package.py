"""Build an allowlisted, source-only LogSentinel release archive."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tarfile
from pathlib import Path

PUBLIC_TOP_LEVEL = {"src", "tests", "docs", "showcase", "scripts"}
PUBLIC_FILES = {
    "README.md",
    "MODEL_CARD.md",
    "DATASET_CARD.md",
    "SECURITY.md",
    "pyproject.toml",
    "uv.lock",
    "LICENSE",
}
DENIED_PARTS = {
    ".streamlit",
    ".logsentinel-storage",
    ".venv",
    "data",
    "artifacts",
    "dist",
    "build",
    "__pycache__",
}
DENIED_SUFFIXES = {".docx", ".pdf", ".safetensors", ".bin", ".pt", ".ckpt"}


def is_public_path(relative_path: str) -> bool:
    """Return whether a repository-relative path is eligible for the public archive."""
    path = Path(relative_path)
    top_level_allowed = bool(path.parts) and path.parts[0] in PUBLIC_TOP_LEVEL
    file_allowed = path.name in PUBLIC_FILES and len(path.parts) == 1
    return (
        (top_level_allowed or file_allowed)
        and not any(part in DENIED_PARTS for part in path.parts)
        and path.suffix.lower() not in DENIED_SUFFIXES
    )


def tracked_paths(root: Path) -> list[Path]:
    """List git-tracked paths eligible for publication, in a stable order."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [
        Path(item.decode())
        for item in result.stdout.split(b"\0")
        if item and is_public_path(item.decode()) and (root / item.decode()).is_file()
    ]


def build_archive(root: Path, output: Path) -> str:
    """Write an allowlisted gzip tar archive and return its SHA-256 checksum."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for relative_path in tracked_paths(root):
            archive.add(root / relative_path, arcname=f"logsentinel/{relative_path}")
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/logsentinel-public-source-0.1.0.tar.gz"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output if args.output.is_absolute() else root / args.output
    checksum = build_archive(root, output)
    print(f"Created {output}")
    print(f"SHA256 {checksum}")


if __name__ == "__main__":
    main()
