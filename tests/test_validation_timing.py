"""Test to validate current write behavior - entries validated at creation time."""

import pytest

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog


def test_invalid_entry_rejected_at_creation(tmp_path):
    """Test that invalid entries are rejected at creation time, not write time."""
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    catalog = StandardNameCatalog(root=catalog_root)
    edit_catalog = EditCatalog(catalog)

    # Try to create entry with no primary tag - should fail immediately
    with pytest.raises(ValueError, match="exactly one primary tag"):
        invalid_entry = {
            "name": "test_quantity",
            "kind": "scalar",
            "description": "Test with only secondary tags.",
            "unit": "m",
            "tags": ["measured", "calibrated"],  # Both secondary, no primary
        }
        edit_catalog.add(invalid_entry)

    # Verify nothing was added
    assert catalog.get("test_quantity") is None
    assert edit_catalog.diff()["counts"]["total_pending"] == 0


def test_valid_entry_accepted_and_writable(tmp_path):
    """Test that valid entries are accepted at creation and successfully written."""
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    catalog = StandardNameCatalog(root=catalog_root)
    edit_catalog = EditCatalog(catalog)

    # Create valid entry
    valid_entry = {
        "name": "electron_density",
        "kind": "scalar",
        "description": "Electron density.",
        "unit": "m^-3",
        "tags": ["fundamental", "measured"],
    }
    edit_catalog.add(valid_entry)

    # Entry should be in memory
    assert catalog.get("electron_density") is not None
    assert edit_catalog.diff()["counts"]["total_pending"] == 1

    # Commit should succeed
    result = edit_catalog.commit()
    assert result["ok"] is True

    # File should exist
    yaml_file = catalog_root / "fundamental" / "electron_density.yml"
    assert yaml_file.exists()

    # No pending changes
    assert edit_catalog.diff()["counts"]["total_pending"] == 0


def test_tag_auto_reordering(tmp_path):
    """Test that tags are automatically reordered to put primary tag first."""
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    catalog = StandardNameCatalog(root=catalog_root)
    edit_catalog = EditCatalog(catalog)

    # Create entry with primary tag NOT in first position
    entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity.",
        "unit": "T",
        "tags": ["measured", "magnetics", "calibrated"],  # magnetics is primary
    }

    # Entry creation succeeds and auto-reorders tags
    edit_catalog.add(entry)
    created_entry = catalog.get("test_quantity")

    # Verify tags were reordered: primary tag moved to first position
    # The order of secondary tags is preserved from input after reordering
    assert created_entry.tags[0] == "magnetics"  # Primary tag first
    assert set(created_entry.tags[1:]) == {"measured", "calibrated"}  # Secondary tags

    # Commit should succeed
    result = edit_catalog.commit()
    assert result["ok"] is True

    # File should be in magnetics subdirectory
    yaml_file = catalog_root / "magnetics" / "test_quantity.yml"
    assert yaml_file.exists()


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
