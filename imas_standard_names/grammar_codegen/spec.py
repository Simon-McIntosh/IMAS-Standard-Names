"""Load and normalize the canonical standard-name grammar specification.

This module lives in a neutral location (outside the ``grammar`` package)
to ensure code generation can run without importing any code that depends
on the generated ``grammar/types.py``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml

_GRAMMAR_PACKAGE = "imas_standard_names.grammar"
_GRAMMAR_FILENAME = "specification.yml"


class IncludeLoader(yaml.SafeLoader):
    """YAML loader that supports !include directive for external vocabulary files."""

    def __init__(self, stream):
        self._root = None
        if hasattr(stream, "name"):
            from pathlib import Path

            self._root = Path(stream.name).parent
        super().__init__(stream)


def include_constructor(loader: IncludeLoader, node):
    """Load vocabulary from external file."""
    filename = loader.construct_scalar(node)
    if loader._root:
        filepath = loader._root / filename
        with open(filepath, encoding="utf-8") as f:
            return yaml.safe_load(f)
    # Fallback to importlib.resources for packaged installations
    from importlib import resources

    vocab_path = resources.files(_GRAMMAR_PACKAGE) / filename
    with vocab_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


IncludeLoader.add_constructor("!include", include_constructor)


@dataclass(frozen=True)
class SegmentSpec:
    identifier: str
    optional: bool
    template: str | None
    vocabulary_name: str | None
    vocabulary_reference: tuple[str, str] | None
    exclusive_with: tuple[str, ...]


@dataclass(frozen=True)
class BasisGroup:
    description: str
    components: tuple[str, ...]


@dataclass(frozen=True)
class ScopeSpec:
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class GrammarSpec:
    segments: tuple[SegmentSpec, ...]
    vocabularies: dict[str, tuple[str, ...]]
    basis: dict[str, BasisGroup]
    scope: ScopeSpec | None = None

    @property
    def segment_map(self) -> dict[str, SegmentSpec]:
        return {segment.identifier: segment for segment in self.segments}

    def tokens_for_segment(self, segment_id: str) -> tuple[str, ...]:
        segment = self.segment_map[segment_id]
        if segment.vocabulary_name:
            return self.vocabularies.get(segment.vocabulary_name, ())
        if segment.vocabulary_reference:
            source, field = segment.vocabulary_reference
            if source == "basis" and field == "components":
                return _flatten_unique(
                    component
                    for group in self.basis.values()
                    for component in group.components
                )
        return ()

    def vocabulary_tokens(self, name: str) -> tuple[str, ...]:
        return self.vocabularies.get(name, ())

    @classmethod
    def load(cls) -> GrammarSpec:
        grammar_path = resources.files(_GRAMMAR_PACKAGE) / _GRAMMAR_FILENAME
        with grammar_path.open("r", encoding="utf-8") as handle:
            data = yaml.load(handle, Loader=IncludeLoader) or {}

        basis_raw = data.get("basis", {})
        vocab_raw = data.get("vocabularies", {})
        segments_raw = data.get("segments", [])
        scope_raw = data.get("scope", {})

        vocabularies = {
            name: _flatten_unique(tokens) for name, tokens in vocab_raw.items()
        }

        # Parse scope section
        scope: ScopeSpec | None = None
        if scope_raw:
            scope = ScopeSpec(
                include=_flatten_unique(scope_raw.get("include", ())),
                exclude=_flatten_unique(scope_raw.get("exclude", ())),
                rationale=str(scope_raw.get("rationale", "")),
            )

        basis: dict[str, BasisGroup] = {}
        if isinstance(basis_raw, Mapping):
            for name, payload in basis_raw.items():
                description = (
                    str(payload.get("description", ""))
                    if isinstance(payload, Mapping)
                    else ""
                )
                components_raw: Sequence[str] = ()
                if isinstance(payload, Mapping):
                    components_raw = payload.get("components", ())
                basis[name] = BasisGroup(
                    description=description,
                    components=_flatten_unique(components_raw),
                )

        segments: list[SegmentSpec] = []
        if isinstance(segments_raw, Sequence):
            for entry in segments_raw:
                if not isinstance(entry, Mapping):
                    continue
                identifier = str(entry.get("id", "")).strip()
                if not identifier:
                    raise ValueError("Each segment must declare an 'id'")
                optional = bool(entry.get("optional", False))
                template = entry.get("template")
                template_str = str(template) if isinstance(template, str) else None
                vocab_field = entry.get("vocabulary")
                vocab_name: str | None = None
                vocab_reference: tuple[str, str] | None = None
                if isinstance(vocab_field, str):
                    vocab_name = vocab_field
                    if vocab_name not in vocabularies:
                        raise KeyError(
                            f"Vocabulary '{vocab_name}' referenced by segment '{identifier}' is undefined"
                        )
                elif isinstance(vocab_field, Mapping):
                    source = str(vocab_field.get("source", "")).strip()
                    field = str(vocab_field.get("field", "")).strip()
                    if not source or not field:
                        raise ValueError(
                            f"Segment '{identifier}' declares an invalid vocabulary reference"
                        )
                    vocab_reference = (source, field)
                    if (
                        source == "basis"
                        and field == "components"
                        and "components" in vocabularies
                    ):
                        vocab_name = "components"
                exclusive_with_raw = entry.get("exclusive_with", ())
                exclusive_with = tuple(
                    str(item) for item in _as_iterable(exclusive_with_raw)
                )
                segments.append(
                    SegmentSpec(
                        identifier=identifier,
                        optional=optional,
                        template=template_str,
                        vocabulary_name=vocab_name,
                        vocabulary_reference=vocab_reference,
                        exclusive_with=exclusive_with,
                    )
                )

        return cls(
            segments=tuple(segments),
            vocabularies=vocabularies,
            basis=basis,
            scope=scope,
        )


def _flatten_unique(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return tuple(result)


def _as_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return value
    if value is None:
        return ()
    return (value,)


__all__ = ["GrammarSpec", "SegmentSpec", "BasisGroup", "ScopeSpec"]
