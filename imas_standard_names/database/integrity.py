"""Integrity verification utilities for file-backed catalogs.

Compares current YAML directory contents with integrity metadata stored
in the SQLite catalog produced by build_catalog.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import yaml as _yaml


def verify_integrity(
    yaml_root: Path, db_path: Path, full: bool = False
) -> list[dict[str, str]]:
    yaml_root = Path(yaml_root).resolve()
    db_path = Path(db_path)
    issues: list[dict[str, str]] = []
    if not db_path.exists():
        return [{"code": "db-missing", "detail": str(db_path)}]
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        # Ensure integrity tables exist
        has_tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('integrity','integrity_manifest')"
        ).fetchall()
        if len(has_tables) < 2:
            return [{"code": "integrity-missing", "detail": "tables not present"}]
        rows = cur.execute(
            "SELECT name, rel_path, size, mtime, hash FROM integrity"
        ).fetchall()
        db_index = {r["name"]: r for r in rows}
        # Track which names we see
        seen = set()
        # Enumerate YAML files and load per-entry
        name_to_file: dict[str, Path] = {}
        name_to_entry_hash: dict[str, str] = {}
        file_stat_cache: dict[Path, tuple[int, float]] = {}
        for yf in sorted(
            list(yaml_root.rglob("*.yml")) + list(yaml_root.rglob("*.yaml"))
        ):
            try:
                raw = yf.read_bytes()
            except OSError:
                continue
            try:
                loaded = _yaml.safe_load(raw)
            except _yaml.YAMLError:
                continue
            if isinstance(loaded, dict) and "name" in loaded:
                loaded = [loaded]
            if not isinstance(loaded, list):
                continue
            st = yf.stat()
            file_stat_cache[yf] = (st.st_size, st.st_mtime)
            for entry in loaded:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if not name:
                    continue
                entry_bytes = _yaml.safe_dump(
                    entry, sort_keys=True, allow_unicode=True
                ).encode()
                name_to_file[name] = yf
                name_to_entry_hash[name] = hashlib.blake2b(
                    entry_bytes, digest_size=16
                ).hexdigest()
        # Detect additions & modifications
        for name, path in name_to_file.items():
            if name not in db_index:
                issues.append({"code": "missing-in-db", "name": name})
                continue
            record = db_index[name]
            size, mtime = file_stat_cache.get(path, (0, 0.0))
            meta_changed = (size != record["size"]) or (mtime != record["mtime"])
            entry_hash = name_to_entry_hash[name]
            hash_changed = entry_hash != record["hash"]
            if hash_changed:
                issues.append({"code": "hash-mismatch", "name": name})
            elif meta_changed:
                issues.append({"code": "mismatch-meta", "name": name})
            seen.add(name)
        # Detect deletions (present in DB but not on disk)
        for name in db_index.keys() - seen:
            issues.append({"code": "missing-on-disk", "name": name})
        # Aggregate manifest verification (only if full)
        if full:
            manifest = cur.execute(
                "SELECT file_count, aggregate_hash FROM integrity_manifest WHERE id=1"
            ).fetchone()
            if manifest:
                # Recompute aggregate over current DB rows (not from disk) for consistency check
                agg = hashlib.blake2b(digest_size=16)
                pairs = [(n, db_index[n]["hash"]) for n in sorted(db_index.keys())]
                for n, h in pairs:
                    agg.update(f"{n}:{h}".encode())
                if agg.hexdigest() != manifest["aggregate_hash"] or manifest[
                    "file_count"
                ] != len(db_index):
                    issues.append(
                        {
                            "code": "manifest-mismatch",
                            "detail": "aggregate or count mismatch",
                        }
                    )
    finally:
        conn.close()
    return issues


__all__ = ["verify_integrity"]
