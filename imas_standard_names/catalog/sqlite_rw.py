"""Writable in-memory SQLite catalog (authoring workflow)."""

from __future__ import annotations

import sqlite3
import json
import os
import logging
from typing import Iterable, List, Tuple

from .base import CatalogBase
from ..schema import StandardName

DDL = [
    "PRAGMA foreign_keys=ON;",
    "CREATE TABLE standard_name ( name TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL, unit TEXT, frame TEXT, description TEXT NOT NULL, documentation TEXT, validity_domain TEXT, deprecates TEXT, superseded_by TEXT, is_dimensionless INTEGER NOT NULL DEFAULT 0 );",
    "CREATE TABLE provenance_operator ( name TEXT PRIMARY KEY REFERENCES standard_name(name) ON DELETE CASCADE, operator_chain TEXT NOT NULL, base TEXT NOT NULL, operator_id TEXT );",
    "CREATE TABLE provenance_reduction ( name TEXT PRIMARY KEY REFERENCES standard_name(name) ON DELETE CASCADE, reduction TEXT NOT NULL, domain TEXT NOT NULL, base TEXT NOT NULL );",
    "CREATE TABLE provenance_expression ( name TEXT PRIMARY KEY REFERENCES standard_name(name) ON DELETE CASCADE, expression TEXT NOT NULL );",
    "CREATE TABLE provenance_expression_dependency ( name TEXT NOT NULL REFERENCES provenance_expression(name) ON DELETE CASCADE, dependency TEXT NOT NULL REFERENCES standard_name(name), PRIMARY KEY(name,dependency) );",
    "CREATE TABLE vector_component ( vector_name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE, axis TEXT NOT NULL, component_name TEXT NOT NULL REFERENCES standard_name(name), PRIMARY KEY(vector_name,axis) );",
    "CREATE TABLE tag ( name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE, tag TEXT NOT NULL, PRIMARY KEY(name,tag));",
    "CREATE TABLE link ( name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE, link TEXT NOT NULL, PRIMARY KEY(name,link));",
    "CREATE VIRTUAL TABLE fts_standard_name USING fts5(name UNINDEXED, description, documentation);",
]


logger = logging.getLogger("imas_standard_names.catalog")


