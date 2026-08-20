from pathlib import Path


def test_declared_readme_exists_and_contains_runnable_quick_start() -> None:
    readme = Path("README.md")
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    assert "logsentinel run-all" in text
    assert "logsentinel serve" in text
    assert "logsentinel dashboard" in text

