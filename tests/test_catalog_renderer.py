"""Tests for catalog rendering functionality."""

from pathlib import Path

from imas_standard_names.rendering.catalog import CatalogRenderer


def _make_test_catalog(tmp_path: Path) -> Path:
    """Create a minimal test catalog with physics_domain set."""
    (tmp_path / "electron_temperature.yml").write_text(
        """name: electron_temperature
kind: scalar
status: active
unit: eV
physics_domain: transport
description: Electron temperature.
documentation: |
  Electron temperature for testing.
""",
        encoding="utf-8",
    )
    (tmp_path / "ion_temperature.yml").write_text(
        """name: ion_temperature
kind: scalar
status: active
unit: eV
physics_domain: transport
description: Ion temperature.
documentation: |
  Ion temperature for testing.
""",
        encoding="utf-8",
    )
    return tmp_path


def test_catalog_renderer_load_names(tmp_path: Path):
    """Test loading names from catalog directory."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    names = renderer.load_names()

    assert len(names) == 2
    name_set = {n["name"] for n in names}
    assert "electron_temperature" in name_set
    assert "ion_temperature" in name_set


def test_catalog_renderer_get_domains_groups_by_physics_domain(tmp_path: Path):
    """Test that grouping uses physics_domain."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    domains = renderer.get_domains()

    assert "transport" in domains
    assert len(domains["transport"]) == 2
    assert "general" not in domains
    assert "uncategorized" not in domains


def test_catalog_renderer_get_domains_fallback_to_uncategorized(tmp_path: Path):
    """Entries without physics_domain fall back to 'uncategorized'."""
    (tmp_path / "no_domain.yml").write_text(
        """name: some_quantity
kind: scalar
status: active
unit: m
description: Has no physics_domain field.
""",
        encoding="utf-8",
    )
    renderer = CatalogRenderer(tmp_path)
    domains = renderer.get_domains()

    assert "uncategorized" in domains
    assert any(e["name"] == "some_quantity" for e in domains["uncategorized"])


def test_catalog_renderer_get_stats(tmp_path: Path):
    """Test catalog statistics."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    stats = renderer.get_stats()

    assert stats["total_names"] == 2
    assert stats["total_domains"] == 1  # both have physics_domain: transport
    assert "transport" in stats["domains"]


def test_catalog_renderer_render_overview(tmp_path: Path):
    """Test rendering catalog overview."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    overview = renderer.render_overview()

    assert "Total Standard Names:" in overview
    assert "2" in overview
    # Domain heading uses title-cased domain name
    assert "Transport" in overview


def test_catalog_renderer_render_catalog_groups_by_physics_domain(tmp_path: Path):
    """Catalog H2 sections are physics domains, not tags."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    catalog = renderer.render_catalog()

    # H2 section header is title-cased domain
    assert "## Transport" in catalog
    # Anchor is the raw domain key
    assert "{: #transport }" in catalog
    # Names appear verbatim
    assert "electron_temperature" in catalog
    assert "ion_temperature" in catalog
    # Unit still rendered
    assert "**Unit:** `eV`" in catalog


def test_catalog_renderer_render_catalog_raw_base_name(tmp_path: Path):
    """Base name heading is raw snake_case in backticks, not title-cased."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    catalog = renderer.render_catalog()

    # Should see backtick-wrapped snake_case base name in an H3
    assert "### `" in catalog
    # Should NOT see title-cased transformation
    assert "Electron Temperature" not in catalog
    assert "Ion Temperature" not in catalog


def test_catalog_renderer_render_catalog_no_cocos_no_tags(tmp_path: Path):
    """COCOS transformation and tags rows are absent from rendered output."""
    (tmp_path / "psi.yml").write_text(
        """name: poloidal_flux
kind: scalar
status: active
unit: Wb
physics_domain: equilibrium
description: Poloidal flux.
cocos_transformation_type: psi_like
tags: [equilibrium, magnetics]
""",
        encoding="utf-8",
    )
    renderer = CatalogRenderer(tmp_path)
    catalog = renderer.render_catalog()

    assert "**COCOS" not in catalog
    assert "**Transformation" not in catalog
    assert "**Tags:**" not in catalog


def test_catalog_renderer_empty_catalog(tmp_path: Path):
    """Test rendering empty catalog."""
    renderer = CatalogRenderer(tmp_path)
    catalog = renderer.render_catalog()

    assert "No standard names found" in catalog


def test_catalog_renderer_render_navigation(tmp_path: Path):
    """Test rendering navigation."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    nav = renderer.render_navigation()

    # Navigation section uses title-cased domain
    assert "Transport" in nav
    # Raw names are linked
    assert "electron_temperature" in nav
    assert "ion_temperature" in nav


def test_catalog_renderer_loads_from_subdirectories(tmp_path: Path):
    """Test that catalog renderer recursively loads from subdirectories.

    This reproduces the issue where `docs build` found 0 entries while
    `build` found 305 entries in a catalog with YAML files organized
    in subdirectories by primary tag.
    """
    # Create subdirectory structure mimicking real catalog organization
    transport_dir = tmp_path / "transport"
    transport_dir.mkdir()
    (transport_dir / "electron_temperature.yml").write_text(
        """name: electron_temperature
