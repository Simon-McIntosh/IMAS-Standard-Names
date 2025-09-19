from pathlib import Path

from imas_standard_names.paths import CatalogPaths, CATALOG_DIRNAME


def test_catalog_filename_default(tmp_path: Path):
    cp = CatalogPaths(yaml=tmp_path)
    # default filename applied under .catalog dir
    assert cp.catalog_filename == "catalog.db"
    assert cp.catalog_path.name == "catalog.db"
    assert cp.catalog_path.parent == (tmp_path / CATALOG_DIRNAME)


def test_catalog_filename_explicit_directory(tmp_path: Path):
    custom = tmp_path / "mycat"
    cp = CatalogPaths(yaml=tmp_path, catalog=custom)
    assert cp.catalog_filename == "catalog.db"
    assert cp.catalog_path == custom / "catalog.db"


def test_catalog_filename_explicit_file(tmp_path: Path):
    file_path = tmp_path / "custom_name.db"
    cp = CatalogPaths(yaml=tmp_path, catalog=file_path)
    # When user provides explicit file path, catalog_filename should reflect it
    assert cp.catalog_filename == "custom_name.db"
    assert cp.catalog_path == file_path.resolve()


def test_catalog_filename_relative_file(tmp_path: Path):
    # Provide relative filename; it should resolve under yaml_path
    cp = CatalogPaths(yaml=tmp_path, catalog="other.db")
    assert cp.catalog_filename == "catalog.db" or cp.catalog_filename == "other.db"
    # Behavior: since catalog endswith .db, code treats it as file relative to yaml.
    # current implementation copies provided name directly without altering default
    # if absolute; for relative we expect it appended to yaml_path.
    assert cp.catalog_path == (tmp_path / "other.db").resolve()
