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

    # Try to create entry with no physics_domain - should fail immediately
    with pytest.raises(ValueError, match="physics_domain"):
        invalid_entry = {
            "name": "test_quantity",
            "kind": "scalar",
            "description": "Test with only secondary tags.",
            "unit": "m",
            "tags": ["measured", "calibrated"],  # No physics_domain provided
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
        "documentation": "Electron density for validation timing testing.",
        "unit": "m^-3",
        "physics_domain": "general",
        "tags": ["measured"],
    }
    edit_catalog.add(valid_entry)

    # Entry should be in memory
    assert catalog.get("electron_density") is not None
    assert edit_catalog.diff()["counts"]["total_pending"] == 1

    # Commit should succeed
    result = edit_catalog.commit()
    assert result["ok"] is True

    # File should exist
    yaml_file = catalog_root / "general" / "electron_density.yml"
    assert yaml_file.exists()

    # No pending changes
    assert edit_catalog.diff()["counts"]["total_pending"] == 0


def test_physics_domain_determines_directory(tmp_path):
    """Test that physics_domain determines the storage subdirectory."""
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    catalog = StandardNameCatalog(root=catalog_root)
    edit_catalog = EditCatalog(catalog)

    entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity.",
        "documentation": "Test quantity for physics domain directory.",
        "unit": "T",
        "physics_domain": "magnetic_field_diagnostics",
        "tags": ["measured", "calibrated"],
    }

    edit_catalog.add(entry)
    created_entry = catalog.get("test_quantity")

    assert created_entry.physics_domain == "magnetic_field_diagnostics"
    assert set(created_entry.tags) == {"measured", "calibrated"}

    # Commit should succeed
    result = edit_catalog.commit()
    assert result["ok"] is True

    # File should be in physics_domain subdirectory
    yaml_file = catalog_root / "magnetic_field_diagnostics" / "test_quantity.yml"
    assert yaml_file.exists()


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
