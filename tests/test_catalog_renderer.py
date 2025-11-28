"""Tests for catalog rendering functionality."""

from pathlib import Path

from imas_standard_names.rendering.catalog import CatalogRenderer


def _make_test_catalog(tmp_path: Path) -> Path:
    """Create a minimal test catalog."""
    (tmp_path / "electron_temperature.yml").write_text(
        """name: electron_temperature
kind: scalar
status: active
unit: eV
description: Electron temperature.
documentation: |
  Electron temperature for testing.
tags: [fundamental, plasma]
""",
        encoding="utf-8",
    )
    (tmp_path / "ion_temperature.yml").write_text(
        """name: ion_temperature
kind: scalar
status: active
unit: eV
description: Ion temperature.
documentation: |
  Ion temperature for testing.
tags: [fundamental]
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


def test_catalog_renderer_get_tags(tmp_path: Path):
    """Test grouping names by primary tag."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    tags = renderer.get_tags()

    assert "fundamental" in tags
    assert len(tags["fundamental"]) == 2


def test_catalog_renderer_get_stats(tmp_path: Path):
    """Test catalog statistics."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    stats = renderer.get_stats()

    assert stats["total_names"] == 2
    assert stats["total_tags"] == 1  # both have "fundamental" as primary
    assert "fundamental" in stats["tags"]


def test_catalog_renderer_render_overview(tmp_path: Path):
    """Test rendering catalog overview."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    overview = renderer.render_overview()

    assert "Total Standard Names:" in overview
    assert "2" in overview
    assert "Fundamental" in overview


def test_catalog_renderer_render_catalog(tmp_path: Path):
    """Test rendering full catalog."""
    catalog_path = _make_test_catalog(tmp_path)
    renderer = CatalogRenderer(catalog_path)
    catalog = renderer.render_catalog()

    assert "electron_temperature" in catalog
    assert "ion_temperature" in catalog
    assert "Fundamental" in catalog
    assert "**Unit:** `eV`" in catalog


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

    assert "Fundamental" in nav
    assert "electron_temperature" in nav
    assert "ion_temperature" in nav
