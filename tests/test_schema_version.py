"""Tests for catalog schema version compatibility checking."""

import logging
import sqlite3

import pytest

from imas_standard_names.database.build import build_catalog
from imas_standard_names.database.read import (
    CatalogRead,
    SchemaVersionError,
    _parse_version,
)
from imas_standard_names.database.readwrite import (
    CATALOG_SCHEMA_VERSION,
    CatalogReadWrite,
)
from imas_standard_names.yaml_store import YamlStore


def test_schema_version_constant_format():
    """Schema version follows major.minor format."""
    major, minor = _parse_version(CATALOG_SCHEMA_VERSION)
    assert major >= 1
    assert minor >= 0


def test_parse_version():
    assert _parse_version("1.0") == (1, 0)
    assert _parse_version("2.3") == (2, 3)
    assert _parse_version("1") == (1, 0)


def test_parse_version_malformed():
    """Malformed version strings raise ValueError."""
    with pytest.raises(ValueError, match="Malformed schema version"):
        _parse_version("abc")

    with pytest.raises(ValueError, match="Malformed schema version"):
        _parse_version("")


def test_in_memory_catalog_has_schema_version():
    """CatalogReadWrite writes schema version to metadata table."""
    catalog = CatalogReadWrite()
    row = catalog.conn.execute(
        "SELECT value FROM catalog_metadata WHERE key = 'schema_version'"
    ).fetchone()
    assert row is not None
    assert row[0] == CATALOG_SCHEMA_VERSION


def test_build_catalog_writes_schema_version(tmp_path, example_scalars):
    """build_catalog writes schema_version and builder_version to catalog_metadata."""
    yaml_root = tmp_path / "standard_names"
    yaml_root.mkdir()

    store = YamlStore(yaml_root)
    for entry in example_scalars[:1]:
        store.write(entry)

    db_path = tmp_path / "catalog.db"
    build_catalog(yaml_root, db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    schema_row = conn.execute(
        "SELECT value FROM catalog_metadata WHERE key = 'schema_version'"
    ).fetchone()
    assert schema_row is not None
    assert schema_row[0] == CATALOG_SCHEMA_VERSION

    builder_row = conn.execute(
        "SELECT value FROM catalog_metadata WHERE key = 'builder_version'"
    ).fetchone()
    assert builder_row is not None
    assert builder_row[0]  # non-empty
    conn.close()


def test_catalog_read_accepts_compatible_version(tmp_path, example_scalars):
    """CatalogRead opens catalogs with matching schema version."""
    yaml_root = tmp_path / "standard_names"
    yaml_root.mkdir()

    store = YamlStore(yaml_root)
    for entry in example_scalars[:1]:
        store.write(entry)

    db_path = tmp_path / "catalog.db"
    build_catalog(yaml_root, db_path)

    catalog = CatalogRead(db_path)
    assert catalog.list() is not None


def test_catalog_read_rejects_major_version_mismatch(tmp_path, example_scalars):
    """CatalogRead raises SchemaVersionError for major version mismatch."""
    yaml_root = tmp_path / "standard_names"
    yaml_root.mkdir()

    store = YamlStore(yaml_root)
    for entry in example_scalars[:1]:
        store.write(entry)

    db_path = tmp_path / "catalog.db"
    build_catalog(yaml_root, db_path)

    # Tamper with the schema version to simulate a major version mismatch
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE catalog_metadata SET value = '99.0' WHERE key = 'schema_version'"
    )
    conn.commit()
    conn.close()

    with pytest.raises(SchemaVersionError, match="major=99"):
        CatalogRead(db_path)


def test_catalog_read_warns_for_minor_version_ahead(tmp_path, example_scalars, caplog):
    """CatalogRead warns when catalog minor version exceeds reader."""
    yaml_root = tmp_path / "standard_names"
    yaml_root.mkdir()

    store = YamlStore(yaml_root)
    for entry in example_scalars[:1]:
        store.write(entry)

    db_path = tmp_path / "catalog.db"
    build_catalog(yaml_root, db_path)

    # Set minor version ahead of reader
    reader_major, _ = _parse_version(CATALOG_SCHEMA_VERSION)
    future_version = f"{reader_major}.99"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE catalog_metadata SET value = ? WHERE key = 'schema_version'",
        (future_version,),
    )
    conn.commit()
    conn.close()

    with caplog.at_level(logging.WARNING):
        catalog = CatalogRead(db_path)
        assert catalog.list() is not None

    assert any("newer than reader" in msg for msg in caplog.messages)


def test_catalog_read_handles_missing_metadata_table(tmp_path, caplog):
    """CatalogRead handles pre-versioning catalogs gracefully."""
    db_path = tmp_path / "old_catalog.db"

    # Create a minimal catalog without the catalog_metadata table
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE standard_name (name TEXT PRIMARY KEY, kind TEXT NOT NULL, "
        "status TEXT NOT NULL, unit TEXT, description TEXT NOT NULL, "
        "documentation TEXT, validity_domain TEXT, deprecates TEXT, "
        "superseded_by TEXT, is_dimensionless INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "CREATE VIRTUAL TABLE fts_standard_name "
        "USING fts5(name UNINDEXED, description, documentation)"
    )
    conn.commit()
    conn.close()

    with caplog.at_level(logging.WARNING):
        catalog = CatalogRead(db_path)
        assert catalog.list() == []

    assert any("no catalog_metadata table" in msg for msg in caplog.messages)


def test_catalog_read_handles_missing_schema_version_key(tmp_path, caplog):
    """CatalogRead handles catalogs with metadata table but no schema_version."""
    db_path = tmp_path / "partial_catalog.db"

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE catalog_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE standard_name (name TEXT PRIMARY KEY, kind TEXT NOT NULL, "
        "status TEXT NOT NULL, unit TEXT, description TEXT NOT NULL, "
        "documentation TEXT, validity_domain TEXT, deprecates TEXT, "
        "superseded_by TEXT, is_dimensionless INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "CREATE VIRTUAL TABLE fts_standard_name "
        "USING fts5(name UNINDEXED, description, documentation)"
    )
    conn.commit()
    conn.close()

    with caplog.at_level(logging.WARNING):
        catalog = CatalogRead(db_path)
        assert catalog.list() == []

    assert any("no schema_version metadata" in msg for msg in caplog.messages)


def test_catalog_read_handles_malformed_version_in_db(
    tmp_path, example_scalars, caplog
):
    """CatalogRead warns on malformed version strings rather than crashing."""
    yaml_root = tmp_path / "standard_names"
    yaml_root.mkdir()

    store = YamlStore(yaml_root)
    for entry in example_scalars[:1]:
        store.write(entry)

    db_path = tmp_path / "catalog.db"
    build_catalog(yaml_root, db_path)

    # Tamper with schema version to be malformed
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE catalog_metadata SET value = 'garbage' WHERE key = 'schema_version'"
    )
    conn.commit()
    conn.close()

    with caplog.at_level(logging.WARNING):
        catalog = CatalogRead(db_path)
        assert catalog.list() is not None

    assert any("malformed" in msg.lower() for msg in caplog.messages)
