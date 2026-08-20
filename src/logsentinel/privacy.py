from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


def stable_hash(value: str | None, *, salt: str = "logsentinel-v1", length: int = 20) -> str:
    payload = f"{salt}\0{value or ''}".encode()
    return hashlib.sha256(payload).hexdigest()[:length]


@dataclass(frozen=True)
class Redactor:
    patterns: tuple[tuple[re.Pattern[str], str], ...] = field(
        default_factory=lambda: (
            (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<EMAIL>"),
            (
                re.compile(
                    r"(?i)\b(?:token|api[_-]?key|password|secret)\s*[=:]\s*[^\s,;]+"
                ),
                "<TOKEN>",
            ),
            (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b"), "<IP>"),
            (re.compile(r"\bblk_-?\d+\b", re.IGNORECASE), "<BLOCK_ID>"),
            (
                re.compile(
                    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
                    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
                ),
                "<UUID>",
            ),
            (re.compile(r"(?<!\w)/(?:[^\s/]+/)*[^\s/]+"), "<PATH>"),
            (re.compile(r"\b\d{7,}\b"), "<LONG_NUMBER>"),
        )
    )

    def redact(self, message: str) -> str:
        value = message
        for pattern, replacement in self.patterns:
            value = pattern.sub(replacement, value)
        return " ".join(value.split())

