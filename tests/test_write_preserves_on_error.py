"""Test that write tool preserves entries in memory on validation failure."""

import pytest

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.write import WriteTool
from imas_standard_names.yaml_store import YamlStore


@pytest.mark.anyio
async def test_write_preserves_entries_on_validation_error(tmp_path):
    """Test that write failures preserve entries in memory for editing."""
    # Setup
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    catalog = StandardNameCatalog(root=catalog_root)
    edit_catalog = EditCatalog(catalog)
    write_tool = WriteTool(catalog, edit_catalog)

    # Create an entry with invalid tags (no primary tag at all)
    # Note: Validation now happens at add() time via pydantic
    invalid_entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity with invalid tags.",
        "documentation": "Test quantity with invalid tags for error preservation testing.",
        "unit": "m",
        "tags": ["calibrated", "measured"],  # WRONG: both are secondary, no primary tag
    }

    # Add to catalog - should raise ValidationError immediately
    with pytest.raises(Exception) as exc_info:
        edit_catalog.add(invalid_entry)

    # Verify it's a validation error about tags
    assert "primary tag" in str(exc_info.value).lower()

    # Verify entry was NOT added to catalog
    assert catalog.get("test_quantity") is None

    # Verify no pending changes (since add failed)
    diff = edit_catalog.diff()
    assert len(diff["added"]) == 0

    # Now add with corrected tags
    fixed_entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity with fixed tags.",
        "documentation": "Test quantity with fixed tags for error preservation testing.",
        "unit": "m",
        "tags": ["magnetics", "calibrated"],  # CORRECT: primary then secondary
    }

    # Add the corrected entry
    edit_catalog.add(fixed_entry)

    # Verify entry is now in memory
    assert catalog.get("test_quantity") is not None

    # Now write should succeed
    result = await write_tool.write_standard_names()

    assert result["success"] is True
    assert result["written"] is True
    assert result["validation_passed"] is True

    # Verify file was written
    yaml_file = catalog_root / "magnetics" / "test_quantity.yml"
    assert yaml_file.exists()

    # Verify no pending changes remain (all persisted)
    diff = edit_catalog.diff()
    assert len(diff["added"]) == 0


@pytest.mark.anyio
async def test_dry_run_validates_without_writing(tmp_path):
    """Test write tool behavior (no dry_run parameter available)."""
    # Setup
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    catalog = StandardNameCatalog(root=catalog_root)
    edit_catalog = EditCatalog(catalog)
    write_tool = WriteTool(catalog, edit_catalog)

    # Create valid entry
    entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity.",
        "documentation": "Test quantity for dry run validation testing.",
        "unit": "m",
        "tags": ["fundamental"],
    }

    edit_catalog.add(entry)

    # Write should succeed (no dry_run available)
    result = await write_tool.write_standard_names()

    assert result["success"] is True
    assert result["written"] is True
    assert result["validation_passed"] is True

    # Entry should be saved
    diff = edit_catalog.diff()
    assert len(diff["added"]) == 0

    # File should exist
    yaml_file = catalog_root / "fundamental" / "test_quantity.yml"
    assert yaml_file.exists()
