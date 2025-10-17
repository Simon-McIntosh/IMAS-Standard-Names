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

    StandardNameCatalog("equilibrium")          # exact directory name
    StandardNameCatalog("equi*")                # wildcard
    StandardNameCatalog("profiles/density*")    # nested path pattern

If no directory matches, a ``ValueError`` is raised to fail fast.
"""

from __future__ import annotations

from pathlib import Path

from .database.readwrite import CatalogReadWrite
from .models import StandardNameEntry
from .ordering import ordered_models
from .paths import CatalogPaths
from .services import row_to_model
from .unit_of_work import UnitOfWork
from .yaml_store import YamlStore


class StandardNameCatalog:
    def __init__(self, root: str | Path | None = None):
        # Map None -> packaged standard_names root for historical semantics.
        paths = CatalogPaths("standard_names" if root is None else root)
        self.paths = paths
        resolved_root = paths.yaml_path
        self.store = YamlStore(resolved_root)
        self.catalog = CatalogReadWrite()
        models = self.store.load()
        # Use centralized dependency ordering (see ordering.py) so that
        # component scalars, bases, and provenance dependencies are guaranteed
        # to precede vectors / derived entries (avoids FK violations).
        for m in ordered_models(models):
            self.catalog.insert(m)
        self._active_uow: UnitOfWork | None = None

    # Basic queries -----------------------------------------------------------
    def get(self, name: str) -> StandardNameEntry | None:
        row = self.catalog.conn.execute(
            "SELECT * FROM standard_name WHERE name=?", (name,)
        ).fetchone()
        return row_to_model(self.catalog.conn, row) if row else None

    def list(self) -> list[StandardNameEntry]:
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

    def reload_from_disk(self):
        """Reload the catalog from YAML files on disk.

        This clears the in-memory SQLite database and repopulates it from
        the current state of YAML files. Used after commit to sync the
        in-memory state with persisted changes.
        """

        # Clear existing data
        for table in [
            "provenance_operator",
            "provenance_reduction",
            "provenance_expression_dependency",
            "provenance_expression",
            "tag",
            "link",
            "fts_standard_name",
            "standard_name",
        ]:
            self.catalog.conn.execute(f"DELETE FROM {table}")
        self.catalog.conn.commit()

        # Reload from YAML
        models = self.store.load()
        for m in ordered_models(models):
            self.catalog.insert(m)

        # Ensure all changes are committed
        self.catalog.conn.commit()

    # Internal helper for UnitOfWork
    def _row_to_model(self, row):
        return row_to_model(self.catalog.conn, row)


__all__ = ["StandardNameCatalog", "UnitOfWork"]
