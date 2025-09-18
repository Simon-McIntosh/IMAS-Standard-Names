from __future__ import annotations
from pathlib import Path
import sqlite3

from imas_standard_names.storage.sqlite import (
    build_sqlite_catalog,
    SqliteStandardNameRepository,
)
from imas_standard_names.repositories import YamlStandardNameRepository
from imas_standard_names.catalog.catalog import load_catalog

from imas_standard_names import schema


def _make_simple(tmp: Path):
    (tmp / "a.yml").write_text(
        "name: a\nkind: scalar\nstatus: active\nunit: keV\ndescription: A.\n"
    )
    (tmp / "b.yml").write_text(
        "name: b\nkind: scalar\nstatus: active\nunit: keV\ndescription: B.\n"
    )


def test_in_memory_clone_and_writable_ops(tmp_path: Path):
    _make_simple(tmp_path)
    # build artifact
    entries = {e.name: e for e in YamlStandardNameRepository(tmp_path).list()}
    db_path = tmp_path / "artifacts" / "catalog.db"
    build_sqlite_catalog(entries, db_path)  # type: ignore[arg-type]
    # load smart (will mem-clone by default)
    cat = load_catalog(tmp_path, db_path=db_path)
    assert cat.source == "sqlite-mem"
    # Open a direct in-memory clone for writable operations
    file_conn = sqlite3.connect(db_path)
    mem_conn = sqlite3.connect(":memory:")
    file_conn.backup(mem_conn)
    file_conn.close()
    repo = SqliteStandardNameRepository.from_connection(
        mem_conn, writable=True, revalidate=False
    )
    # Add new entry
    new_model = schema.create_standard_name(
        {
            "name": "c",
            "kind": "scalar",
            "status": "draft",
            "unit": "keV",
            "description": "C entry.",
        }
    )
    repo.add(new_model)
    assert repo.get("c") is not None
    # Ensure disk artifact not changed
    disk_conn = sqlite3.connect(db_path)
    disk_row = disk_conn.execute(
        "SELECT name FROM standard_name WHERE name='c'"
    ).fetchone()
    assert disk_row is None
    disk_conn.close()
    # Update existing
    updated = schema.create_standard_name(
        {
            "name": "a",
            "kind": "scalar",
            "status": "active",
            "unit": "keV",
            "description": "A updated.",
        }
    )
    repo.update("a", updated)
    a_obj = repo.get("a")
    assert a_obj is not None
    assert "updated" in a_obj.description.lower()
    # Delete b
    repo.remove("b")
    assert repo.get("b") is None
