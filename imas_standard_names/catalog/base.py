"""Catalog base classes (SQLite-backed) for Standard Names.

Provides shared FTS search + row->model reconstruction helpers.
"""

from __future__ import annotations

from typing import List, Optional
import sqlite3

from ..schema import StandardName
from ..services import row_to_model


class CatalogBase:
    """Abstract base over a SQLite connection (no mutation semantics)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    # ---------------------------- Query API ----------------------------
    def get(self, name: str) -> Optional[StandardName]:
        row = self.conn.execute(
            "SELECT * FROM standard_name WHERE name=?", (name,)
        ).fetchone()
        return row_to_model(self.conn, row) if row else None

    def list(self) -> List[StandardName]:
        rows = self.conn.execute("SELECT * FROM standard_name").fetchall()
        return [row_to_model(self.conn, r) for r in rows]

    def search(self, query: str, limit: int = 20, with_meta: bool = False):
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT name, bm25(fts_standard_name) AS score, highlight(fts_standard_name,1,'<b>','</b>') AS h_desc, highlight(fts_standard_name,2,'<b>','</b>') AS h_doc FROM fts_standard_name WHERE fts_standard_name MATCH ? ORDER BY score LIMIT ?",
                (query, limit),
            )
            rows = cur.fetchall()
        except Exception:  # fallback substring scan
            q = query.lower()
            base = []
            for r in self.conn.execute(
                "SELECT name, description, documentation FROM standard_name"
            ).fetchall():
                blob = (r["name"] + " " + (r["description"] or "")).lower()
                if q in blob:
                    base.append((r["name"], None, r["description"], r["documentation"]))
            rows = base[:limit]
        if with_meta:
            return [
                {
                    "name": name,
                    "score": score,
                    "highlight_description": h_desc,
                    "highlight_documentation": h_doc,
                }
                for name, score, h_desc, h_doc in rows
            ]
        return [n for (n, *_rest) in rows]

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
