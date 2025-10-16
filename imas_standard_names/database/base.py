"""Catalog base classes (SQLite-backed) for Standard Names.

Provides shared FTS search + row->model reconstruction helpers.
"""

from __future__ import annotations

import sqlite3

from ..models import StandardNameEntry
from ..services import row_to_model


class CatalogBase:
    """Abstract base over a SQLite connection (no mutation semantics)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    # ---------------------------- Query API ----------------------------
    def get(self, name: str) -> StandardNameEntry | None:
        row = self.conn.execute(
            "SELECT * FROM standard_name WHERE name=?", (name,)
        ).fetchone()
        return row_to_model(self.conn, row) if row else None

    def list(self) -> list[StandardNameEntry]:
        rows = self.conn.execute("SELECT * FROM standard_name").fetchall()
        return [row_to_model(self.conn, r) for r in rows]

    def search(self, query: str, limit: int = 20, with_meta: bool = False):
        cur = self.conn.cursor()
        try:
            # Only highlight documentation (long form). We intentionally drop
            # description highlighting to keep that field pristine and reduce
            # noisy HTML tags for downstream LLM/tooling use.
            cur.execute(
                "SELECT name, bm25(fts_standard_name) AS score, "
                "highlight(fts_standard_name,2,'<b>','</b>') AS h_doc "
                "FROM fts_standard_name WHERE fts_standard_name MATCH ? "
                "ORDER BY score LIMIT ?",
                (query, limit),
            )
            rows = cur.fetchall()
        except Exception:  # fallback substring scan
            q = query.lower()
            base = []
            for r in self.conn.execute(
                "SELECT name, description, documentation FROM standard_name"
            ).fetchall():
                blob = (
                    r["name"]
                    + " "
                    + (r["description"] or "")
                    + " "
                    + (r["documentation"] or "")
                ).lower()
                if q in blob:
                    # Fallback: no highlighting available in substring mode
                    base.append((r["name"], None, None))
            rows = base[:limit]

        # Fast path: names only
        if not with_meta:
            return [r[0] for r in rows]

        # Collect names for bulk hydration
        names = [r[0] for r in rows]
        if not names:
            return []
        placeholders = ",".join(["?"] * len(names))
        full_rows = self.conn.execute(
            f"SELECT * FROM standard_name WHERE name IN ({placeholders})", names
        ).fetchall()
        model_map = {
            fr["name"]: row_to_model(self.conn, fr).model_dump(exclude_none=True)
            for fr in full_rows
        }

        results = []
        for tup in rows:
            # FTS path: (name, score, h_doc); fallback: (name, None, None)
            name, score, h_doc = tup
            results.append(
                {
                    "name": name,
                    "score": score,
                    "highlight_documentation": h_doc,
                    "standard_name": model_map.get(name),
                }
            )
        return results

    # Mutation guard placeholders; subclasses may override
    def insert(self, *_args, **_kwargs) -> None:  # pragma: no cover
        raise RuntimeError(
            "CatalogBase is read-only; use CatalogReadWrite for mutations"
        )
        return None

    def delete(self, *_args, **_kwargs) -> None:  # pragma: no cover
        raise RuntimeError(
            "CatalogBase is read-only; use CatalogReadWrite for mutations"
        )
        return None


__all__ = ["CatalogBase"]
