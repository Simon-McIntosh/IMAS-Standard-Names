"""Validate bundled standard_name_examples against current grammar and schema.

This test catches drift between the bundled example entries and the
current grammar/validation rules, ensuring examples stay valid as the
project evolves.
"""

import importlib.resources as ir
from pathlib import Path

import pytest

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.yaml_store import YamlStore


def test_bundled_examples_load_in_strict_mode():
    """All bundled example YAML files must load without permissive mode."""
    files_obj = ir.files("imas_standard_names") / "resources" / "standard_name_examples"
    with ir.as_file(files_obj) as examples_path:
        examples_path = Path(examples_path)
        if not examples_path.exists():
            pytest.skip("No bundled examples directory found")

        store = YamlStore(examples_path, permissive=False)
        yaml_files = store.yaml_files()
        if not yaml_files:
            pytest.skip("No YAML files in bundled examples")

        # Load in strict mode — any validation error will raise
        models = store.load()
        assert len(models) > 0, "Expected at least one valid example entry"


def test_bundled_examples_catalog_loads():
    """Bundled examples can initialize a full StandardNameCatalog."""
    files_obj = ir.files("imas_standard_names") / "resources" / "standard_name_examples"
    with ir.as_file(files_obj) as examples_path:
        examples_path = Path(examples_path)
        if not examples_path.exists():
            pytest.skip("No bundled examples directory found")

        # Load without permissive mode to catch schema drift
        catalog = StandardNameCatalog(root=examples_path, permissive=False)
        entries = catalog.list()
        assert len(entries) > 0, "Expected at least one entry in examples catalog"

        # Verify each entry has required fields
        for entry in entries:
            assert entry.name, f"Entry missing name: {entry}"
            assert entry.description, f"Entry {entry.name} missing description"
            assert entry.physics_domain, f"Entry {entry.name} missing physics_domain"
