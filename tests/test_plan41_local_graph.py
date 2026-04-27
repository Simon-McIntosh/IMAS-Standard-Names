"""Tests for plan 41: local NetworkX graph + MCP tools + renderer upgrades."""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
nx = pytest.importorskip("networkx")

from imas_standard_names.graph.local_graph import (  # noqa: E402
    ALL_EDGE_TYPES,
    build_catalog_graph,
    get_ancestors,
    get_descendants,
    get_neighbours,
    shortest_path,
)
from imas_standard_names.rendering.catalog import CatalogRenderer  # noqa: E402

# ---------------------------------------------------------------------------
# Fixture catalog (plan 41 §6 — covers all edge types + stub)
# ---------------------------------------------------------------------------
_DOMAIN_FIXTURE = [
    # Simple base for components to wrap.
    {
        "name": "magnetic_field",
        "kind": "scalar",
        "unit": "T",
        "description": "Magnetic flux density.",
        "status": "draft",
    },
    # Unary-prefix argument (component axis=x).
    {
        "name": "x_component_of_magnetic_field",
        "kind": "scalar",
        "unit": "T",
        "description": "X component.",
        "status": "draft",
        "arguments": [
            {
                "name": "magnetic_field",
                "operator": "component",
                "operator_kind": "unary",
                "axis": "x",
            }
        ],
    },
    # Binary arguments (role=a, role=b).
    {
        "name": "pressure",
        "kind": "scalar",
        "unit": "Pa",
        "description": "Thermodynamic pressure.",
        "status": "draft",
    },
    {
        "name": "density",
        "kind": "scalar",
        "unit": "kg/m^3",
        "description": "Mass density.",
        "status": "draft",
    },
    {
        "name": "ratio_of_pressure_to_density",
        "kind": "scalar",
        "unit": "Pa*m^3/kg",
        "description": "Pressure-to-density ratio.",
        "status": "draft",
        "arguments": [
            {
                "name": "pressure",
                "operator": "ratio",
                "operator_kind": "binary",
                "role": "a",
            },
            {
                "name": "density",
                "operator": "ratio",
                "operator_kind": "binary",
                "role": "b",
            },
        ],
    },
    # Base with error_variants (error_variants emitted base→variant).
    {
        "name": "temperature",
        "kind": "scalar",
        "unit": "K",
        "description": "Temperature.",
        "status": "draft",
        "error_variants": {
            "upper": "upper_uncertainty_of_temperature",
            "lower": "lower_uncertainty_of_temperature",
            "index": "uncertainty_index_of_temperature",
        },
    },
    {
        "name": "upper_uncertainty_of_temperature",
        "kind": "scalar",
        "unit": "K",
        "description": "Upper uncertainty bound.",
        "status": "draft",
    },
    {
        "name": "lower_uncertainty_of_temperature",
        "kind": "scalar",
        "unit": "K",
        "description": "Lower uncertainty bound.",
        "status": "draft",
    },
    {
        "name": "uncertainty_index_of_temperature",
        "kind": "metadata",
        "description": "Uncertainty representation index.",
        "status": "draft",
    },
    # Deprecation chain.
    {
        "name": "old_name",
        "kind": "scalar",
        "unit": "1",
        "description": "Legacy name.",
        "status": "deprecated",
        "superseded_by": "new_name",
    },
    {
        "name": "new_name",
        "kind": "scalar",
        "unit": "1",
        "description": "Modern replacement.",
        "status": "draft",
        "deprecates": "old_name",
    },
    # Entry with links + cocos_transformation_type.
    {
        "name": "poloidal_magnetic_flux",
        "kind": "scalar",
        "unit": "Wb",
        "description": "Poloidal flux.",
        "status": "draft",
        "cocos_transformation_type": "psi_like",
        "links": ["name:magnetic_field", "https://example.org/cocos"],
    },
    # Entry with a stub forward reference.
    {
        "name": "wraps_something_missing",
        "kind": "scalar",
        "unit": "1",
        "description": "Wraps an absent base.",
        "status": "draft",
        "arguments": [
            {
                "name": "missing_base",
                "operator": "component",
                "operator_kind": "unary",
                "axis": "z",
            }
        ],
    },
    # Projection operator (axis + shape label coverage).
    {
        "name": "radial_projection_shape_3",
        "kind": "vector",
        "unit": "1",
        "description": "Projection with axis+shape metadata.",
        "status": "draft",
        "arguments": [
            {
                "name": "magnetic_field",
                "operator": "projection",
                "operator_kind": "unary",
                "axis": "r",
                "shape": "3",
            }
        ],
    },
]


