"""Write-side API for mirroring the ISN grammar spec into a Neo4j graph.

Phase E.3 of plan 29 ADR-8. This module is the *only* place where write
Cypher for grammar nodes lives. imas-codex's ``sync-isn-grammar`` CLI
(Phase E.6) injects its own :class:`GraphClient` into :func:`sync_grammar`.

Design rules:

* Pure Python. Do **not** import ``neo4j`` at module top-level — only inside
  ``TYPE_CHECKING`` or lazily. Callers supply any duck-typed object matching
  :class:`CypherClient`.
* Idempotent: repeated calls with the same ISN version are a no-op
  (``MERGE`` everywhere; ``version`` included in every key).
* Additive version bumps: a new ``ISNGrammarVersion`` node is created; old
  versioned nodes are left in place.
* ``dry_run=True`` executes **no** Cypher — neither reads nor writes. The
  returned report counts what *would* be written, with ``applied=False``.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from imas_standard_names import __version__ as _ISN_VERSION
from imas_standard_names.graph.spec import (
    GrammarGraphSpec,
    get_grammar_graph_spec,
)

if TYPE_CHECKING:  # pragma: no cover - type-only imports
    pass


__all__ = [
    "CypherClient",
    "SyncReport",
    "sync_grammar",
]


# ---------------------------------------------------------------------------
# Client Protocol (driver-agnostic)
# ---------------------------------------------------------------------------


@runtime_checkable
class CypherClient(Protocol):
    """Minimal duck-typed interface for a Cypher-executing client.

    imas-codex's ``GraphClient`` already matches this signature, so no
    adapter is needed on the consumer side. A bare ``neo4j.Driver`` does
    not match directly — wrap it in a thin adapter that forwards to
    ``session.run(cypher, **params)``.
    """

    def query(
        self, cypher: str, **params: Any
    ) -> Iterable[Any]:  # pragma: no cover - protocol only
        ...


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class SyncReport:
    """Outcome of a :func:`sync_grammar` call.

    For ``dry_run=True`` invocations the ``*_written`` counters reflect what
    *would* be written; ``applied`` is ``False`` and ``created_version`` is
    conservatively ``False`` (no read queries are issued in dry-run).
    """

    version: str
    applied: bool
    created_version: bool
    segments_written: int
    tokens_written: int
    templates_written: int
    next_edges_written: int
    defines_edges_written: int
    has_token_edges_written: int
    elapsed_seconds: float
    planned_statements: list[tuple[str, dict[str, Any]]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Cypher statement builders
# ---------------------------------------------------------------------------


_CONSTRAINT_STATEMENTS: tuple[str, ...] = (
    (
        "CREATE CONSTRAINT isn_grammar_version_unique IF NOT EXISTS "
        "FOR (v:ISNGrammarVersion) REQUIRE v.version IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT grammar_segment_name_version_unique IF NOT EXISTS "
        "FOR (s:GrammarSegment) REQUIRE (s.name, s.version) IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT grammar_token_value_segment_version_unique IF NOT EXISTS "
        "FOR (t:GrammarToken) REQUIRE (t.value, t.segment, t.version) IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT grammar_template_name_segment_version_unique IF NOT EXISTS "
        "FOR (tpl:GrammarTemplate) REQUIRE (tpl.name, tpl.segment, tpl.version) IS UNIQUE"
    ),
)


_MERGE_VERSION = (
    "MERGE (v:ISNGrammarVersion {version: $version}) "
    "ON CREATE SET v.created_at = datetime() "
    "RETURN v.version AS version"
)


_MERGE_SEGMENTS = (
    "UNWIND $rows AS row "
    "MATCH (v:ISNGrammarVersion {version: $version}) "
    "MERGE (s:GrammarSegment {name: row.name, version: $version}) "
    "SET s.position = row.position, s.required = row.required "
    "MERGE (v)-[:DEFINES]->(s)"
)


_MERGE_TOKENS = (
    "UNWIND $rows AS row "
    "MATCH (s:GrammarSegment {name: row.segment, version: $version}) "
    "MERGE (t:GrammarToken {value: row.value, segment: row.segment, version: $version}) "
    "SET t.aliases = row.aliases "
    "MERGE (s)-[:HAS_TOKEN]->(t)"
)


_MERGE_TEMPLATES = (
    "UNWIND $rows AS row "
    "MATCH (s:GrammarSegment {name: row.segment, version: $version}) "
    "MERGE (tpl:GrammarTemplate {"
    "name: row.name, segment: row.segment, version: $version"
    "}) "
    "SET tpl.pattern = row.pattern "
    "MERGE (s)-[:USES_TEMPLATE]->(tpl)"
)


_MERGE_NEXT = (
    "UNWIND $rows AS row "
    "MATCH (a:GrammarSegment {name: row.from_name, version: $version}) "
    "MATCH (b:GrammarSegment {name: row.to_name, version: $version}) "
    "MERGE (a)-[:NEXT]->(b)"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sync_grammar(
    client: CypherClient,
    *,
    active_version: str | None = None,
    dry_run: bool = False,
) -> SyncReport:
    """Mirror the grammar spec for ``active_version`` into the graph.

    Args:
        client: Any object with a ``query(cypher, **params)`` method
            (see :class:`CypherClient`).
        active_version: ISN version label for the spec. Defaults to the
            installed ``imas_standard_names.__version__``.
        dry_run: When ``True``, no Cypher is executed; the returned report
            lists the statements that *would* have been issued in
            ``planned_statements``.

    Returns:
        A :class:`SyncReport` summarising the operation.

    Notes:
        The writes batch into a small, fixed number of Cypher statements
        (constraints + 5 UNWIND MERGEs). If the underlying driver supports
        session-level transactions, callers may wrap this call in one; the
        :class:`CypherClient` Protocol only exposes per-statement ``query()``
        calls, so atomicity across statements is **not** guaranteed by this
        module.
    """
    version = active_version or _ISN_VERSION
    spec: GrammarGraphSpec = get_grammar_graph_spec()

    # Use the caller-supplied version, but reuse the spec's segment/token
    # data — the spec's own ``version`` field is informational only.
    segment_rows: list[dict[str, Any]] = [
        {
            "name": entry["name"],
            "position": entry["position"],
            "required": entry["required"],
        }
        for entry in spec["segments"]
    ]

    token_rows: list[dict[str, Any]] = [
        {
            "segment": segment["name"],
            "value": token["value"],
            "aliases": list(token["aliases"]),
        }
        for segment in spec["segments"]
        for token in segment["tokens"]
    ]

    template_rows: list[dict[str, Any]] = [
        {
            "name": entry["name"],
            "segment": entry["segment"],
            "pattern": entry["pattern"],
        }
        for entry in spec["templates"]
    ]

    segment_order = spec["segment_order"]
    next_rows: list[dict[str, Any]] = [
        {"from_name": a, "to_name": b}
        for a, b in zip(segment_order, segment_order[1:], strict=False)
    ]

    planned: list[tuple[str, dict[str, Any]]] = []
    for cypher in _CONSTRAINT_STATEMENTS:
        planned.append((cypher, {}))
    planned.append((_MERGE_VERSION, {"version": version}))
    planned.append((_MERGE_SEGMENTS, {"version": version, "rows": segment_rows}))
    planned.append((_MERGE_TOKENS, {"version": version, "rows": token_rows}))
    planned.append((_MERGE_TEMPLATES, {"version": version, "rows": template_rows}))
    planned.append((_MERGE_NEXT, {"version": version, "rows": next_rows}))

    start = time.perf_counter()

    if dry_run:
        return SyncReport(
            version=version,
            applied=False,
            created_version=False,
            segments_written=len(segment_rows),
            tokens_written=len(token_rows),
            templates_written=len(template_rows),
            next_edges_written=len(next_rows),
            defines_edges_written=len(segment_rows),
            has_token_edges_written=len(token_rows),
            elapsed_seconds=time.perf_counter() - start,
            planned_statements=planned,
        )

    # Pre-check whether the version node already exists so we can report
    # ``created_version`` truthfully. This is a single cheap read.
    existing = list(
        client.query(
            "MATCH (v:ISNGrammarVersion {version: $version}) RETURN count(v) AS n",
            version=version,
        )
    )
    created_version = _count_zero(existing)

    for cypher, params in planned:
        # Constraints and MERGEs are separate statements; atomicity is
        # per-statement unless the driver-specific client bundles them.
        client.query(cypher, **params)

    return SyncReport(
        version=version,
        applied=True,
        created_version=created_version,
        segments_written=len(segment_rows),
        tokens_written=len(token_rows),
        templates_written=len(template_rows),
        next_edges_written=len(next_rows),
        defines_edges_written=len(segment_rows),
        has_token_edges_written=len(token_rows),
        elapsed_seconds=time.perf_counter() - start,
        planned_statements=planned,
    )


def _count_zero(rows: list[Any]) -> bool:
    """Return ``True`` if the count query reported zero rows.

    Tolerates the various row shapes drivers return (dict, Record-like,
    tuple, or bare int).
    """
    if not rows:
        return True
    row = rows[0]
    if isinstance(row, dict):
        return int(row.get("n", 0)) == 0
    if hasattr(row, "get"):
        try:
            return int(row.get("n", 0)) == 0  # type: ignore[no-any-return]
        except Exception:
            pass
    if hasattr(row, "__getitem__"):
        try:
            return int(row[0]) == 0
        except Exception:
            pass
    try:
        return int(row) == 0
    except Exception:
        return False
