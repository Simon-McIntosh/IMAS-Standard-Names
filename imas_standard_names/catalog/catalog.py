"""Unified catalog facade for IMAS Standard Names.

The catalog loads from either the authoritative YAML tree or a pre-built SQLite artifact
(`catalog.db`). Selection rules:

* If `db_path` provided (or inferred) AND `prefer_db` is True AND the
    SQLite file is fresh (its recorded `max_yaml_mtime` meta matches the
    current max mtime of YAML files) -> load entries from SQLite.
* Otherwise parse YAML files into memory; optional downstream build of
    SQLite can be handled by the build CLI (not here) to keep the facade
    side-effect free.

The facade exposes a uniform `entries` dict plus convenience helpers.
Search semantics:
    - If backed by SQLite and an FTS table (`fts_standard_name`) exists,
        use MATCH for ranked results (default simple query).
    - Else perform a naive substring case-insensitive match over name,
        description, and documentation fields.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Dict, List
import sqlite3

from ..schema import StandardName, create_standard_name
import yaml
from ..storage.sqlite import SqliteStandardNameRepository


def _compute_max_yaml_mtime(root: Path) -> float:
    mtimes = [p.stat().st_mtime for p in root.rglob("*.yml")]
    mtimes += [p.stat().st_mtime for p in root.rglob("*.yaml")]
    return max(mtimes) if mtimes else 0.0


def _read_db_meta(db_path: Path) -> Dict[str, str]:  # lightweight helper
    if not db_path.exists():
        return {}
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meta'")
        if not cur.fetchone():
            conn.close()
            return {}
        rows = cur.execute("SELECT key, value FROM meta").fetchall()
        conn.close()
        return {k: v for k, v in rows}
    except Exception:  # pragma: no cover - defensive
        return {}


@dataclass
class StandardNameCatalog:
    root: Path | str
    db_path: Path | None = None
    prefer_db: bool = True
    strict: bool = True
    revalidate: bool = True
    require_fresh: bool = (
        False  # if True and DB stale -> force YAML (no silent stale use)
    )
    entries: Dict[str, StandardName] = field(default_factory=dict, init=False)
    source: str = field(default="", init=False)  # 'sqlite' | 'yaml'

    def __post_init__(self):  # pragma: no cover
        self._resolve_root()
        if self.db_path is None:
            # default artifact path relative to root
            self.db_path = Path(self.root) / ".." / "artifacts" / "catalog.db"
            self.db_path = self.db_path.resolve()

    def _resolve_root(self):  # pragma: no cover
        original = self.root
        try:
            package_root = Path(importlib_resources.files(__package__))  # type: ignore[arg-type]
        except Exception:  # pragma: no cover
            package_root = Path(__file__).resolve().parent.parent
        standard_names_root = package_root.parent / "resources" / "standard_names"
        match original:
            case Path() as p:
                self.root = p.expanduser().resolve()
            case str() as s if s.strip() in ("", "standard_names"):
                self.root = standard_names_root
            case str() as s if Path(s).is_absolute():
                self.root = Path(s).expanduser().resolve()
            case str() as s:
                parts = [p for p in s.replace("\\", "/").split("/") if p]
                if parts and parts[0] == "standard_names":
                    parts = parts[1:]
                self.root = (
                    (standard_names_root.joinpath(*parts)).expanduser().resolve()
                )
            case _:
                self.root = Path(str(original)).expanduser().resolve()

    # Public API -----------------------------------------------------
    # Internal auto-dispatch loader used by top-level load_catalog()
    def _load_auto(self) -> "StandardNameCatalog":
        root_path = Path(self.root)
        if self.prefer_db and self.db_path and self.db_path.exists():
            meta = _read_db_meta(self.db_path)
            db_mtime = float(meta.get("max_yaml_mtime", "0") or 0)
            current_mtime = _compute_max_yaml_mtime(root_path)
            fresh = current_mtime <= db_mtime + 1e-9  # allow float tolerance
            if fresh or not self.require_fresh:
                try:
                    repo = SqliteStandardNameRepository(
                        self.db_path, revalidate=self.revalidate
                    )
                    self.entries = {e.name: e for e in repo.list()}
                    self.source = "sqlite"
                    # If stale and require_fresh False, still loaded sqlite but mark flag
                    if not fresh:
                        self.source = "sqlite-stale"
                    return self
                except Exception:
                    if self.strict:
                        raise
                    # fallback to YAML path
        # YAML fallback / primary path
        return self._load_yaml_only()

    # Explicit source helpers -------------------------------------------------
    def _load_yaml_only(self) -> "StandardNameCatalog":
        root_path = Path(self.root)
        matches = list(root_path.rglob("*.yml")) + list(root_path.rglob("*.yaml"))
        for file in sorted(matches):
            if file.is_dir():
                continue
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if not isinstance(data, dict) or "name" not in data:
                    if self.strict:
                        raise ValueError(f"Malformed standard name file: {file}")
                    continue
                # Normalise numeric unit edge case
                unit_val = data.get("unit")
                if isinstance(unit_val, (int, float)):
                    data["unit"] = str(unit_val)
                entry = create_standard_name(data)
                if entry.name in self.entries:
                    msg = f"Duplicate standard name '{entry.name}' (file: {file})"
                    if self.strict:
                        raise ValueError(msg)
                    continue
                self.entries[entry.name] = entry
            except Exception:
                if self.strict:
                    raise
                else:
                    continue
        self.source = "yaml"
        return self

    def _load_sqlite_only(self) -> "StandardNameCatalog":
        if not self.db_path or not self.db_path.exists():
            raise FileNotFoundError(f"SQLite catalog not found at: {self.db_path}")
        repo = SqliteStandardNameRepository(self.db_path, revalidate=self.revalidate)
        self.entries = {e.name: e for e in repo.list()}
        self.source = "sqlite"
        return self

    # Class factory constructors (Option B) -----------------------------------
    @classmethod
    def from_yaml(
        cls,
        root: str | Path = "standard_names",
        *,
        strict: bool = True,
    ) -> "StandardNameCatalog":
        cat = cls(root, prefer_db=False, strict=strict)
        return cat._load_yaml_only()

    @classmethod
    def from_sqlite(
        cls,
        root: str | Path = "standard_names",
        *,
        db_path: str | Path | None = None,
        strict: bool = True,
        revalidate: bool = True,
    ) -> "StandardNameCatalog":
        cat = cls(
            root,
            db_path=Path(db_path) if db_path else None,
            prefer_db=True,
            strict=strict,
            revalidate=revalidate,
        )
        return cat._load_sqlite_only()

    def get(self, name: str) -> StandardName | None:
        return self.entries.get(name)

    def search(
        self,
        query: str,
        limit: int = 20,
        *,
        with_meta: bool = False,
        highlight_open: str = "<b>",
        highlight_close: str = "</b>",
    ) -> List[StandardName] | List[dict]:
        """Ranked search over catalog entries.

        Behaviour:
        - If backed by SQLite + FTS table present -> perform ranked (BM25)
          query returning highlights for description & documentation.
        - Otherwise fall back to simple substring match (unordered) with
          optional naive highlighting (case-insensitive token wrap in name & description).

        Parameters
        ----------
        query: str
            FTS expression or plain text. Multi words are treated per FTS rules.
        limit: int
            Maximum results.
        with_meta: bool
            When True, return a list of dicts: {name, score, highlight_description,
            highlight_documentation, model}. Otherwise return list[StandardName].
        highlight_open / highlight_close: str
            Tags to wrap matched terms (FTS highlight path).
        """
        # --- FTS path ---
        if self.source.startswith("sqlite") and self.db_path and self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='fts_standard_name'"
                )
                if cur.fetchone():
                    # highlight() column indexes: 0=name,1=description,2=documentation
                    sql = (
                        "SELECT name, bm25(fts_standard_name) AS score, "
                        "highlight(fts_standard_name, ?, ?, 1) AS h_desc, "
                        "highlight(fts_standard_name, ?, ?, 2) AS h_doc "
                        "FROM fts_standard_name WHERE fts_standard_name MATCH ? "
                        "ORDER BY score LIMIT ?"
                    )
                    cur.execute(
                        sql,
                        (
                            highlight_open,
                            highlight_close,
                            highlight_open,
                            highlight_close,
                            query,
                            limit,
                        ),
                    )
                    rows = cur.fetchall()
                    conn.close()
                    if with_meta:
                        out: List[dict] = []
                        for name, score, h_desc, h_doc in rows:
                            model = self.entries.get(name)
                            if not model:
                                continue
                            out.append(
                                {
                                    "name": name,
                                    "score": float(score)
                                    if score is not None
                                    else None,
                                    "highlight_description": h_desc,
                                    "highlight_documentation": h_doc,
                                    "model": model,
                                }
                            )
                        return out
                    return [self.entries[n[0]] for n in rows if n[0] in self.entries]
                conn.close()
            except Exception:  # pragma: no cover - fallback resilience
                pass

        # --- Substring fallback ---
        q = query.lower().strip()
        tokens = [t for t in q.split() if t]
        results: List[StandardName] = []
        for e in self.entries.values():
            text_doc = (getattr(e, "documentation", "") or "").lower()
            haystack = (e.name.lower(), e.description.lower(), text_doc)
            if all(any(tok in part for part in haystack) for tok in tokens):
                results.append(e)
                if len(results) >= limit:
                    break
        if not with_meta:
            return results
        # naive highlighting for fallback
        meta_results: List[dict] = []
        for e in results:
            desc_h = e.description
            doc_h = getattr(e, "documentation", "") or ""
            for tok in tokens:
                if not tok:
                    continue

                # simple case-insensitive replace preserving original case by scanning words
                def _hi(s: str) -> str:
                    import re

                    pattern = re.compile(re.escape(tok), re.IGNORECASE)
                    return pattern.sub(
                        lambda m: f"{highlight_open}{m.group(0)}{highlight_close}", s
                    )

                desc_h = _hi(desc_h)
                doc_h = _hi(doc_h)
            meta_results.append(
                {
                    "name": e.name,
                    "score": None,
                    "highlight_description": desc_h,
                    "highlight_documentation": doc_h,
                    "model": e,
                }
            )
        return meta_results


def load_catalog(
    root: str | Path = "standard_names",
    *,
    db_path: str | Path | None = None,
    prefer_db: bool = True,
    require_fresh: bool = False,
    strict: bool = True,
    revalidate: bool = True,
    in_memory_copy: bool = True,
) -> StandardNameCatalog:
    """Load a Standard Name catalog from SQLite (if fresh) or YAML.

    Parameters
    ----------
    root: path-like
        Root directory of YAML standard name files or shorthand 'standard_names'.
    db_path: path-like | None
        Explicit path to catalog.db (defaults to <root>/../artifacts/catalog.db if None).
    prefer_db: bool
        When True attempt to use SQLite artifact first (if exists).
    require_fresh: bool
        If True only use SQLite when meta max_yaml_mtime is >= current YAML tree mtime.
    strict: bool
        Propagate exceptions (True) or skip invalid entries (False) while parsing YAML / SQLite.
    revalidate: bool
        When False (SQLite only) skip full pydantic model reconstruction for speed (future optimization).
    """
    cat = StandardNameCatalog(
        root,
        db_path=Path(db_path) if db_path else None,
        prefer_db=prefer_db,
        strict=strict,
        revalidate=revalidate,
        require_fresh=require_fresh,
    )
    catalog = cat._load_auto()
    # If source is sqlite and in_memory_copy requested, clone to :memory: and rehydrate
    if (
        in_memory_copy
        and catalog.source.startswith("sqlite")
        and catalog.db_path
        and catalog.db_path.exists()
    ):
        try:
            import sqlite3
            from ..storage.sqlite import SqliteStandardNameRepository

            file_conn = sqlite3.connect(catalog.db_path)
            mem_conn = sqlite3.connect(":memory:")
            file_conn.backup(mem_conn)
            file_conn.close()
            # Rebuild entries from in-memory connection (read-only semantics preserved unless user opts writable)
            repo = SqliteStandardNameRepository.from_connection(
                mem_conn, revalidate=revalidate, writable=False
            )
            catalog.entries = {e.name: e for e in repo.list()}
            catalog.source = "sqlite-mem"
        except Exception:
            if strict:
                raise
            # fallback silently keeps disk-backed entries
    return catalog


__all__ = ["StandardNameCatalog", "load_catalog"]
