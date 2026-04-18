"""Grammar-graph spec and sync primitives.

Phase E.2 (plan 29 ADR-8) adds :mod:`.spec` — a pure-Python, deterministic
export of the ISN grammar for imas-codex to mirror into Neo4j. Phase E.3
will add a ``.sync`` module gated on the ``[graph]`` extra.
"""

from .spec import (
    GrammarGraphSpec,
    SegmentEdgeSpec,
    SegmentSpecEntry,
    TemplateSpecEntry,
    TokenSpecEntry,
    get_grammar_graph_spec,
    segment_edge_specs,
)

__all__ = [
    "GrammarGraphSpec",
    "SegmentEdgeSpec",
    "SegmentSpecEntry",
    "TemplateSpecEntry",
    "TokenSpecEntry",
    "get_grammar_graph_spec",
    "segment_edge_specs",
]
