"""SQLite artifact builder and read-only repository for Standard Names.

This module replaces the JSON artifact writer. It builds a single
`catalog.db` file capturing all validated standard names plus provenance
and vector component relationships. The YAML per-file sources remain the
source of truth.

Schema (denormalized minimal):
  standard_name(name PK, kind, status, unit, frame, description, documentation,
                validity_domain, deprecates, superseded_by, is_dimensionless)
  provenance_operator(name FK->standard_name, operator_chain JSON text, base, operator_id)
  provenance_reduction(name FK->standard_name, reduction, domain, base)
  provenance_expression(name FK->standard_name, expression)
  provenance_expression_dependency(name, dependency)
  vector_component(vector_name, axis, component_name)
  tag(name, tag)
  link(name, link)
  meta(key,value)

FTS (full text search) is enabled by default via an FTS5 table
`fts_standard_name` indexing name, description and documentation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Dict, Any, Optional
import sqlite3
import json
from datetime import datetime, UTC

from ..schema import StandardNameBase, StandardName, create_standard_name
from types import SimpleNamespace

META_KEYS = {"version", "generated_at", "max_yaml_mtime", "schema_version"}
SCHEMA_VERSION = "1"

DDL = [
    "PRAGMA foreign_keys=ON;",
    "CREATE TABLE IF NOT EXISTS standard_name (\n"
    "  name TEXT PRIMARY KEY,\n"
    "  kind TEXT NOT NULL,\n"
    "  status TEXT NOT NULL,\n"
    "  unit TEXT,\n"
    "  frame TEXT,\n"
    "  description TEXT NOT NULL,\n"
    "  documentation TEXT,\n"
    "  validity_domain TEXT,\n"
    "  deprecates TEXT,\n"
    "  superseded_by TEXT,\n"
    "  is_dimensionless INTEGER NOT NULL DEFAULT 0\n"
    ");",
    "CREATE TABLE IF NOT EXISTS provenance_operator (\n"
    "  name TEXT PRIMARY KEY REFERENCES standard_name(name) ON DELETE CASCADE,\n"
    "  operator_chain TEXT NOT NULL,\n"
    "  base TEXT NOT NULL,\n"
    "  operator_id TEXT\n"
    ");",
    "CREATE TABLE IF NOT EXISTS provenance_reduction (\n"
    "  name TEXT PRIMARY KEY REFERENCES standard_name(name) ON DELETE CASCADE,\n"
    "  reduction TEXT NOT NULL,\n"
    "  domain TEXT NOT NULL,\n"
    "  base TEXT NOT NULL\n"
    ");",
    "CREATE TABLE IF NOT EXISTS provenance_expression (\n"
    "  name TEXT PRIMARY KEY REFERENCES standard_name(name) ON DELETE CASCADE,\n"
    "  expression TEXT NOT NULL\n"
    ");",
    "CREATE TABLE IF NOT EXISTS provenance_expression_dependency (\n"
    "  name TEXT NOT NULL REFERENCES provenance_expression(name) ON DELETE CASCADE,\n"
    "  dependency TEXT NOT NULL REFERENCES standard_name(name),\n"
    "  PRIMARY KEY(name, dependency)\n"
    ");",
    "CREATE TABLE IF NOT EXISTS vector_component (\n"
    "  vector_name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE,\n"
    "  axis TEXT NOT NULL,\n"
    "  component_name TEXT NOT NULL REFERENCES standard_name(name),\n"
    "  PRIMARY KEY(vector_name, axis)\n"
    ");",
    "CREATE TABLE IF NOT EXISTS tag (\n"
    "  name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE,\n"
    "  tag TEXT NOT NULL,\n"
    "  PRIMARY KEY(name, tag)\n"
    ");",
    "CREATE TABLE IF NOT EXISTS link (\n"
    "  name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE,\n"
    "  link TEXT NOT NULL,\n"
    "  PRIMARY KEY(name, link)\n"
    ");",
    "CREATE TABLE IF NOT EXISTS meta (\n"
    "  key TEXT PRIMARY KEY,\n"
    "  value TEXT NOT NULL\n"
    ");",
    # FTS5 virtual table (contentless for simplicity). Using simple tokenizer.
    "CREATE VIRTUAL TABLE IF NOT EXISTS fts_standard_name USING fts5(\n"
    "  name UNINDEXED,\n"
    "  description,\n"
    "  documentation\n"
    ");",
]


def _conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")  # readers scale
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def build_sqlite_catalog(
    entries: Dict[str, StandardNameBase],
    db_path: Path,
    *,
    version: str = "dev",
    max_yaml_mtime: float | None = None,
) -> Path:
    """Build (overwrite) a SQLite catalog artifact from validated entries."""
    tmp = db_path.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _conn(tmp)
    cur = conn.cursor()
    for stmt in DDL:
        cur.execute(stmt)

    # Bulk insert standard_name
    sn_rows = []
    for e in entries.values():
        sn_rows.append(
            (
                e.name,
                getattr(e, "kind", ""),
                getattr(e, "status", "draft"),
                getattr(e, "unit", "") or None,
                getattr(e, "frame", None),
                getattr(e, "description", ""),
                getattr(e, "documentation", "") or None,
                getattr(e, "validity_domain", "") or None,
                getattr(e, "deprecates", "") or None,
                getattr(e, "superseded_by", "") or None,
                1 if getattr(e, "is_dimensionless", False) else 0,
            )
        )
    cur.executemany(
        "INSERT INTO standard_name(name,kind,status,unit,frame,description,documentation,validity_domain,deprecates,superseded_by,is_dimensionless) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        sn_rows,
    )

    # Provenance tables
    for e in entries.values():
        prov = getattr(e, "provenance", None)
        if not prov:
            continue
        mode = getattr(prov, "mode", None)
        if mode == "operator":
            chain = json.dumps(getattr(prov, "operators", []))
            cur.execute(
                "INSERT INTO provenance_operator(name, operator_chain, base, operator_id) VALUES (?,?,?,?)",
                (
                    e.name,
                    chain,
                    getattr(prov, "base", None),
                    getattr(prov, "operator_id", None),
                ),
            )
        elif mode == "reduction":
            cur.execute(
                "INSERT INTO provenance_reduction(name, reduction, domain, base) VALUES (?,?,?,?)",
                (
                    e.name,
                    getattr(prov, "reduction", None),
                    getattr(prov, "domain", None),
                    getattr(prov, "base", None),
                ),
            )
        elif mode == "expression":
            cur.execute(
                "INSERT INTO provenance_expression(name, expression) VALUES (?,?)",
                (e.name, getattr(prov, "expression", None)),
            )
            for dep in getattr(prov, "dependencies", []):
                cur.execute(
                    "INSERT INTO provenance_expression_dependency(name, dependency) VALUES (?,?)",
                    (e.name, dep),
                )

    # Vector components
    for e in entries.values():
        if getattr(e, "kind", "").endswith("vector"):
            components = getattr(e, "components", {}) or {}
            for axis, comp in components.items():
                cur.execute(
                    "INSERT INTO vector_component(vector_name, axis, component_name) VALUES (?,?,?)",
                    (e.name, axis, comp),
                )

    # Tags & links
    for e in entries.values():
        for t in getattr(e, "tags", []) or []:
            cur.execute("INSERT INTO tag(name, tag) VALUES (?,?)", (e.name, t))
        for link_val in getattr(e, "links", []) or []:
            cur.execute("INSERT INTO link(name, link) VALUES (?,?)", (e.name, link_val))

    # FTS population
    fts_rows = [
        (
            e.name,
            getattr(e, "description", ""),
            getattr(e, "documentation", "") or "",
        )
        for e in entries.values()
    ]
    cur.executemany(
        "INSERT INTO fts_standard_name(name, description, documentation) VALUES (?,?,?)",
        fts_rows,
    )

    # Meta
    # Use timezone-aware UTC timestamp (avoid deprecated utcnow); normalize to trailing 'Z'
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    meta_rows = [
        ("version", version),
        ("generated_at", now),
        ("schema_version", SCHEMA_VERSION),
    ]
    if max_yaml_mtime is not None:
        meta_rows.append(("max_yaml_mtime", str(max_yaml_mtime)))
    cur.executemany("INSERT INTO meta(key,value) VALUES (?,?)", meta_rows)

    conn.commit()
    conn.close()
    tmp.replace(db_path)
    return db_path


class SqliteStandardNameRepository:
    """SQLite-backed repository for Standard Names.

    Default behaviour matches prior *read-only artifact* usage. A writable mode
    is permitted ONLY for ephemeral / in-memory connections that are explicitly
    constructed via `from_connection(..., writable=True)`.

    Rationale:
      - On-disk artifact (`catalog.db`) remains an immutable build product.
      - Interactive or test scenarios can copy the file into an in-memory SQLite
        database and perform rapid mutation without touching the canonical disk.

    Safety rules:
      - If `db_path` is set (file-based), write operations raise NotImplementedError.
      - If created with `from_connection(..., writable=True)` and the underlying
        database is in-memory (path empty according to PRAGMA database_list),
        add/update/remove are enabled.
    """

    def __init__(self, db_path: Path, *, revalidate: bool = True):
        self.db_path = db_path
        self.revalidate = revalidate
        self._conn: Optional[sqlite3.Connection] = None
        self._cache: Dict[str, StandardName] = {}
        self._writable: bool = False  # guarded
        self._in_memory: bool = False

    # ------------------------------------------------------------------
    # Alternate constructor for in-memory / external connections
    # ------------------------------------------------------------------
    @classmethod
    def from_connection(
        cls,
        conn: sqlite3.Connection,
        *,
        revalidate: bool = True,
        writable: bool = False,
    ) -> "SqliteStandardNameRepository":
        obj = cls.__new__(cls)  # bypass __init__ path-based
        obj.db_path = None  # type: ignore[assignment]
        obj.revalidate = revalidate
        obj._conn = conn
        try:
            obj._conn.row_factory = sqlite3.Row
        except Exception:
            pass
        obj._cache = {}
        obj._writable = False  # set after inspection
        # Determine if connection is in-memory (path empty in pragma list)
        try:
            rows = conn.execute("PRAGMA database_list").fetchall()
            # rows: seq, name, file
            file_paths = [r[2] for r in rows if r[1] == "main"]
            is_mem = (not file_paths) or (file_paths[0] in (None, "", ":memory:"))
        except Exception:
            is_mem = False
        obj._in_memory = is_mem
        if writable and is_mem:
            obj._writable = True
        elif writable and not is_mem:
            raise ValueError("Writable mode only supported for in-memory connections")
        return obj

    def _connect(self):
        if self._conn is None:
            self._conn = _conn(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get(self, name: str) -> Optional[StandardName]:
        if name in self._cache:
            return self._cache[name]
        row = (
            self._connect()
            .execute("SELECT * FROM standard_name WHERE name=?", (name,))
            .fetchone()
        )
        if not row:
            return None
        model = self._row_to_model(row)
        self._cache[name] = model
        return model

    def list(self) -> Iterable[StandardName]:
        rows = self._connect().execute("SELECT * FROM standard_name").fetchall()
        return [self._row_to_model(r) for r in rows]

    def exists(self, name: str) -> bool:
        row = (
            self._connect()
            .execute("SELECT 1 FROM standard_name WHERE name=?", (name,))
            .fetchone()
        )
        return bool(row)

    # Mutations are unsupported for artifact repository
    def add(self, model: StandardName):  # pragma: no cover - explicit
        if not self._writable:
            raise NotImplementedError(
                "Repository not writable (only in-memory copies can be mutated)"
            )
        self._ensure_schema()
        self._insert_model(model)
        self._cache.pop(model.name, None)

    def update(self, name: str, model: StandardName):  # pragma: no cover
        if not self._writable:
            raise NotImplementedError(
                "Repository not writable (only in-memory copies can be mutated)"
            )
        if name != model.name:
            # Treat as rename: remove old then add new
            self.remove(name)
            self.add(model)
            return
        # remove dependent rows then re-insert
        self._delete_rows(name)
        self._insert_model(model)
        self._cache.pop(name, None)

    def remove(self, name: str):  # pragma: no cover
        if not self._writable:
            raise NotImplementedError(
                "Repository not writable (only in-memory copies can be mutated)"
            )
        self._delete_rows(name)
        self._connect().execute("DELETE FROM standard_name WHERE name=?", (name,))
        self._connect().execute("DELETE FROM fts_standard_name WHERE name=?", (name,))
        self._connect().commit()
        self._cache.pop(name, None)

    # ------------------------------------------------------------------
    # Internal helpers for writable mode
    # ------------------------------------------------------------------
    def _ensure_schema(self):
        # FTS table might not exist in ephemeral connections if caller created a raw DB.
        cur = self._connect().cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='standard_name'"
        )
        if not cur.fetchone():  # extremely defensive; expected to exist
            raise RuntimeError("standard_name table missing in connection")
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fts_standard_name'"
        )
        if not cur.fetchone():
            cur.execute(
                "CREATE VIRTUAL TABLE fts_standard_name USING fts5( name UNINDEXED, description, documentation )"
            )

    def _insert_model(self, e: StandardName):
        cur = self._connect().cursor()
        cur.execute(
            "INSERT INTO standard_name(name,kind,status,unit,frame,description,documentation,validity_domain,deprecates,superseded_by,is_dimensionless) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                e.name,
                getattr(e, "kind", ""),
                getattr(e, "status", "draft"),
                getattr(e, "unit", "") or None,
                getattr(e, "frame", None),
                getattr(e, "description", ""),
                getattr(e, "documentation", "") or None,
                getattr(e, "validity_domain", "") or None,
                getattr(e, "deprecates", "") or None,
                getattr(e, "superseded_by", "") or None,
                1 if getattr(e, "is_dimensionless", False) else 0,
            ),
        )
        prov = getattr(e, "provenance", None)
        if prov:
            mode = getattr(prov, "mode", None)
            if mode == "operator":
                chain = json.dumps(getattr(prov, "operators", []))
                cur.execute(
                    "INSERT INTO provenance_operator(name, operator_chain, base, operator_id) VALUES (?,?,?,?)",
                    (
                        e.name,
                        chain,
                        getattr(prov, "base", None),
                        getattr(prov, "operator_id", None),
                    ),
                )
            elif mode == "reduction":
                cur.execute(
                    "INSERT INTO provenance_reduction(name, reduction, domain, base) VALUES (?,?,?,?)",
                    (
                        e.name,
                        getattr(prov, "reduction", None),
                        getattr(prov, "domain", None),
                        getattr(prov, "base", None),
                    ),
                )
            elif mode == "expression":
                cur.execute(
                    "INSERT INTO provenance_expression(name, expression) VALUES (?,?)",
                    (e.name, getattr(prov, "expression", None)),
                )
                for dep in getattr(prov, "dependencies", []):
                    cur.execute(
                        "INSERT INTO provenance_expression_dependency(name, dependency) VALUES (?,?)",
                        (e.name, dep),
                    )
        if getattr(e, "kind", "").endswith("vector"):
            for axis, comp in (getattr(e, "components", {}) or {}).items():
                cur.execute(
                    "INSERT INTO vector_component(vector_name, axis, component_name) VALUES (?,?,?)",
                    (e.name, axis, comp),
                )
        for t in getattr(e, "tags", []) or []:
            cur.execute("INSERT INTO tag(name, tag) VALUES (?,?)", (e.name, t))
        for link_val in getattr(e, "links", []) or []:
            cur.execute("INSERT INTO link(name, link) VALUES (?,?)", (e.name, link_val))
        # FTS row
        cur.execute(
            "INSERT INTO fts_standard_name(name, description, documentation) VALUES (?,?,?)",
            (
                e.name,
                getattr(e, "description", ""),
                getattr(e, "documentation", "") or "",
            ),
        )
        self._connect().commit()

    def _delete_rows(self, name: str):
        cur = self._connect().cursor()
        # Remove dependant rows explicitly then base; order matters if no cascade defined everywhere
        cur.execute("DELETE FROM provenance_operator WHERE name=?", (name,))
        cur.execute("DELETE FROM provenance_reduction WHERE name=?", (name,))
        cur.execute(
            "DELETE FROM provenance_expression_dependency WHERE name=?", (name,)
        )
        cur.execute("DELETE FROM provenance_expression WHERE name=?", (name,))
        cur.execute("DELETE FROM vector_component WHERE vector_name=?", (name,))
        cur.execute("DELETE FROM tag WHERE name=?", (name,))
        cur.execute("DELETE FROM link WHERE name=?", (name,))
        cur.execute("DELETE FROM fts_standard_name WHERE name=?", (name,))
        cur.execute("DELETE FROM standard_name WHERE name=?", (name,))
        self._connect().commit()

    def _row_to_model(self, row: sqlite3.Row) -> StandardName:
        data: Dict[str, Any] = {
            "name": row["name"],
            "kind": row["kind"],
            "status": row["status"],
            "unit": row["unit"] or "",
            "description": row["description"],
            "documentation": row["documentation"] or "",
            "validity_domain": row["validity_domain"] or "",
            "deprecates": row["deprecates"] or "",
            "superseded_by": row["superseded_by"] or "",
        }
        # Augment provenance / components by secondary queries (lazy)
        if row["kind"].endswith("vector"):
            comps = (
                self._connect()
                .execute(
                    "SELECT axis, component_name FROM vector_component WHERE vector_name=?",
                    (row["name"],),
                )
                .fetchall()
            )
            data["frame"] = row["frame"]
            data["components"] = {c["axis"]: c["component_name"] for c in comps}
        prov_op = (
            self._connect()
            .execute(
                "SELECT operator_chain, base, operator_id FROM provenance_operator WHERE name=?",
                (row["name"],),
            )
            .fetchone()
        )
        prov_red = (
            self._connect()
            .execute(
                "SELECT reduction, domain, base FROM provenance_reduction WHERE name=?",
                (row["name"],),
            )
            .fetchone()
        )
        prov_expr = (
            self._connect()
            .execute(
                "SELECT expression FROM provenance_expression WHERE name=?",
                (row["name"],),
            )
            .fetchone()
        )
        if prov_op:
            data["provenance"] = {
                "mode": "operator",
                "operators": json.loads(prov_op["operator_chain"]),
                "base": prov_op["base"],
                "operator_id": prov_op["operator_id"],
            }
        elif prov_red:
            data["provenance"] = {
                "mode": "reduction",
                "reduction": prov_red["reduction"],
                "domain": prov_red["domain"],
                "base": prov_red["base"],
            }
        elif prov_expr:
            deps = [
                r[0]
                for r in self._connect()
                .execute(
                    "SELECT dependency FROM provenance_expression_dependency WHERE name=?",
                    (row["name"],),
                )
                .fetchall()
            ]
            data["provenance"] = {
                "mode": "expression",
                "expression": prov_expr["expression"],
                "dependencies": deps,
            }
        # Tags & links
        tags = [
            r[0]
            for r in self._connect()
            .execute("SELECT tag FROM tag WHERE name=?", (row["name"],))
            .fetchall()
        ]
        links = [
            r[0]
            for r in self._connect()
            .execute("SELECT link FROM link WHERE name=?", (row["name"],))
            .fetchall()
        ]
        if tags:
            data["tags"] = tags
        if links:
            data["links"] = links
        if not self.revalidate:
            # Fast path: return lightweight namespace with expected attributes.
            # Downstream code should treat as read-only. No validation performed.
            return SimpleNamespace(**data)  # type: ignore[return-value]
        return create_standard_name(data)


__all__ = ["build_sqlite_catalog", "SqliteStandardNameRepository"]
