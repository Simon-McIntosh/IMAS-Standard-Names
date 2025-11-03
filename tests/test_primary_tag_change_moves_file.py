"""Test that changing primary tag moves file to new directory."""

from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog


def test_modify_entry_with_primary_tag_change_deletes_old_file(tmp_path):
    """When primary tag changes via modify, old file should be deleted."""
    # Setup
    root = tmp_path / "catalog"
    root.mkdir()

    # Create initial entry with "fundamental" primary tag
    initial_data = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity for primary tag change.",
        "documentation": "Test quantity for primary tag change validation.",
        "tags": ["fundamental", "spatial-profile"],
        "unit": "m",
        "status": "draft",
    }

    catalog = StandardNameCatalog(root)
    uow = catalog.start_uow()
    model = create_standard_name_entry(initial_data)
    uow.add(model)
    uow.commit()

    # Verify initial file location
    fundamental_path = root / "fundamental" / "test_quantity.yml"
    equilibrium_path = root / "equilibrium" / "test_quantity.yml"
    assert fundamental_path.exists(), "Initial file should exist in fundamental/"
    assert not equilibrium_path.exists(), "File should not yet exist in equilibrium/"

    # Modify entry to change primary tag from "fundamental" to "equilibrium"
    modified_data = initial_data.copy()
    modified_data["tags"] = ["equilibrium", "spatial-profile"]

    catalog = StandardNameCatalog(root)  # Reload catalog
    uow = catalog.start_uow()
    modified_model = create_standard_name_entry(modified_data)
    uow.update("test_quantity", modified_model)
    uow.commit()

    # Verify file has moved
    assert not fundamental_path.exists(), (
        "Old file in fundamental/ should be deleted after primary tag change"
    )
    assert equilibrium_path.exists(), (
        "New file should exist in equilibrium/ after primary tag change"
    )

    # Verify only one file exists
    all_files = list(root.rglob("test_quantity.yml"))
    assert len(all_files) == 1, (
        f"Expected exactly 1 file, found {len(all_files)}: {all_files}"
    )
    assert all_files[0] == equilibrium_path


def test_rename_entry_preserves_primary_tag_directory(tmp_path):
    """Renaming an entry should keep it in the same primary tag directory."""
    # Setup
    root = tmp_path / "catalog"
    root.mkdir()

    # Create initial entry
    initial_data = {
        "name": "old_name",
        "kind": "scalar",
        "description": "Test entry for rename.",
        "documentation": "Test entry for rename validation.",
        "tags": ["equilibrium", "spatial-profile"],
        "unit": "m",
        "status": "draft",
    }

    catalog = StandardNameCatalog(root)
    uow = catalog.start_uow()
    model = create_standard_name_entry(initial_data)
    uow.add(model)
    uow.commit()

    # Verify initial location
    old_path = root / "equilibrium" / "old_name.yml"
    assert old_path.exists()

    # Rename entry
    renamed_data = initial_data.copy()
    renamed_data["name"] = "new_name"

    catalog = StandardNameCatalog(root)  # Reload
    uow = catalog.start_uow()
    renamed_model = create_standard_name_entry(renamed_data)
    uow.rename("old_name", renamed_model)
    uow.commit()

    # Verify rename preserved directory
    new_path = root / "equilibrium" / "new_name.yml"
    assert not old_path.exists(), "Old file should be deleted"
    assert new_path.exists(), "New file should exist in same directory"

    all_files = list(root.rglob("*.yml"))
    assert len(all_files) == 1, f"Should have exactly 1 file, found {len(all_files)}"


def test_rename_with_primary_tag_change_moves_file(tmp_path):
    """Renaming and changing primary tag should move file to new directory."""
    # Setup
    root = tmp_path / "catalog"
    root.mkdir()

    # Create initial entry
    initial_data = {
        "name": "old_name",
        "kind": "scalar",
        "description": "Test entry for rename with tag change.",
        "documentation": "Test entry for rename with tag change validation.",
        "tags": ["fundamental", "spatial-profile"],
        "unit": "m",
        "status": "draft",
    }

    catalog = StandardNameCatalog(root)
    uow = catalog.start_uow()
    model = create_standard_name_entry(initial_data)
    uow.add(model)
    uow.commit()

    # Verify initial location
    old_path = root / "fundamental" / "old_name.yml"
    assert old_path.exists()

    # Rename entry AND change primary tag
    renamed_data = initial_data.copy()
    renamed_data["name"] = "new_name"
    renamed_data["tags"] = ["equilibrium", "spatial-profile"]

    catalog = StandardNameCatalog(root)  # Reload
    uow = catalog.start_uow()
    renamed_model = create_standard_name_entry(renamed_data)
    uow.rename("old_name", renamed_model)
    uow.commit()

    # Verify file moved to new directory with new name
    new_path = root / "equilibrium" / "new_name.yml"
    assert not old_path.exists(), "Old file should be deleted"
    assert new_path.exists(), "New file should exist in new directory"

    # Ensure no orphaned files
    fundamental_files = list((root / "fundamental").rglob("*.yml"))
    assert len(fundamental_files) == 0, "No files should remain in fundamental/"

    all_files = list(root.rglob("*.yml"))
    assert len(all_files) == 1, f"Should have exactly 1 file, found {len(all_files)}"
