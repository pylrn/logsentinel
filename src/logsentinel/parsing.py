from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from logsentinel.privacy import Redactor, stable_hash


@dataclass(frozen=True)
class TemplateMatch:
    event_id: str
    template: str
    is_unknown: bool = False


class DeterministicTemplateMiner:
    """Small deterministic template vocabulary with a Drain3-compatible boundary.

    Dataset workflows can supply Drain3-mined templates to this class. Keeping the
    vocabulary layer independent makes freezing and artifact loading testable even
    when the optional Drain3 dependency is unavailable.
    """

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}
        self._frozen = False

    @property
    def vocabulary_size(self) -> int:
        return len(self._templates)

    def fit_transform(self, messages: list[str]) -> list[TemplateMatch]:
        return [self._fit(message) for message in messages]

    def _fit(self, template: str) -> TemplateMatch:
        if template not in self._templates:
            if self._frozen:
                return TemplateMatch("<UNK>", template, True)
            self._templates[template] = f"E_{stable_hash(template, salt='event', length=12)}"
        return TemplateMatch(self._templates[template], template)

    def transform(self, template: str) -> TemplateMatch:
        event_id = self._templates.get(template)
        if event_id is None:
            return TemplateMatch("<UNK>", template, True)
        return TemplateMatch(event_id, template)

    def freeze(self) -> None:
        self._frozen = True

    def to_dict(self) -> dict[str, str]:
        return dict(self._templates)

    @classmethod
    def from_dict(cls, templates: dict[str, str]) -> DeterministicTemplateMiner:
        miner = cls()
        miner._templates = dict(templates)
        miner.freeze()
        return miner


class DrainTemplateParser:
    """Privacy-safe adapter around Drain3's non-mutating match interface."""

    def __init__(self, *, backend: Any | None = None, redactor: Redactor | None = None) -> None:
        if backend is None:
            try:
                from drain3 import TemplateMiner
            except ImportError as exc:
                raise RuntimeError(
                    "Drain parsing requires the 'data' extra: pip install 'logsentinel[data]'"
                ) from exc
            backend = TemplateMiner()
        self.backend = backend
        self.redactor = redactor or Redactor()

    def fit(self, raw_message: str) -> TemplateMatch:
        normalized = self.redactor.redact(raw_message)
        result = self.backend.add_log_message(normalized)
        template = str(result["template_mined"])
        return TemplateMatch(_event_id(template), template)

    def transform(self, raw_message: str) -> TemplateMatch:
        normalized = self.redactor.redact(raw_message)
        cluster = self.backend.match(normalized, full_search_strategy="fallback")
        if cluster is None:
            return TemplateMatch("<UNK>", normalized, True)
        template = str(cluster.get_template())
        return TemplateMatch(_event_id(template), template)


def _event_id(template: str) -> str:
    return f"E_{stable_hash(template, salt='event', length=12)}"
