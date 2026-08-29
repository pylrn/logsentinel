from __future__ import annotations

from pathlib import Path

SHOWCASE = Path("showcase")


def test_showcase_has_required_evidence_sections() -> None:
    page = (SHOWCASE / "index.html").read_text()
    for marker in (
        "How it works",
        "Sample replay",
        "Evidence &amp; limits",
        "Onboard an environment",
        "Run it yourself",
    ):
        assert marker in page
    assert 'id="replay"' in page


def test_showcase_never_claims_hosted_inference() -> None:
    content = "\n".join(
        path.read_text()
        for path in SHOWCASE.rglob("*.*")
        if path.suffix in {".html", ".css", ".js"}
    )
    assert "live model" not in content.lower()
    assert "zero-day" not in content.lower()


def test_replay_uses_redacted_deterministic_fixtures() -> None:
    fixture = (SHOWCASE / "assets" / "replay-data.js").read_text()
    assert "<IP>" in fixture
    assert "<USER_ID>" in fixture
    assert "illustrative" in fixture.lower()
    assert "198.51.100.42" not in fixture


def test_replay_has_no_external_api_call() -> None:
    app = (SHOWCASE / "assets" / "app.js").read_text()
    assert "fetch(" not in app
