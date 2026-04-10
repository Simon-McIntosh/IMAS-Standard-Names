"""Test that changing physics_domain moves file to new directory."""

from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog


def test_modify_entry_with_physics_domain_change_deletes_old_file(tmp_path):
    """When physics_domain changes via modify, old file should be deleted."""
    # Setup
    root = tmp_path / "catalog"
    root.mkdir()

    # Create initial entry with "general" physics_domain
    initial_data = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity for physics domain change.",
        "documentation": "Test quantity for physics domain change validation.",
        "physics_domain": "general",
        "tags": ["spatial-profile"],
        "unit": "m",
        "status": "draft",
    }

    catalog = StandardNameCatalog(root)
    uow = catalog.start_uow()
    model = create_standard_name_entry(initial_data)
    uow.add(model)
    uow.commit()

    # Verify initial file location
    general_path = root / "general" / "test_quantity.yml"
    equilibrium_path = root / "equilibrium" / "test_quantity.yml"
    assert general_path.exists(), "Initial file should exist in general/"
    assert not equilibrium_path.exists(), "File should not yet exist in equilibrium/"

    # Modify entry to change physics_domain from "general" to "equilibrium"
    modified_data = initial_data.copy()
    modified_data["physics_domain"] = "equilibrium"

    catalog = StandardNameCatalog(root)  # Reload catalog
    uow = catalog.start_uow()
    modified_model = create_standard_name_entry(modified_data)
    uow.update("test_quantity", modified_model)
    uow.commit()

    # Verify file has moved
    assert not general_path.exists(), (
        "Old file in general/ should be deleted after physics_domain change"
    )
    assert equilibrium_path.exists(), (
        "New file should exist in equilibrium/ after physics_domain change"
    )

    # Verify only one file exists
    all_files = list(root.rglob("test_quantity.yml"))
    assert len(all_files) == 1, (
        f"Expected exactly 1 file, found {len(all_files)}: {all_files}"
    )
    assert all_files[0] == equilibrium_path


def test_rename_entry_preserves_physics_domain_directory(tmp_path):
    """Renaming an entry should keep it in the same physics_domain directory."""
    # Setup
    root = tmp_path / "catalog"
    root.mkdir()

    # Create initial entry
    initial_data = {
        "name": "old_name",
        "kind": "scalar",
        "description": "Test entry for rename.",
        "documentation": "Test entry for rename validation.",
        "physics_domain": "equilibrium",
        "tags": ["spatial-profile"],
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


def test_rename_with_physics_domain_change_moves_file(tmp_path):
    """Renaming and changing physics_domain should move file to new directory."""
    # Setup
    root = tmp_path / "catalog"
    root.mkdir()

    # Create initial entry
    initial_data = {
        "name": "old_name",
        "kind": "scalar",
        "description": "Test entry for rename with domain change.",
        "documentation": "Test entry for rename with domain change validation.",
        "physics_domain": "general",
        "tags": ["spatial-profile"],
        "unit": "m",
        "status": "draft",
    }

    catalog = StandardNameCatalog(root)
    uow = catalog.start_uow()
    model = create_standard_name_entry(initial_data)
    uow.add(model)
    uow.commit()

    # Verify initial location
    old_path = root / "general" / "old_name.yml"
    assert old_path.exists()

    # Rename entry AND change physics_domain
    renamed_data = initial_data.copy()
    renamed_data["name"] = "new_name"
    renamed_data["physics_domain"] = "equilibrium"

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
    general_files = list((root / "general").rglob("*.yml"))
    assert len(general_files) == 0, "No files should remain in general/"

    all_files = list(root.rglob("*.yml"))
    assert len(all_files) == 1, f"Should have exactly 1 file, found {len(all_files)}"
