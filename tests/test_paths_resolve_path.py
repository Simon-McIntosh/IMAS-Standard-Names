from __future__ import annotations

from pathlib import Path

import pytest

from imas_standard_names.paths import (
    CATALOG_DIRNAME,
    CatalogPaths,
)


def test_catalog_paths_no_default_raises():
    """Test that CatalogPaths() without args raises when no standard_names dir exists."""
    with pytest.raises(FileNotFoundError, match="Standard names directory not found"):
        CatalogPaths()


def test_catalog_paths_existing_yaml(tmp_path: Path):
    custom = tmp_path / "my_names"
    custom.mkdir()
    paths = CatalogPaths(yaml=custom)
    assert paths.yaml_path == custom.resolve()


def test_catalog_paths_nonexistent_absolute_dir(tmp_path: Path):
    """Test that absolute path to nonexistent dir is allowed (for creation)."""
    nonexistent = tmp_path / "___no_such_directory___"
    p = CatalogPaths(yaml=nonexistent).yaml_path
    assert p.name == "___no_such_directory___"
    assert not p.exists()
