"""CI drift gate for the pure-Python grammar-graph spec API.

Covers plan 29 Phase E.2 contract:

* Spec ↔ YAML sanity — each segment's token list matches ``GrammarSpec.load``
  (the same loader used by grammar codegen). This catches accidental drift
  between the in-repo YAML vocabularies and the graph-spec export.
* Determinism — repeated calls return equal dicts, including list order.
* Version correctness — spec's ``version`` matches the package version.
* Edge spec round-trip — parsing a known standard name and emitting edges
  produces monotonic positions with segments drawn from ``SEGMENT_ORDER``.
"""

from __future__ import annotations

import imas_standard_names
from imas_standard_names.grammar import parse_standard_name
from imas_standard_names.grammar.constants import SEGMENT_ORDER
from imas_standard_names.grammar_codegen.spec import GrammarSpec
from imas_standard_names.graph import (
    SegmentEdgeSpec,
    get_grammar_graph_spec,
    segment_edge_specs,
)


def test_spec_tokens_match_yaml_loader() -> None:
    """Each segment's tokens must match the canonical YAML loader output.

    This is the critical drift gate: if the grammar YAML or vocabulary files
    change, the graph spec must re-export consistently.
    """
    spec = get_grammar_graph_spec()
    grammar = GrammarSpec.load()

    spec_by_name = {entry["name"]: entry for entry in spec["segments"]}
    assert set(spec_by_name) == set(SEGMENT_ORDER)

    for segment_name in SEGMENT_ORDER:
        entry = spec_by_name[segment_name]
        spec_tokens = [token["value"] for token in entry["tokens"]]
        expected = sorted(set(grammar.tokens_for_segment(segment_name)))
        assert spec_tokens == expected, (
            f"Token drift for segment '{segment_name}': "
            f"spec={spec_tokens} expected={expected}"
        )


def test_spec_is_deterministic() -> None:
    """Repeated calls must return equal dicts including all list orderings."""
    first = get_grammar_graph_spec()
    second = get_grammar_graph_spec()
    assert first == second

    # Segment order follows SEGMENT_ORDER exactly
    assert [s["name"] for s in first["segments"]] == list(SEGMENT_ORDER)
    assert first["segment_order"] == list(SEGMENT_ORDER)

    # Tokens within each segment are alphabetically sorted
    for entry in first["segments"]:
        values = [token["value"] for token in entry["tokens"]]
        assert values == sorted(values), (
            f"Segment '{entry['name']}' tokens not alphabetically sorted: {values}"
        )

    # Templates are sorted by name
    template_names = [t["name"] for t in first["templates"]]
    assert template_names == sorted(template_names)


def test_spec_version_matches_package() -> None:
    spec = get_grammar_graph_spec()
    assert spec["version"] == imas_standard_names.__version__


def test_spec_segment_positions_are_sequential() -> None:
    spec = get_grammar_graph_spec()
    positions = [entry["position"] for entry in spec["segments"]]
    assert positions == list(range(len(SEGMENT_ORDER)))


def test_segment_edge_specs_round_trip() -> None:
    """Parse a known name and verify emitted edges satisfy the contract."""
    parsed = parse_standard_name("electron_temperature")
    edges = segment_edge_specs(parsed)

    assert edges, "expected at least one edge for electron_temperature"

    # Every edge must be a SegmentEdgeSpec with segment ∈ SEGMENT_ORDER
    for edge in edges:
        assert isinstance(edge, SegmentEdgeSpec)
        assert edge.segment in SEGMENT_ORDER
        assert isinstance(edge.token, str) and edge.token
        assert edge.position == SEGMENT_ORDER.index(edge.segment)

    # Positions are strictly monotonic in segment-order
    positions = [edge.position for edge in edges]
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)

    # Content sanity for this specific name
    by_segment = {edge.segment: edge for edge in edges}
    assert by_segment["subject"].token == "electron"
    assert by_segment["physical_base"].token == "temperature"


def test_segment_edge_specs_template_attached_when_applicable() -> None:
    """Segments with compose templates propagate the pattern to edges."""
    parsed = parse_standard_name("electron_temperature_at_magnetic_axis")
    edges = segment_edge_specs(parsed)
    by_segment = {edge.segment: edge for edge in edges}

    position_edge = by_segment.get("position")
    assert position_edge is not None
    assert position_edge.template == "at_{token}"

    # Segments without templates (e.g. subject) report None
    assert by_segment["subject"].template is None
