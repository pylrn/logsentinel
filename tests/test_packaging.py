import json
from pathlib import Path


def test_declared_readme_exists_and_contains_runnable_quick_start() -> None:
    readme = Path("README.md")
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    assert "logsentinel run-all" in text
    assert "logsentinel serve" in text
    assert "logsentinel dashboard" in text
    assert "Static public showcase" in text
    assert "local Streamlit research lab" in text
    assert "illustrative replay" in text.lower()


def test_handoff_documents_and_colab_notebook_have_no_placeholders() -> None:
    paths = [
        Path("MODEL_CARD.md"),
        Path("DATASET_CARD.md"),
        Path("SECURITY.md"),
        Path("docs/design/dashboard-fidelity-ledger.md"),
        Path("notebooks/logsentinel_colab.ipynb"),
        Path(".github/workflows/ci.yml"),
    ]
    assert all(path.is_file() for path in paths)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert not any(marker in combined for marker in ("TODO", "TBD", "YOUR_", "<fill"))
    notebook = json.loads(Path("notebooks/logsentinel_colab.ipynb").read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert any("train-transformer" in "".join(cell.get("source", [])) for cell in notebook["cells"])
