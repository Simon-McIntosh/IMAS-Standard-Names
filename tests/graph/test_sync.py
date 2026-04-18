"""Tests for :mod:`imas_standard_names.graph.sync` (plan 29 Phase E.3).

All tests are purely mock-based — no live Neo4j. Integration tests with a
real database live in imas-codex (Phase E.8).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from imas_standard_names.graph import (
    CypherClient,
    SyncReport,
    get_grammar_graph_spec,
    sync_grammar,
)


class RecordingClient:
    """Minimal mock that records every ``query()`` call.

    Returns a canned row for the version-existence pre-check so the
    "applied" path can run end-to-end without touching a database.
    """

    def __init__(self, existing_version: bool = False) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._existing = 1 if existing_version else 0

    def query(self, cypher: str, **params: Any) -> Iterable[Any]:
        self.calls.append((cypher, dict(params)))
        if "count(v) AS n" in cypher:
            return [{"n": self._existing}]
        return []


def test_dry_run_report_shape_matches_spec() -> None:
    """Report counters must mirror the spec's own dimensions."""
    client = RecordingClient()
    spec = get_grammar_graph_spec()
    expected_segments = len(spec["segments"])
    expected_tokens = sum(len(s["tokens"]) for s in spec["segments"])
    expected_templates = len(spec["templates"])
    expected_next = max(0, len(spec["segment_order"]) - 1)

    report = sync_grammar(client, dry_run=True)

    assert isinstance(report, SyncReport)
    assert report.applied is False
    assert report.created_version is False
    assert report.version == spec["version"]
    assert report.segments_written == expected_segments
    assert report.tokens_written == expected_tokens
    assert report.templates_written == expected_templates
    assert report.next_edges_written == expected_next
    assert report.defines_edges_written == expected_segments
    assert report.has_token_edges_written == expected_tokens
    # dry_run issues zero Cypher
    assert client.calls == []
    # planned_statements should be non-empty and include constraints + MERGEs
    assert len(report.planned_statements) >= 6
    assert any("CREATE CONSTRAINT" in s for s, _ in report.planned_statements)
    assert any("ISNGrammarVersion" in s for s, _ in report.planned_statements)


def test_dry_run_is_idempotent_across_calls() -> None:
    """Two dry runs produce identical planned Cypher."""
    client_a = RecordingClient()
    client_b = RecordingClient()

    report_a = sync_grammar(client_a, dry_run=True)
    report_b = sync_grammar(client_b, dry_run=True)

    statements_a = [s for s, _ in report_a.planned_statements]
    statements_b = [s for s, _ in report_b.planned_statements]
    assert statements_a == statements_b

    params_a = [p for _, p in report_a.planned_statements]
    params_b = [p for _, p in report_b.planned_statements]
    assert params_a == params_b


def test_every_merge_includes_version_in_key_map() -> None:
    """Grammar-node MERGEs must key on ``version`` so versions coexist."""
    client = RecordingClient()
    report = sync_grammar(client, dry_run=True)

    merges = [
        cypher
        for cypher, _ in report.planned_statements
        if cypher.lstrip().startswith("MERGE")
        or (" MERGE (" in cypher and "UNWIND" in cypher)
        or "MERGE (v:ISNGrammarVersion" in cypher
    ]
    assert merges, "expected at least one MERGE statement in the plan"

    for cypher in merges:
        # Every MERGE we issue targets a grammar node; version must appear
        # either as a literal key in the MERGE map or bound via $version.
        assert "version" in cypher, f"no version key in MERGE: {cypher!r}"
        assert (
            "{version: $version" in cypher
            or "version: $version" in cypher
            or "version: row" in cypher  # composite keys via UNWIND rows
        ), f"MERGE does not key on version: {cypher!r}"


def test_cypher_client_protocol_is_runtime_checkable() -> None:
    """``CypherClient`` must be usable with ``isinstance``."""
    # Declared explicitly — this is the public contract.
    from typing import Protocol, runtime_checkable

    assert isinstance(CypherClient, type(Protocol))  # Protocol metaclass
    _ = runtime_checkable  # silence unused import in minor refactors

    class MinimalClient:
        def query(self, cypher: str, **params: Any) -> Iterable[Any]:
            return []

    assert isinstance(MinimalClient(), CypherClient)


def test_applied_path_executes_planned_statements_in_order() -> None:
    """With ``dry_run=False`` the mock records exactly the planned calls."""
    client = RecordingClient(existing_version=False)
    report = sync_grammar(client, dry_run=False)

    assert report.applied is True
    # First call is the version pre-check; remainder mirror the plan.
    assert client.calls[0][0].startswith("MATCH (v:ISNGrammarVersion")
    executed = [c for c, _ in client.calls[1:]]
    planned = [c for c, _ in report.planned_statements]
    assert executed == planned
    # Version didn't exist before → created_version is True.
    assert report.created_version is True


def test_applied_path_detects_existing_version() -> None:
    client = RecordingClient(existing_version=True)
    report = sync_grammar(client, dry_run=False)
    assert report.applied is True
    assert report.created_version is False


def test_custom_active_version_flows_into_params() -> None:
    client = RecordingClient()
    report = sync_grammar(client, active_version="0.0.0-test", dry_run=True)
    assert report.version == "0.0.0-test"
    for _, params in report.planned_statements:
        if "version" in params:
            assert params["version"] == "0.0.0-test"


def test_bad_client_fails_protocol_check() -> None:
    class NoQuery:
        pass

    assert not isinstance(NoQuery(), CypherClient)

    # A runtime call must still work if the user supplies a conformant
    # client; this is implicitly tested elsewhere. Here we just assert the
    # negative case to guard against accidental Protocol weakening.
    with pytest.raises(AttributeError):
        sync_grammar(NoQuery(), dry_run=False)  # type: ignore[arg-type]
