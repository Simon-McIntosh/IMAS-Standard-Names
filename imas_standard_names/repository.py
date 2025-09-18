"""Repository facade wired to modular components.

Enhancements
------------
* ``root`` parameter now accepts ``None | str | Path``.
    - ``None`` -> resolves to the packaged resources directory
        ``imas_standard_names/resources/standard_names``.
    - ``str`` -> if it refers to an existing directory (absolute or relative)
        it's used directly. Otherwise it is treated as a glob-style *pattern*
        searched within the packaged ``standard_names`` tree and the *first*
        matching directory (sorted lexicographically) is used.
    - ``Path`` -> used as-is.

Pattern Matching Semantics
--------------------------
The pattern is matched against the POSIX relative path of each directory
under ``standard_names`` (recursive) using :mod:`fnmatch` rules. Examples::

        StandardNameRepository("equilibrium")          # exact directory name
        StandardNameRepository("equi*")                # wildcard
        StandardNameRepository("profiles/density*")    # nested path pattern

If no directory matches, a ``ValueError`` is raised to fail fast.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from .schema import StandardName
from .catalog.sqlite_rw import CatalogReadWrite
from .yaml_store import YamlStore
from .services import row_to_model
from .uow import UnitOfWork
from .paths import resolve_root
from .ordering import ordered_models


class StandardNameRepository:
    def __init__(self, root: Union[str, Path, None] = None):
        resolved_root = resolve_root(root)
        self.store = YamlStore(resolved_root)
        self.catalog = CatalogReadWrite()
        models = self.store.load()
        # Use centralized dependency ordering (see ordering.py) so that
        # component scalars, bases, and provenance dependencies are guaranteed
        # to precede vectors / derived entries (avoids FK violations).
        for m in ordered_models(models):
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

    def __len__(self) -> int:  # pragma: no cover - trivial
        """Return the number of standard names.

        Uses ``SELECT COUNT(*)`` for O(1) aggregation in SQLite rather than
        materializing rows. Chosen over ``len(self.list())`` for efficiency.
        """
        (count,) = self.catalog.conn.execute(
            "SELECT COUNT(*) FROM standard_name"
        ).fetchone()
        return count

    def list_names(self) -> list[str]:
        """Return all standard name identifiers without hydrating full models.

        Selecting only the ``name`` column avoids unnecessary I/O and object
        construction overhead compared to :meth:`list`.
        """
        rows = self.catalog.conn.execute(
            "SELECT name FROM standard_name ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def exists(self, name: str) -> bool:
        """Return ``True`` if a standard name exists, else ``False``.

        Uses an index/PK probe with ``SELECT 1 ... LIMIT 1`` for minimal work.
        """
        row = self.catalog.conn.execute(
            "SELECT 1 FROM standard_name WHERE name=? LIMIT 1", (name,)
        ).fetchone()
        return row is not None

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
