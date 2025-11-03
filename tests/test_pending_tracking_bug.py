"""Test to reproduce and fix the pending changes tracking bug."""

import pytest

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog


def test_modify_should_appear_in_pending(temp_catalog, temp_edit_catalog):
    """Test that modified entries appear in pending list."""
    # Create a test entry
    entry_data = {
        "name": "test_quantity",
        "description": "Original description",
        "documentation": "Test quantity for tracking pending modifications.",
        "unit": "m",
        "status": "draft",
        "tags": ["equilibrium"],
        "kind": "scalar",
    }

    temp_edit_catalog.add(entry_data)
    temp_edit_catalog.write()  # Commit to disk

    # Check no pending changes after write
    diff1 = temp_edit_catalog.diff()
    assert diff1["counts"]["total_pending"] == 0, "Should have 0 pending after write"

    # Now modify the entry
    temp_edit_catalog.modify(
        "test_quantity", updates={"description": "Modified description"}
    )

    # Check that modification appears in pending
    diff2 = temp_edit_catalog.diff()

    print("\nDEBUG: After modify:")
    print(f"  total_pending: {diff2['counts']['total_pending']}")
    print(f"  updated: {diff2['counts']['updated']}")
    print(f"  modified list: {diff2['updated']}")
    print(f"  dirty_names: {temp_edit_catalog._dirty_names}")

    # Fetch the entry to see current state
    current_entry = temp_catalog.get("test_quantity")
    print(
        f"  current description: {current_entry.description if current_entry else 'NOT FOUND'}"
    )

    # Check baseline snapshot
    baseline_entry = temp_edit_catalog._baseline_snapshot.get("test_quantity")
    print(
        f"  baseline description: {baseline_entry['description'] if baseline_entry else 'NOT IN BASELINE'}"
    )

    assert diff2["counts"]["total_pending"] == 1, (
        "Should have 1 pending change after modify"
    )
    assert diff2["counts"]["updated"] == 1, "Should have 1 updated entry"
    assert len(diff2["updated"]) == 1, "Should have entry in updated list"
    assert diff2["updated"][0]["name"] == "test_quantity"
    assert diff2["updated"][0]["before"]["description"] == "Original description"
    assert diff2["updated"][0]["after"]["description"] == "Modified description"


def test_batch_modify_should_appear_in_pending(temp_catalog, temp_edit_catalog):
    """Test that batch modified entries appear in pending list."""
    # Create test entries
    for i in range(3):
        entry_data = {
            "name": f"test_quantity_{i}",
            "description": f"Original description {i}",
            "documentation": f"Test quantity {i} for batch modify tracking.",
            "unit": "m",
            "status": "draft",
            "tags": ["equilibrium"],
            "kind": "scalar",
        }
        temp_edit_catalog.add(entry_data)

    temp_edit_catalog.write()  # Commit to disk

    # Modify all entries
    for i in range(3):
        temp_edit_catalog.modify(
            f"test_quantity_{i}", updates={"description": f"Modified description {i}"}
        )

    # Check pending
    diff = temp_edit_catalog.diff()

    assert diff["counts"]["total_pending"] == 3, (
        f"Should have 3 pending changes, got {diff['counts']['total_pending']}"
    )
    assert diff["counts"]["updated"] == 3, (
        f"Should have 3 updated entries, got {diff['counts']['updated']}"
    )
