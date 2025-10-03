"""File-backed build catalog producing a definitive mirror of YAML.

CatalogBuild inherits from CatalogReadWrite but persists to an on-disk SQLite
database instead of :memory:. It is used only during the build step to create
an immutable artifact; subsequent consumers should open it with CatalogRead.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from ..ordering import ordered_models
from ..schema import StandardName
from ..yaml_store import YamlStore
from .sqlite_rw import DDL, CatalogReadWrite


class CatalogBuild(CatalogReadWrite):
    def __init__(self, db_path: Path, overwrite: bool = True):
        db_path = Path(db_path)
        if db_path.exists() and overwrite:
            db_path.unlink()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Replace in-memory connection with file connection + run DDL
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        for stmt in DDL:
            cur.execute(stmt)
        self.conn.commit()


def build_catalog(yaml_root: Path, db_path: Path, overwrite: bool = True) -> Path:
    """Build a definitive SQLite catalog file mirroring the YAML source.

    The function loads all YAML entries (validating structurally/semantically)
    then inserts them into a file-backed SQLite database using the canonical
    schema + FTS layout. Returns the db_path.
    """
    store = YamlStore(yaml_root)
    models: Iterable[StandardName] = store.load()
    builder = CatalogBuild(db_path, overwrite=overwrite)
    # Insert using dependency-safe ordering (vectors after components, derived after bases)
    for m in ordered_models(models):
        builder.insert(m)
    # Integrity tables -------------------------------------------------
    cur = builder.conn.cursor()
    cur.execute(
        "CREATE TABLE integrity (name TEXT PRIMARY KEY, rel_path TEXT NOT NULL, size INTEGER NOT NULL, mtime REAL NOT NULL, hash TEXT NOT NULL)"
    )
    cur.execute(
        "CREATE TABLE integrity_manifest (id INTEGER PRIMARY KEY CHECK (id=1), algo TEXT NOT NULL, file_count INTEGER NOT NULL, aggregate_hash TEXT NOT NULL)"
    )
    root = Path(yaml_root).resolve()
    digest_pairs = []  # (name, hash)
    for yf in sorted(store.yaml_files()):
        try:
            data = yf.read_bytes()
        except OSError:
            continue
        h = hashlib.blake2b(data, digest_size=16).hexdigest()
        st = yf.stat()
        rel_path = os.path.relpath(yf, root)
        # Attempt to derive name from filename (stem)
        name = yf.stem
        cur.execute(
            "INSERT INTO integrity(name, rel_path, size, mtime, hash) VALUES (?,?,?,?,?)",
            (name, rel_path, st.st_size, st.st_mtime, h),
        )
        digest_pairs.append((name, h))
    # Aggregate hash (sorted by name for determinism)
    agg_hasher = hashlib.blake2b(digest_size=16)
    for name, h in sorted(digest_pairs, key=lambda x: x[0]):
        agg_hasher.update(f"{name}:{h}".encode())
    aggregate_hash = agg_hasher.hexdigest()
    cur.execute(
        "INSERT INTO integrity_manifest(id, algo, file_count, aggregate_hash) VALUES (1,?,?,?)",
        ("blake2b-16", len(digest_pairs), aggregate_hash),
    )
    builder.conn.commit()
    builder.conn.close()
    return Path(db_path)


__all__ = ["CatalogBuild", "build_catalog"]
