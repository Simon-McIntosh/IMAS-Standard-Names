"""Repository abstractions for StandardName storage (lazy YAML backend)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Protocol, Optional
import yaml

from .schema import create_standard_name, StandardName, StandardNameBase
from .validation import run_structural_checks


class StandardNameRepository(Protocol):
    def get(self, name: str) -> Optional[StandardName]: ...
    def list(self) -> Iterable[StandardName]: ...
    def exists(self, name: str) -> bool: ...
    def add(self, model: StandardName) -> None: ...
    def update(self, name: str, model: StandardName) -> None: ...
    def remove(self, name: str) -> None: ...


@dataclass
class YamlStandardNameRepository(StandardNameRepository):
    root: Path
    _loaded: bool = field(default=False, init=False)
    _entries: Dict[str, StandardName] = field(default_factory=dict, init=False)
    _paths: Dict[str, Path] = field(default_factory=dict, init=False)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)
        files = list(self.root.rglob("*.yml")) + list(self.root.rglob("*.yaml"))
        for file in sorted(files):
            if file.is_dir():
                continue
            with open(file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict) or "name" not in data:
                continue  # skip malformed silently (strictness can be added)
            unit_val = data.get("unit")
            if isinstance(unit_val, (int, float)):
                data["unit"] = str(unit_val)
            model = create_standard_name(data)
            self._entries[model.name] = model
            self._paths[model.name] = file
        # structural checks (non-strict: raise if issues found now)
        issues = run_structural_checks(self._entries)
        if issues:
            raise ValueError("Structural validation failed: \n" + "\n".join(issues))
        self._loaded = True

    # Protocol methods
    def get(self, name: str) -> Optional[StandardName]:
        self._ensure_loaded()
        return self._entries.get(name)

    def list(self) -> Iterable[StandardName]:
        self._ensure_loaded()
        return list(self._entries.values())

    def exists(self, name: str) -> bool:
        self._ensure_loaded()
        return name in self._entries

    def add(self, model: StandardName) -> None:
        self._ensure_loaded()
        if model.name in self._entries:
            raise ValueError(f"Entry '{model.name}' already exists")
        self._entries[model.name] = model
        self._paths[model.name] = self.root / f"{model.name}.yml"

    def update(self, name: str, model: StandardName) -> None:
        self._ensure_loaded()
        if name not in self._entries:
            raise KeyError(name)
        if model.name != name and model.name in self._entries:
            raise ValueError(f"Cannot rename to existing entry '{model.name}'")
        # Handle rename
        if model.name != name:
            new_path = self.root / f"{model.name}.yml"
            self._entries.pop(name)
            self._entries[model.name] = model
            self._paths.pop(name)
            self._paths[model.name] = new_path
            # Defer filesystem removal; handled by UnitOfWork commit
        else:
            self._entries[name] = model

    def remove(self, name: str) -> None:
        self._ensure_loaded()
        if name not in self._entries:
            raise KeyError(name)
        self._entries.pop(name)
        # Path retained for possible deletion by UnitOfWork

    # Filesystem write helpers (used by UnitOfWork)
    def _write(self, model: StandardNameBase) -> Path:
        path = self._paths.get(model.name) or (self.root / f"{model.name}.yml")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in model.model_dump().items() if v not in (None, [], "")}
        data["name"] = model.name
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        self._paths[model.name] = path
        return path

    def _delete_file(self, name: str) -> None:
        path = self._paths.get(name)
        if path and path.exists():
            try:
                path.unlink()
            except OSError:
                pass


__all__ = [
    "StandardNameRepository",
    "YamlStandardNameRepository",
]


def load_standard_name_file(path: Path) -> StandardName:
    """Convenience helper (test use) to load a single file via repository logic."""
    repo = YamlStandardNameRepository(path.parent)
    # Force load only this file by calling internal ensure then filtering
    repo._ensure_loaded()  # type: ignore[attr-defined]
    return repo.get(Path(path).stem)  # type: ignore[return-value]


__all__.append("load_standard_name_file")
