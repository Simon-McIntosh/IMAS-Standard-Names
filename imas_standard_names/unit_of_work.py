"""Unit of Work for managing batched StandardName catalog mutations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Iterable

from .schema import StandardName
from .repository import StandardNameRepository
from .services import validate_models
from .yaml_store import YamlStore


@dataclass
class UnitOfWork:
    repo: StandardNameRepository
    _new: Dict[str, StandardName] = field(default_factory=dict, init=False)
    _dirty: Dict[str, StandardName] = field(default_factory=dict, init=False)
    _deleted: Set[str] = field(default_factory=set, init=False)

    def add(self, model: StandardName) -> None:
        if self.repo.get(model.name) or model.name in self._new:
            raise ValueError(f"Entry '{model.name}' already exists (repo or staged)")
        self._new[model.name] = model

    def update(self, name: str, model: StandardName) -> None:
        if name not in self._new and not self.repo.get(name):
            raise KeyError(name)
        # Handle rename across staged items
        if name in self._new and name != model.name:
            self._new.pop(name)
            if model.name in self._new or self.repo.get(model.name):
                raise ValueError(f"Cannot rename to existing entry '{model.name}'")
            self._new[model.name] = model
            return
        self._dirty[model.name] = model

    def remove(self, name: str) -> None:
        if name in self._new:
            self._new.pop(name)
            return
        if not self.repo.get(name):
            raise KeyError(name)
        self._deleted.add(name)

    def list(self) -> Iterable[StandardName]:
        existing = {m.name: m for m in self.repo.list()}
        existing.update(self._dirty)
        existing.update(self._new)
        for d in self._deleted:
            existing.pop(d, None)
        return list(existing.values())

    def validate(self) -> None:
        view = {m.name: m for m in self.list()}
        issues = validate_models(view)
        if issues:
            raise ValueError("Structural validation failed:\n" + "\n".join(issues))

    def commit(self) -> None:
        # Validate staged + existing view
        self.validate()
        # Access underlying yaml store (authoritative persistence)
        store: YamlStore = self.repo.store  # type: ignore[attr-defined]
        # Deletions
        for name in self._deleted:
            store.delete(name)
        # New + dirty -> write YAML (idempotent overwrite for dirty)
        for model in {**self._new, **self._dirty}.values():
            store.write(model)
            # Reflect into in-memory catalog
            existing = self.repo.get(model.name)
            if not existing:  # new
                self.repo.catalog.insert(model)
            else:  # update: remove + insert simplistic approach
                self.repo.catalog.delete(model.name)
                self.repo.catalog.insert(model)
        # Removed from in-memory catalog
        for name in self._deleted:
            if self.repo.get(name):
                self.repo.catalog.delete(name)
        # Clear state + notify repo
        self.repo._end_uow()
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()


__all__ = ["UnitOfWork"]
