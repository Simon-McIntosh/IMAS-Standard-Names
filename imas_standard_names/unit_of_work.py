"""Unit of Work for managing batched StandardName catalog mutations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Iterable

from .schema import StandardName
from .repositories import YamlStandardNameRepository, StandardNameRepository
from .validation import run_structural_checks


@dataclass
class UnitOfWork:
    repo: StandardNameRepository
    _new: Dict[str, StandardName] = field(default_factory=dict, init=False)
    _dirty: Dict[str, StandardName] = field(default_factory=dict, init=False)
    _deleted: Set[str] = field(default_factory=set, init=False)

    def add(self, model: StandardName) -> None:
        if self.repo.exists(model.name) or model.name in self._new:
            raise ValueError(f"Entry '{model.name}' already exists (repo or staged)")
        self._new[model.name] = model

    def update(self, name: str, model: StandardName) -> None:
        if name not in self._new and not self.repo.exists(name):
            raise KeyError(name)
        # Handle rename across staged items
        if name in self._new and name != model.name:
            self._new.pop(name)
            if model.name in self._new or self.repo.exists(model.name):
                raise ValueError(f"Cannot rename to existing entry '{model.name}'")
            self._new[model.name] = model
            return
        self._dirty[model.name] = model

    def remove(self, name: str) -> None:
        if name in self._new:
            self._new.pop(name)
            return
        if not self.repo.exists(name):
            raise KeyError(name)
        self._deleted.add(name)

    def list(self) -> Iterable[StandardName]:
        # Combined current view (repo + staged changes excluding deletions)
        existing = {m.name: m for m in self.repo.list()}
        existing.update(self._dirty)
        existing.update(self._new)
        for d in self._deleted:
            existing.pop(d, None)
        return existing.values()

    def validate(self) -> None:
        view = {m.name: m for m in self.list()}
        issues = run_structural_checks(view)
        if issues:
            raise ValueError("Structural validation failed:\n" + "\n".join(issues))

    def commit(self) -> None:
        # Validate full view first
        self.validate()
        # Writes
        if isinstance(self.repo, YamlStandardNameRepository):
            # Ensure repo loaded (so internal path mapping exists)
            self.repo._ensure_loaded()  # type: ignore[attr-defined]
        # Apply deletions
        for name in self._deleted:
            if isinstance(self.repo, YamlStandardNameRepository):
                path = self.repo._paths.get(name)  # type: ignore[attr-defined]
                if path:
                    self.repo._delete_file(name)  # type: ignore[attr-defined]
            # Remove from repo entries if present
            if self.repo.exists(name):
                self.repo.remove(name)
        # Apply new
        for model in self._new.values():
            if isinstance(self.repo, YamlStandardNameRepository):
                self.repo.add(model)
                self.repo._write(model)  # type: ignore[attr-defined]
            else:
                self.repo.add(model)
        # Apply dirty
        for model in self._dirty.values():
            if isinstance(self.repo, YamlStandardNameRepository):
                # update handles rename logic
                self.repo.update(model.name, model)
                self.repo._write(model)  # type: ignore[attr-defined]
            else:
                self.repo.update(model.name, model)
        # Clear staging
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()


__all__ = ["UnitOfWork"]
