from __future__ import annotations

from pathlib import Path

import pytest

from imas_standard_names.paths import (
    CATALOG_DIRNAME,
    STANDARD_NAMES_DIRNAME,
    CatalogPaths,
)


def test_catalog_paths_defaults():
    paths = CatalogPaths()
    assert paths.yaml_path.exists() and paths.yaml_path.is_dir()
    assert paths.yaml_path.name == STANDARD_NAMES_DIRNAME
    assert paths.catalog_path.parent.name == CATALOG_DIRNAME


def test_catalog_paths_existing_yaml(tmp_path: Path):
    custom = tmp_path / "my_names"
    custom.mkdir()
    paths = CatalogPaths(yaml=custom)
    assert paths.yaml_path == custom.resolve()


def test_catalog_paths_nonexistent_relative_dir():
    p = CatalogPaths(yaml="___no_such_directory_pattern___").yaml_path
    assert p.name == "___no_such_directory_pattern___"
    assert not p.exists()


def test_catalog_paths_wildcard_not_found_raises():
    with pytest.raises(ValueError):
        CatalogPaths(yaml="___no_such_directory_pattern___*")