kind: scalar
status: active
unit: eV
physics_domain: transport
description: Electron temperature.
""",
        encoding="utf-8",
    )

    geometry_dir = tmp_path / "geometry"
    geometry_dir.mkdir()
    (geometry_dir / "major_radius.yml").write_text(
        """name: major_radius
kind: scalar
status: active
unit: m
physics_domain: geometry
description: Major radius of the plasma.
""",
        encoding="utf-8",
    )

    # Create nested subdirectory
    nested_dir = tmp_path / "diagnostics" / "magnetics"
    nested_dir.mkdir(parents=True)
    (nested_dir / "magnetic_field.yml").write_text(
        """name: magnetic_field
kind: scalar
status: active
unit: T
physics_domain: magnetics
description: Magnetic field measurement.
tags: [measured]
""",
        encoding="utf-8",
    )

    renderer = CatalogRenderer(tmp_path)
    names = renderer.load_names()

    # Should find all 3 entries across subdirectories
    assert len(names) == 3
    name_set = {n["name"] for n in names}
    assert "electron_temperature" in name_set
    assert "major_radius" in name_set
    assert "magnetic_field" in name_set


# ---------------------------------------------------------------------------
# Fix 5: name: link rewriting
# ---------------------------------------------------------------------------


def test_rewrite_name_links_single(tmp_path: Path):
    """[label](name:foo) is rewritten to [label](#foo)."""
    from imas_standard_names.rendering.catalog import _rewrite_name_links

    assert _rewrite_name_links("[foo](#foo)") == "[foo](#foo)"  # already good
    assert _rewrite_name_links("[foo](name:foo)") == "[foo](#foo)"


def test_rewrite_name_links_external_untouched(tmp_path: Path):
    """External https:// links are not modified."""
    from imas_standard_names.rendering.catalog import _rewrite_name_links

    link = "[ext](https://example.com/doc)"
    assert _rewrite_name_links(link) == link


def test_rewrite_name_links_multiple_in_paragraph(tmp_path: Path):
    """Multiple name: links in one paragraph are all rewritten."""
    from imas_standard_names.rendering.catalog import _rewrite_name_links

    text = "See [foo](name:foo) and also [bar_baz](name:bar_baz) for details."
    result = _rewrite_name_links(text)
    assert "[foo](#foo)" in result
    assert "[bar_baz](#bar_baz)" in result
    assert "name:" not in result


def test_catalog_render_rewrites_name_links_in_documentation(tmp_path: Path):
    """name: links inside documentation strings are rewritten to anchors."""
    (tmp_path / "alpha.yml").write_text(
        """name: alpha_quantity
kind: scalar
status: active
unit: m
physics_domain: geometry
description: See also [beta_quantity](name:beta_quantity).
documentation: |
  Detailed text referencing [beta_quantity](name:beta_quantity).
""",
        encoding="utf-8",
    )
    renderer = CatalogRenderer(tmp_path)
    catalog = renderer.render_catalog()

    assert "[beta_quantity](#beta_quantity)" in catalog
    assert "name:beta_quantity" not in catalog


# ---------------------------------------------------------------------------
# Fix 6: sources debug block
# ---------------------------------------------------------------------------


def test_render_sources_empty(tmp_path: Path):
    """No sources block when sources list is empty."""
    from imas_standard_names.rendering.catalog import CatalogRenderer

    renderer = CatalogRenderer(tmp_path)
    assert renderer._render_sources([]) == ""


def test_render_sources_dd_path(tmp_path: Path):
    """Sources block emits dd_path labels inside <details>."""
    from imas_standard_names.rendering.catalog import CatalogRenderer

    renderer = CatalogRenderer(tmp_path)
    sources = [
        {"dd_path": "equilibrium/time_slice/profiles_1d/psi", "status": "extracted"},
        {
            "dd_path": "core_profiles/profiles_1d/electrons/temperature",
            "status": "composed",
        },
    ]
    block = renderer._render_sources(sources)

    assert "<details>" in block
    assert "<summary>Sources (debug)</summary>" in block
    assert "`dd:equilibrium/time_slice/profiles_1d/psi` (extracted)" in block
    assert "`dd:core_profiles/profiles_1d/electrons/temperature` (composed)" in block
    assert "</details>" in block


def test_catalog_render_includes_sources_block(tmp_path: Path):
    """Sources <details> block appears in full catalog render when sources present."""
    (tmp_path / "psi.yml").write_text(
        """name: poloidal_flux
kind: scalar
status: active
unit: Wb
physics_domain: equilibrium
description: Poloidal flux.
documentation: |
  The poloidal flux.
sources:
- dd_path: equilibrium/time_slice/profiles_1d/psi
  status: extracted
""",
        encoding="utf-8",
    )
    renderer = CatalogRenderer(tmp_path)
    catalog = renderer.render_catalog()

    assert "<details>" in catalog
    assert "Sources (debug)" in catalog
    assert "equilibrium/time_slice/profiles_1d/psi" in catalog


def test_catalog_render_no_sources_block_when_absent(tmp_path: Path):
    """No <details> block when sources field is absent from YAML."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    catalog = renderer.render_catalog()

    assert "<details>" not in catalog
    assert "Sources (debug)" not in catalog
