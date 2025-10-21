"""Test that catalog reloads from disk after commit to fix fetch/search issues."""

import pytest

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog


def test_catalog_reload_after_commit(tmp_path):
    """Test that catalog is reloaded from disk after commit.

    This test verifies the fix for the bug where fetch_standard_names
    returned zero entries after a successful write because the in-memory
    SQLite database was not reloaded from the updated YAML files.
    """
    # Create a temporary catalog
    catalog = StandardNameCatalog(tmp_path)
    edit_catalog = EditCatalog(catalog)

    # Initially empty
    assert len(catalog.list_names()) == 0

    # Create entries
    entries = [
        {
            "name": "test_scalar_1",
            "kind": "scalar",
            "description": "Test scalar 1",
            "unit": "m",
            "tags": ["fundamental"],
        },
        {
            "name": "test_scalar_2",
            "kind": "scalar",
            "description": "Test scalar 2",
            "unit": "s",
            "tags": ["fundamental"],
        },
    ]

    # Add entries via EditCatalog
    for entry in entries:
        edit_catalog.add(entry)

    # Verify entries are in memory before commit
    assert len(catalog.list_names()) == 2
    assert catalog.exists("test_scalar_1")
    assert catalog.exists("test_scalar_2")

    # Commit (writes to disk)
    result = edit_catalog.commit()
    assert result["ok"]
    assert result["committed"]

    # CRITICAL: After commit, catalog should still be able to fetch entries
    # This was the bug - catalog.list_names() would return [] because
    # the SQLite database was not reloaded from YAML files
    assert len(catalog.list_names()) == 2, (
        "Catalog should reload from disk after commit"
    )
    assert catalog.exists("test_scalar_1"), "Should be able to fetch entry after commit"
    assert catalog.exists("test_scalar_2"), "Should be able to fetch entry after commit"

    # Verify get() also works
    entry1 = catalog.get("test_scalar_1")
    assert entry1 is not None
    assert entry1.name == "test_scalar_1"

    # Verify search works
    results = catalog.search("test scalar")
    assert len(results) >= 2


def test_catalog_reload_after_multiple_commits(tmp_path):
    """Test that catalog remains consistent through multiple commit cycles."""
    catalog = StandardNameCatalog(tmp_path)
    edit_catalog = EditCatalog(catalog)

    # First commit cycle
    edit_catalog.add(
        {
            "name": "entry_1",
            "kind": "scalar",
            "description": "First entry",
            "tags": ["fundamental"],
        }
    )
    edit_catalog.commit()

    assert len(catalog.list_names()) == 1
    assert catalog.exists("entry_1")

    # Second commit cycle - add more
    edit_catalog.add(
        {
            "name": "entry_2",
            "kind": "scalar",
            "description": "Second entry",
            "tags": ["fundamental"],
        }
    )
    edit_catalog.commit()

    # Both entries should be accessible
    assert len(catalog.list_names()) == 2
    assert catalog.exists("entry_1")
    assert catalog.exists("entry_2")

    # Third commit cycle - delete one
    edit_catalog.delete("entry_1")
    edit_catalog.commit()

    # Only entry_2 should remain
    assert len(catalog.list_names()) == 1
    assert not catalog.exists("entry_1")
    assert catalog.exists("entry_2")


def test_catalog_reload_preserves_relationships(tmp_path):
    """Test that reload preserves provenance and tag relationships."""
    catalog = StandardNameCatalog(tmp_path)
    edit_catalog = EditCatalog(catalog)

    # Create base scalar
    edit_catalog.add(
        {
            "name": "base_quantity",
            "kind": "scalar",
            "description": "Base quantity",
            "unit": "m",
            "tags": ["fundamental", "measured"],
        }
    )

    # Create derived scalar with provenance
    edit_catalog.add(
        {
            "name": "gradient_of_base_quantity",
            "kind": "vector",
            "description": "Gradient of base quantity",
            "unit": "m.m^-1",
            "tags": ["fundamental", "derived"],
            "provenance": {
                "mode": "operator",
                "operators": ["gradient"],
                "base": "base_quantity",
            },
        }
    )

    edit_catalog.commit()

    # Verify both entries and their metadata are accessible
    assert len(catalog.list_names()) == 2

    base = catalog.get("base_quantity")
    assert base is not None
    assert base.tags == ["fundamental", "measured"]

    derived = catalog.get("gradient_of_base_quantity")
    assert derived is not None
    assert derived.provenance is not None
    assert derived.provenance.mode == "operator"
    assert derived.provenance.base == "base_quantity"