def _configure_logging():  # lightweight, idempotent
    if getattr(_configure_logging, "_done", False):  # type: ignore[attr-defined]
        return
    level_name = os.getenv("IMAS_SN_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(level=level, format="[%(levelname)s] %(name)s: %(message)s")
    _configure_logging._done = True  # type: ignore[attr-defined]


class CatalogReadWrite(CatalogBase):
    def __init__(self):
        _configure_logging()
        conn = sqlite3.connect(":memory:")
        super().__init__(conn)
        cur = self.conn.cursor()
        for stmt in DDL:
            cur.execute(stmt)
        self.conn.commit()
        logger.debug("Initialized in-memory writable catalog with schema")

    def load_models(self, models: Iterable[StandardName]):
        for m in models:
            self.insert(m)

    def _diagnose_fk(self) -> List[Tuple[str, int, str, int]]:
        cur = self.conn.cursor()
        cur.execute("PRAGMA foreign_key_check;")
        rows = cur.fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in rows]

    def insert(self, m: StandardName):  # override guard
        logger.debug(
            "Inserting standard name '%s' (kind=%s)", m.name, getattr(m, "kind", "?")
        )
        c = self.conn.cursor()
        try:
            c.execute(
                "INSERT INTO standard_name(name,kind,status,unit,frame,description,documentation,validity_domain,deprecates,superseded_by,is_dimensionless) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    m.name,
                    getattr(m, "kind", ""),
                    getattr(m, "status", "draft"),
                    getattr(m, "unit", "") or None,
                    getattr(m, "frame", None),
                    m.description,
                    getattr(m, "documentation", "") or None,
                    getattr(m, "validity_domain", "") or None,
                    getattr(m, "deprecates", "") or None,
                    getattr(m, "superseded_by", "") or None,
                    1 if getattr(m, "is_dimensionless", False) else 0,
                ),
            )
            prov = getattr(m, "provenance", None)
            if prov:
                mode = getattr(prov, "mode", None)
                if mode == "operator":
                    c.execute(
                        "INSERT INTO provenance_operator(name, operator_chain, base, operator_id) VALUES (?,?,?,?)",
                        (
                            m.name,
                            json.dumps(getattr(prov, "operators", [])),
                            getattr(prov, "base", None),
                            getattr(prov, "operator_id", None),
                        ),
                    )
                elif mode == "reduction":
                    c.execute(
                        "INSERT INTO provenance_reduction(name, reduction, domain, base) VALUES (?,?,?,?)",
                        (
                            m.name,
                            getattr(prov, "reduction", None),
                            getattr(prov, "domain", None),
                            getattr(prov, "base", None),
                        ),
                    )
                elif mode == "expression":
                    c.execute(
                        "INSERT INTO provenance_expression(name, expression) VALUES (?,?)",
                        (m.name, getattr(prov, "expression", None)),
                    )
                    for dep in getattr(prov, "dependencies", []):
                        c.execute(
                            "INSERT INTO provenance_expression_dependency(name, dependency) VALUES (?,?)",
                            (m.name, dep),
                        )
            if getattr(m, "kind", "").endswith("vector"):
                for axis, comp in (getattr(m, "components", {}) or {}).items():
                    c.execute(
                        "INSERT INTO vector_component(vector_name, axis, component_name) VALUES (?,?,?)",
                        (m.name, axis, comp),
                    )
            for t in getattr(m, "tags", []) or []:
                c.execute("INSERT INTO tag(name, tag) VALUES (?,?)", (m.name, t))
            for link in getattr(m, "links", []) or []:
                c.execute("INSERT INTO link(name, link) VALUES (?,?)", (m.name, link))
            c.execute(
                "INSERT INTO fts_standard_name(name, description, documentation) VALUES (?,?,?)",
                (m.name, m.description, getattr(m, "documentation", "") or ""),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as e:  # enhance FK diagnostics
            failed = self._diagnose_fk()
            if failed:
                details_lines = []
                for table, rowid, parent, fkid in failed:
                    ref_val = None
                    try:
                        if table == "vector_component":
                            r = self.conn.execute(
                                "SELECT vector_name, axis, component_name FROM vector_component WHERE rowid=?",
                                (rowid,),
                            ).fetchone()
                            if r:
                                ref_val = r[2]
                        elif table == "provenance_expression_dependency":
                            r = self.conn.execute(
                                "SELECT dependency FROM provenance_expression_dependency WHERE rowid=?",
                                (rowid,),
                            ).fetchone()
                            if r:
                                ref_val = r[0]
                    except Exception:  # pragma: no cover - best effort
                        pass
                    details_lines.append(
                        f"table={table} rowid={rowid} parent_table={parent} fkid={fkid}"
                        + (f" missing_ref='{ref_val}'" if ref_val else "")
                    )
                msg = (
                    f"Foreign key constraint failed while inserting '{m.name}'.\n"
                    + "\n".join(details_lines)
                    + "\nHint: This often means referenced component or dependency names were not inserted yet."
                )
                logger.error(msg)
                raise sqlite3.IntegrityError(msg) from e
            # If we reach here PRAGMA returned nothing (common when the failing
            # statement itself violates FK). Provide heuristic for vectors.
            if getattr(m, "kind", "").endswith("vector"):
                missing = []
                for comp in (getattr(m, "components", {}) or {}).values():
                    row = self.conn.execute(
                        "SELECT 1 FROM standard_name WHERE name=?", (comp,)
                    ).fetchone()
                    if not row:
                        missing.append(comp)
                if missing:
                    msg = (
                        f"Foreign key constraint failed while inserting vector '{m.name}'.\n"
                        f"Missing component standard_name rows: {', '.join(missing)}\n"
                        "Insert the component scalar definitions before the vector or reorder YAML files."
                    )
                    logger.error(msg)
                    raise sqlite3.IntegrityError(msg) from e
            raise

    def get_row(self, name: str):
        return self.conn.execute(
            "SELECT * FROM standard_name WHERE name=?", (name,)
        ).fetchone()

    def list_rows(self):
        return self.conn.execute("SELECT * FROM standard_name").fetchall()

    def delete(self, name: str):  # override guard
        c = self.conn.cursor()
        for table, col in [
            ("provenance_operator", "name"),
            ("provenance_reduction", "name"),
            ("provenance_expression_dependency", "name"),
            ("provenance_expression", "name"),
            ("vector_component", "vector_name"),
            ("tag", "name"),
            ("link", "name"),
            ("fts_standard_name", "name"),
            ("standard_name", "name"),
        ]:
            c.execute(f"DELETE FROM {table} WHERE {col}=?", (name,))
        self.conn.commit()


__all__ = ["CatalogReadWrite", "DDL"]
