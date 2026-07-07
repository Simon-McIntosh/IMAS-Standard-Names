"""Grammar-graph spec and sync primitives.

:mod:`.spec` provides a pure-Python, deterministic
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
from .sync import CypherClient, SyncReport, sync_grammar

__all__ = [
    "CypherClient",
    "GrammarGraphSpec",
    "SegmentEdgeSpec",
    "SegmentSpecEntry",
    "SyncReport",
    "TemplateSpecEntry",
    "TokenSpecEntry",
    "get_grammar_graph_spec",
    "segment_edge_specs",
    "sync_grammar",
]
