"""Repository facade wired to modular components (SQLiteCatalog + YamlStore + services + UnitOfWork)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .schema import StandardName
from .catalog.sqlite_rw import CatalogReadWrite
from .yaml_store import YamlStore
from .services import row_to_model
from .uow import UnitOfWork


class StandardNameRepository:
    def __init__(self, root: Path):
        self.store = YamlStore(root)
        self.catalog = CatalogReadWrite()
        models = self.store.load()
        for m in models:
            self.catalog.insert(m)
        self._active_uow: Optional[UnitOfWork] = None

    # Basic queries -----------------------------------------------------------
    def get(self, name: str) -> Optional[StandardName]:
        row = self.catalog.conn.execute(
            "SELECT * FROM standard_name WHERE name=?", (name,)
        ).fetchone()
        return row_to_model(self.catalog.conn, row) if row else None

    def list(self) -> List[StandardName]:
        rows = self.catalog.conn.execute("SELECT * FROM standard_name").fetchall()
        return [row_to_model(self.catalog.conn, r) for r in rows]

    def search(self, query: str, limit: int = 20, with_meta: bool = False):
        return self.catalog.search(query, limit=limit, with_meta=with_meta)

    # Unit of Work ------------------------------------------------------------
    def start_uow(self) -> UnitOfWork:
        if self._active_uow:
            raise RuntimeError("A UnitOfWork is already active")
        self._active_uow = UnitOfWork(self)
        return self._active_uow

    def _end_uow(self):  # internal callback from UnitOfWork
        self._active_uow = None

    # Internal helper for UnitOfWork
    def _row_to_model(self, row):  # compatibility shim
        return row_to_model(self.catalog.conn, row)


__all__ = ["StandardNameRepository", "UnitOfWork"]
