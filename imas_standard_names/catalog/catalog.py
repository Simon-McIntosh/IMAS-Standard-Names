"""Catalog utilities for IMAS Standard Names (relocated)."""

from __future__ import annotations
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Dict, List, Any
import json

from .. import schema


@dataclass
class StandardNameCatalog:
    root: Path | str
    strict: bool = True
    entries: Dict[str, schema.StandardName] = field(default_factory=dict, init=False)

    def __post_init__(self):  # pragma: no cover
        self._resolve_root()

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

    def load(self) -> "StandardNameCatalog":
        root_path = self.root if isinstance(self.root, Path) else Path(self.root)
        if not root_path.exists():  # pragma: no cover
            raise FileNotFoundError(f"Catalog root does not exist: {root_path}")
        matches = list(root_path.rglob("*.yml")) + list(root_path.rglob("*.yaml"))
        for file in sorted(matches):
            if file.is_dir():
                continue
            try:
                entry = schema.load_standard_name_file(file)
            except Exception:
                if self.strict:
                    raise
                else:
                    continue
            if entry.name in self.entries:
                msg = f"Duplicate standard name '{entry.name}' (file: {file})"
                if self.strict:
                    raise ValueError(msg)
                continue
            self.entries[entry.name] = entry
        return self

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: e.model_dump(exclude_none=True, exclude_defaults=True)
            for name, e in self.entries.items()
        }

    def index(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": e.name,
                "kind": getattr(e, "kind", None),
                "status": getattr(e, "status", None),
                "unit": getattr(e, "unit", ""),
                "tags": getattr(e, "tags", []),
            }
            for e in self.entries.values()
        ]

    def relationships(self) -> Dict[str, Dict[str, Any]]:
        rel: Dict[str, Dict[str, Any]] = {}
        for name, e in self.entries.items():
            data = e.model_dump()
            rel[name] = {
                "components": data.get("components", {}) or {},
                "magnitude": data.get("magnitude"),
                "provenance": data.get("provenance"),
                "parent_vector": data.get("parent_vector"),
                "axis": data.get("axis"),
            }
        return rel

    def write_json_artifacts(self, out_dir: Path | str) -> List[Path]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "catalog.json": self.as_dict(),
            "index.json": self.index(),
            "relationships.json": self.relationships(),
        }
        written: List[Path] = []
        for filename, payload in artifacts.items():
            path = out / filename
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=False)
            written.append(path)
        return written


__all__ = ["StandardNameCatalog"]
