"""Canonical grammar-graph specification for imas-codex consumption.

This module exports a pure-Python, deterministic representation of the ISN
grammar (segment order, tokens, templates) suitable for mirroring into an
external graph store. It is the sole boundary between ISN and imas-codex
for the LinkML schema and graph-sync workflow described in plan 29 ADR-8
(Phase E.2).

Design rules:
- Pure Python + existing dependencies only (no ``neo4j`` driver here; sync
  lives in a separate ``imas_standard_names.graph.sync`` module planned for
  Phase E.3 under an optional ``[graph]`` extra).
- Deterministic output: segments ordered by position in
  :data:`imas_standard_names.grammar.constants.SEGMENT_ORDER`; tokens sorted
  alphabetically to prevent set-iteration drift (Phase A fix rationale).
- One-way boundary: never import from ``imas_codex``.
- Token data is derived from :class:`GrammarSpec.load` (the same loader used
  by the grammar code generator) — do not re-parse YAML here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict

from imas_standard_names import __version__
from imas_standard_names.grammar.constants import SEGMENT_ORDER, SEGMENT_TEMPLATES
from imas_standard_names.grammar_codegen.spec import GrammarSpec

if TYPE_CHECKING:  # pragma: no cover - type-only imports
    from imas_standard_names.grammar.model import StandardName


__all__ = [
    "GrammarGraphSpec",
    "SegmentEdgeSpec",
    "SegmentSpecEntry",
    "TemplateSpecEntry",
    "TokenSpecEntry",
    "get_grammar_graph_spec",
    "segment_edge_specs",
]


# ---------------------------------------------------------------------------
# Spec shape (TypedDicts for structural documentation)
# ---------------------------------------------------------------------------


class TokenSpecEntry(TypedDict):
    value: str
    aliases: list[str]


class SegmentSpecEntry(TypedDict):
    name: str
    position: int
    required: bool
    tokens: list[TokenSpecEntry]


class TemplateSpecEntry(TypedDict):
    name: str
    segment: str
    pattern: str


class GrammarGraphSpec(TypedDict):
    version: str
    segment_order: list[str]
    segments: list[SegmentSpecEntry]
    templates: list[TemplateSpecEntry]


# ---------------------------------------------------------------------------
# Edge spec dataclass (per-name emission for HAS_SEGMENT MERGE)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SegmentEdgeSpec:
    """A single grammar-segment edge to be materialised in the graph.

    Consumed by the imas-codex ``persist_worker`` to MERGE
    ``(sn:StandardName)-[:HAS_SEGMENT {position, segment}]->(t:GrammarToken)``.

    Attributes:
        position: 0-based index in :data:`SEGMENT_ORDER` — not the position
            within the composed name. Use this to ORDER BY when reconstructing
            the name from graph data.
        segment: Segment identifier (e.g. ``"substance"``, ``"physical_base"``).
            Always drawn from :data:`SEGMENT_ORDER`.
        token: Resolved token value (e.g. ``"electron"``, ``"temperature"``).
        template: Template name if a grammar template produced this segment's
            surface form (e.g. ``"at_{token}"``), else ``None``.
    """

    position: int
    segment: str
    token: str
    template: str | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_grammar_graph_spec() -> GrammarGraphSpec:
    """Return the canonical grammar-graph spec.

    Output is deterministic: segments follow :data:`SEGMENT_ORDER`; tokens
    within each segment are sorted alphabetically. Re-running this function
    on the same grammar always yields an equal dict (safe for equality-based
    CI drift gates).
    """
    grammar = GrammarSpec.load()
    segment_map = grammar.segment_map

    segments: list[SegmentSpecEntry] = []
    templates: list[TemplateSpecEntry] = []

    for position, segment_name in enumerate(SEGMENT_ORDER):
        segment = segment_map.get(segment_name)
        # Required == NOT optional. SEGMENT_RULES currently marks all segments
        # optional at the individual-segment level; the base requirement is
        # a cross-segment invariant (geometric_base OR physical_base). Report
        # the per-segment flag truthfully here.
        required = not segment.optional if segment is not None else False
        raw_tokens = grammar.tokens_for_segment(segment_name)
        tokens_sorted = sorted(set(raw_tokens))
        tokens: list[TokenSpecEntry] = [
            {"value": token, "aliases": []} for token in tokens_sorted
        ]
        segments.append(
            {
                "name": segment_name,
                "position": position,
                "required": required,
                "tokens": tokens,
            }
        )

        template_pattern = SEGMENT_TEMPLATES.get(segment_name)
        if template_pattern is not None:
            templates.append(
                {
                    "name": f"{segment_name}_template",
                    "segment": segment_name,
                    "pattern": template_pattern,
                }
            )

    templates.sort(key=lambda entry: entry["name"])

    spec: GrammarGraphSpec = {
        "version": __version__,
        "segment_order": list(SEGMENT_ORDER),
        "segments": segments,
        "templates": templates,
    }
    return spec


def segment_edge_specs(parsed: StandardName) -> list[SegmentEdgeSpec]:
    """Emit one :class:`SegmentEdgeSpec` per set segment in ``parsed``.

    Walks :data:`SEGMENT_ORDER` and produces an edge for each segment whose
    attribute on ``parsed`` is non-``None``. The resulting list is ordered
    by the canonical segment position, so consumers can rely on monotonic
    ``position`` values.

    Args:
        parsed: Result of :func:`imas_standard_names.grammar.parse_standard_name`.

    Returns:
        Edges in segment-order. May be shorter than ``len(SEGMENT_ORDER)``
        because most segments are optional.
    """
    edges: list[SegmentEdgeSpec] = []
    for position, segment_name in enumerate(SEGMENT_ORDER):
        value: Any = getattr(parsed, segment_name, None)
        if value is None:
            continue
        token = value.value if hasattr(value, "value") else str(value)
        edges.append(
            SegmentEdgeSpec(
                position=position,
                segment=segment_name,
                token=token,
                template=SEGMENT_TEMPLATES.get(segment_name),
            )
        )
    return edges
