"""Read-only on-disk SQLite catalog (snapshot consumer)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .base import CatalogBase


class CatalogRead(CatalogBase):
    def __init__(self, db_path: Path):
        dbp = Path(db_path)
        if not dbp.exists():
            raise FileNotFoundError(f"SQLite snapshot not found: {dbp}")
        # Open in read-only mode (URI) to guard against accidental writes
        conn = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
        super().__init__(conn)

    # Explicitly block mutation (already guarded in base, but clearer error context)
    def insert(self, *_, **__):  # pragma: no cover
        raise RuntimeError(
            "CatalogRead is read-only; export a new snapshot to change contents"
        )

    def delete(self, *_, **__):  # pragma: no cover
        raise RuntimeError(
            "CatalogRead is read-only; export a new snapshot to change contents"
        )


__all__ = ["CatalogRead"]
