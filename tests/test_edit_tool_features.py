"""Tests for new edit tool features: batch_delete and dry_run."""

import asyncio

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.edit import CatalogTool


def invoke(tool, payload):
    """Helper to invoke async tool method."""
    return asyncio.run(tool.edit_standard_name(payload))


def test_delete_with_dry_run(tmp_path):
    """Test that delete with dry_run shows dependencies without deleting."""
    repo = StandardNameCatalog(root=tmp_path)
    edit_catalog = EditCatalog(repo)
    tool = CatalogTool(repo, edit_catalog)

    # Create a test entry first
    test_entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity.",
        "unit": "m",
        "tags": ["fundamental"],
    }
    edit_catalog.add(test_entry)
    edit_catalog.commit()

    # Get the name that exists
    target_name = "test_quantity"

    # Delete with dry_run=True
    result = invoke(tool, {"action": "delete", "name": target_name, "dry_run": True})

    # Should return success with dry_run flag and dependencies info
    assert result["action"] == "delete"
    assert result["dry_run"] is True
    assert "dependencies" in result
    assert result["existed"] is True

    # Verify entry still exists (wasn't actually deleted)
    assert repo.get(target_name) is not None


def test_delete_without_dry_run(tmp_path):
    """Test that delete without dry_run actually removes the entry."""
    repo = StandardNameCatalog(root=tmp_path)
    edit_catalog = EditCatalog(repo)
    tool = CatalogTool(repo, edit_catalog)

    # Create a test entry first
    test_entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity.",
        "unit": "m",
        "tags": ["fundamental"],
    }
    edit_catalog.add(test_entry)
    edit_catalog.commit()

    # Get the name that exists
    target_name = "test_quantity"

    # Delete without dry_run (default behavior)
    result = invoke(tool, {"action": "delete", "name": target_name})

    # Should return success
    assert result["action"] == "delete"
    assert result["existed"] is True
    assert result.get("dry_run", False) is False

    # Verify entry is removed from catalog view
    # (Note: it's staged for deletion, not committed yet)
    assert edit_catalog.has_pending_changes()


def test_rename_with_dry_run(tmp_path):
    """Test that rename with dry_run shows dependencies without renaming."""
    repo = StandardNameCatalog(root=tmp_path)
    edit_catalog = EditCatalog(repo)
    tool = CatalogTool(repo, edit_catalog)

    # Create a test entry first
    test_entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity.",
        "unit": "m",
        "tags": ["fundamental"],
    }
    edit_catalog.add(test_entry)
    edit_catalog.commit()

    # Get the name that exists
    old_name = "test_quantity"
    new_name = "test_quantity_renamed"

    # Rename with dry_run=True
    result = invoke(
        tool,
        {
            "action": "rename",
            "old_name": old_name,
            "new_name": new_name,
            "dry_run": True,
        },
    )

    # Should return success with dry_run flag and dependencies
    assert result["action"] == "rename"
    assert result["dry_run"] is True
    assert "dependencies" in result
    assert result["old_name"] == old_name
    assert result["new_name"] == new_name

    # Verify original name still exists (wasn't actually renamed)
    assert repo.get(old_name) is not None
    assert repo.get(new_name) is None


def test_batch_delete(tmp_path):
    """Test batch deletion of multiple entries."""
    repo = StandardNameCatalog(root=tmp_path)
    edit_catalog = EditCatalog(repo)
    tool = CatalogTool(repo, edit_catalog)

    # Create test entries first
    for i in range(3):
        test_entry = {
            "name": f"test_quantity_{i}",
            "kind": "scalar",
            "description": f"Test quantity {i}.",
            "unit": "m",
            "tags": ["fundamental"],
        }
        edit_catalog.add(test_entry)
    edit_catalog.commit()

    # Get the names to delete
    names_to_delete = [f"test_quantity_{i}" for i in range(3)]

    # Batch delete
    result = invoke(tool, {"action": "batch_delete", "names": names_to_delete})

    # Should return batch_delete result
    assert result["action"] == "batch_delete"
    assert result["dry_run"] is False
    assert "summary" in result
    assert result["summary"]["total"] == 3
    assert result["summary"]["successful"] == 3

    # Check results list
    assert "results" in result
    assert len(result["results"]) == 3
    for name, existed, deps in result["results"]:
        assert name in names_to_delete
        assert existed is True
        assert deps is None  # No dependencies requested without dry_run


def test_batch_delete_with_dry_run(tmp_path):
    """Test batch deletion with dry_run shows dependencies for all entries."""
    repo = StandardNameCatalog(root=tmp_path)
    edit_catalog = EditCatalog(repo)
    tool = CatalogTool(repo, edit_catalog)

    # Create test entries first
    for i in range(3):
        test_entry = {
            "name": f"test_quantity_{i}",
            "kind": "scalar",
            "description": f"Test quantity {i}.",
            "unit": "m",
            "tags": ["fundamental"],
        }
        edit_catalog.add(test_entry)
    edit_catalog.commit()

    # Get the names to check
    names_to_check = [f"test_quantity_{i}" for i in range(3)]

    # Batch delete with dry_run
    result = invoke(
        tool, {"action": "batch_delete", "names": names_to_check, "dry_run": True}
    )

    # Should return batch_delete result with dependencies
    assert result["action"] == "batch_delete"
    assert result["dry_run"] is True
    assert "summary" in result
    assert result["summary"]["total"] == 3

    # Check results include dependency information
    assert "results" in result
    for name, existed, deps in result["results"]:
        assert name in names_to_check
        assert existed is True
        assert deps is not None  # Dependencies checked with dry_run
        assert isinstance(deps, list)

    # Verify entries still exist
    for name in names_to_check:
        assert repo.get(name) is not None


def test_batch_delete_nonexistent_names():
    """Test batch deletion handles non-existent names gracefully."""
    repo = StandardNameCatalog()
    edit_catalog = EditCatalog(repo)
    tool = CatalogTool(repo, edit_catalog)

    # Use names that don't exist
    fake_names = ["nonexistent_name_1", "nonexistent_name_2"]

    # Batch delete
    result = invoke(tool, {"action": "batch_delete", "names": fake_names})

    # Should return result with existed=False for each
    assert result["action"] == "batch_delete"
    assert result["summary"]["total"] == 2
    assert result["summary"]["successful"] == 0  # None existed

    # Check results
    for name, existed, _deps in result["results"]:
        assert name in fake_names
        assert existed is False