@pytest.fixture()
def fixture_catalog(tmp_path: Path) -> Path:
    """Build a per-domain catalog layout under ``tmp_path``."""
    catalog_root = tmp_path / "catalog"
    sn_dir = catalog_root / "standard_names"
    sn_dir.mkdir(parents=True)
    (sn_dir / "testdomain.yml").write_text(
        yaml.safe_dump(_DOMAIN_FIXTURE, sort_keys=False), encoding="utf-8"
    )
    return catalog_root


# ---------------------------------------------------------------------------
# build_catalog_graph
# ---------------------------------------------------------------------------
class TestBuildCatalogGraph:
    def test_nodes_and_edges_present(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        assert "magnetic_field" in g
        assert "x_component_of_magnetic_field" in g
        assert g.has_edge("x_component_of_magnetic_field", "magnetic_field")
        data = g.get_edge_data("x_component_of_magnetic_field", "magnetic_field")
        assert data["edge_type"] == "HAS_ARGUMENT"
        assert data["operator"] == "component"
        assert data["axis"] == "x"

    def test_binary_operator_two_edges(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        ratio = "ratio_of_pressure_to_density"
        assert g.has_edge(ratio, "pressure")
        assert g.has_edge(ratio, "density")
        for tgt, expected_role in [("pressure", "a"), ("density", "b")]:
            data = g.get_edge_data(ratio, tgt)
            assert data["edge_type"] == "HAS_ARGUMENT"
            assert data["role"] == expected_role

    def test_projection_operator_carries_axis_and_shape(
        self, fixture_catalog: Path
    ) -> None:
        g = build_catalog_graph(fixture_catalog)
        data = g.get_edge_data("radial_projection_shape_3", "magnetic_field")
        assert data["edge_type"] == "HAS_ARGUMENT"
        assert data["operator"] == "projection"
        assert data["axis"] == "r"
        assert data["shape"] == "3"

    def test_error_variants_edges_base_to_variant(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        for variant, error_type in [
            ("upper_uncertainty_of_temperature", "upper"),
            ("lower_uncertainty_of_temperature", "lower"),
            ("uncertainty_index_of_temperature", "index"),
        ]:
            assert g.has_edge("temperature", variant)
            data = g.get_edge_data("temperature", variant)
            assert data["edge_type"] == "HAS_ERROR"
            assert data["error_type"] == error_type

    def test_deprecation_edges(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        assert g.has_edge("old_name", "new_name")
        assert g.get_edge_data("old_name", "new_name")["edge_type"] == "HAS_SUCCESSOR"
        assert g.has_edge("new_name", "old_name")
        assert g.get_edge_data("new_name", "old_name")["edge_type"] == "HAS_PREDECESSOR"

    def test_link_edges_resolve_internal_refs(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        assert g.has_edge("poloidal_magnetic_flux", "magnetic_field")
        assert (
            g.get_edge_data("poloidal_magnetic_flux", "magnetic_field")["edge_type"]
            == "REFERENCES"
        )

    def test_forward_reference_creates_stub(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        assert "missing_base" in g
        assert g.nodes["missing_base"].get("stub") is True
        # Real entries are not stubs.
        assert g.nodes["magnetic_field"].get("stub") is False

    def test_all_edge_types_used(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        observed = {data["edge_type"] for _, _, data in g.edges(data=True)}
        assert observed == ALL_EDGE_TYPES


# ---------------------------------------------------------------------------
# get_neighbours / ancestors / descendants / shortest_path
# ---------------------------------------------------------------------------
class TestGraphTraversal:
    def test_neighbours_outgoing_only(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        results = get_neighbours(g, "x_component_of_magnetic_field", direction="out")
        assert len(results) == 1
        assert results[0]["neighbour"] == "magnetic_field"
        assert results[0]["edge_type"] == "HAS_ARGUMENT"
        assert results[0]["direction"] == "out"
        assert results[0]["props"]["axis"] == "x"

    def test_neighbours_incoming_includes_error_base(
        self, fixture_catalog: Path
    ) -> None:
        g = build_catalog_graph(fixture_catalog)
        results = get_neighbours(g, "upper_uncertainty_of_temperature", direction="in")
        assert any(
            r["neighbour"] == "temperature" and r["edge_type"] == "HAS_ERROR"
            for r in results
        )

    def test_neighbours_filter_by_edge_type(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        results = get_neighbours(
            g, "temperature", edge_types={"HAS_ERROR"}, direction="both"
        )
        assert all(r["edge_type"] == "HAS_ERROR" for r in results)
        assert {r["neighbour"] for r in results} == {
            "upper_uncertainty_of_temperature",
            "lower_uncertainty_of_temperature",
            "uncertainty_index_of_temperature",
        }

    def test_ancestors_unary_component(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        assert get_ancestors(g, "x_component_of_magnetic_field") == ["magnetic_field"]

    def test_ancestors_uncertainty_variant_reaches_base(
        self, fixture_catalog: Path
    ) -> None:
        g = build_catalog_graph(fixture_catalog)
        # error-variants are ancestors via HAS_ERROR-incoming
        ancestors = get_ancestors(g, "upper_uncertainty_of_temperature")
        assert "temperature" in ancestors

    def test_descendants_base_enumerates_wrappers_and_variants(
        self, fixture_catalog: Path
    ) -> None:
        g = build_catalog_graph(fixture_catalog)
        descendants = set(get_descendants(g, "magnetic_field"))
        assert "x_component_of_magnetic_field" in descendants
        assert "radial_projection_shape_3" in descendants

        temp_descendants = set(get_descendants(g, "temperature"))
        assert "upper_uncertainty_of_temperature" in temp_descendants
        assert "lower_uncertainty_of_temperature" in temp_descendants
        assert "uncertainty_index_of_temperature" in temp_descendants

    def test_shortest_path_records_edge_types(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        path = shortest_path(g, "x_component_of_magnetic_field", "magnetic_field")
        assert path == [
            {"name": "x_component_of_magnetic_field", "edge_type_in": None},
            {"name": "magnetic_field", "edge_type_in": "HAS_ARGUMENT"},
        ]

    def test_shortest_path_no_route(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        assert shortest_path(g, "pressure", "temperature") == []

    def test_unknown_edge_type_rejected(self, fixture_catalog: Path) -> None:
        g = build_catalog_graph(fixture_catalog)
        with pytest.raises(ValueError):
            get_neighbours(g, "magnetic_field", edge_types={"HAS_WAT"})


# ---------------------------------------------------------------------------
# MCP tool wrapper
# ---------------------------------------------------------------------------
class TestLocalGraphMCPTool:
    def test_tool_builds_graph_and_returns_neighbours(
        self, fixture_catalog: Path
    ) -> None:
        import asyncio

        from imas_standard_names.tools.graph import LocalGraphTool

        tool = LocalGraphTool(catalog_root=str(fixture_catalog))
        result = asyncio.run(
            tool.get_standard_name_neighbours(
                "x_component_of_magnetic_field", direction="out"
            )
        )
        assert result["name"] == "x_component_of_magnetic_field"
        assert result["count"] == 1
        assert result["results"][0]["neighbour"] == "magnetic_field"

    def test_tool_rejects_bad_direction(self, fixture_catalog: Path) -> None:
        import asyncio

        from imas_standard_names.tools.graph import LocalGraphTool

        tool = LocalGraphTool(catalog_root=str(fixture_catalog))
        result = asyncio.run(
            tool.get_standard_name_neighbours("magnetic_field", direction="sideways")
        )
        assert "error" in result

    def test_tool_ancestors_descendants_path(self, fixture_catalog: Path) -> None:
        import asyncio

        from imas_standard_names.tools.graph import LocalGraphTool

        tool = LocalGraphTool(catalog_root=str(fixture_catalog))
        anc = asyncio.run(
            tool.get_standard_name_ancestors("x_component_of_magnetic_field")
        )
        assert "magnetic_field" in anc["ancestors"]

        desc = asyncio.run(tool.get_standard_name_descendants("magnetic_field"))
        assert "x_component_of_magnetic_field" in desc["descendants"]

        path = asyncio.run(
            tool.shortest_standard_name_path(
                "x_component_of_magnetic_field", "magnetic_field"
            )
        )
        assert path["hops"] == 1
        assert path["path"][-1]["edge_type_in"] == "HAS_ARGUMENT"


# ---------------------------------------------------------------------------
# Renderer upgrades
# ---------------------------------------------------------------------------
class TestRenderer:
    def test_links_field_resolved_as_anchors(self, fixture_catalog: Path) -> None:
        renderer = CatalogRenderer(fixture_catalog / "standard_names")
        out = renderer.render_catalog()
        assert "[magnetic_field](#magnetic_field)" in out

    def test_cocos_transformation_type_not_rendered(
        self, fixture_catalog: Path
    ) -> None:
        """COCOS transformation is metadata clutter and must not appear in rendered output."""
        renderer = CatalogRenderer(fixture_catalog / "standard_names")
        out = renderer.render_catalog()
        assert "**COCOS transformation:**" not in out
        assert "psi_like" not in out

    def test_mermaid_block_for_unary_argument(self, fixture_catalog: Path) -> None:
        renderer = CatalogRenderer(fixture_catalog / "standard_names")
        out = renderer.render_catalog()
        assert "```mermaid" in out
        assert (
            'x_component_of_magnetic_field -- "component axis=x" --> magnetic_field'
            in out
        )

    def test_mermaid_block_for_binary_argument(self, fixture_catalog: Path) -> None:
        renderer = CatalogRenderer(fixture_catalog / "standard_names")
        out = renderer.render_catalog()
        assert 'ratio_of_pressure_to_density -- "ratio role=a" --> pressure' in out
        assert 'ratio_of_pressure_to_density -- "ratio role=b" --> density' in out

    def test_mermaid_block_for_error_variants(self, fixture_catalog: Path) -> None:
        renderer = CatalogRenderer(fixture_catalog / "standard_names")
        out = renderer.render_catalog()
        assert (
            'temperature -- "error upper" --> upper_uncertainty_of_temperature' in out
        )
        assert (
            'temperature -- "error lower" --> lower_uncertainty_of_temperature' in out
        )

    def test_sibling_nav_wrapped_by(self, fixture_catalog: Path) -> None:
        renderer = CatalogRenderer(fixture_catalog / "standard_names")
        out = renderer.render_catalog()
        # magnetic_field is wrapped by x_component and the projection entry.
        assert "**Wrapped by:**" in out
        assert "[x_component_of_magnetic_field](#x_component_of_magnetic_field)" in out

    def test_sibling_nav_deprecates_and_superseded_by(
        self, fixture_catalog: Path
    ) -> None:
        renderer = CatalogRenderer(fixture_catalog / "standard_names")
        out = renderer.render_catalog()
        assert "**Deprecates:** [old_name](#old_name)" in out
        assert "**Superseded by:** [new_name](#new_name)" in out
