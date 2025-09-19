"""UnitOfWork with undo stack and YAML persistence commit boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from .schema import StandardName
from .services import validate_models


@dataclass
class Snapshot:
    name: str
    model: StandardName


@dataclass
class UndoOpAdd:  # inverse delete
    name: str


@dataclass
class UndoOpDelete:  # inverse reinsert
    snap: Snapshot


@dataclass
class UndoOpUpdate:  # inverse restore old
    snap: Snapshot


@dataclass
class UndoOpRename:  # inverse delete new then reinsert old
    old: Snapshot
    new_name: str


if TYPE_CHECKING:  # pragma: no cover
    from .repository import StandardNameRepository


class UnitOfWork:
    def __init__(self, repo: "StandardNameRepository"):
        self.repo = repo
        self.catalog = repo.catalog
        self._undo: List[object] = []
        self._closed = False

    # Mutations --------------------------------------------------------------
    def add(self, model: StandardName):
        if self.catalog.get_row(model.name):
            raise ValueError(f"Entry '{model.name}' exists")
        self.catalog.insert(model)
        self._undo.append(UndoOpAdd(model.name))

    def update(self, name: str, model: StandardName):
        row = self.catalog.get_row(name)
        if not row:
            raise KeyError(name)
        old_model = self.repo._row_to_model(row)
        self.catalog.delete(name)
        self.catalog.insert(model)
        self._undo.append(UndoOpUpdate(Snapshot(name, old_model)))

    def remove(self, name: str):
        row = self.catalog.get_row(name)
        if not row:
            return
        old_model = self.repo._row_to_model(row)
        self.catalog.delete(name)
        self._undo.append(UndoOpDelete(Snapshot(name, old_model)))

    def rename(self, old_name: str, new_model: StandardName):
        if old_name == new_model.name:
            return self.update(old_name, new_model)
        row = self.catalog.get_row(old_name)
        if not row:
            raise KeyError(old_name)
        old_model = self.repo._row_to_model(row)
        if self.catalog.get_row(new_model.name):
            raise ValueError(f"Target name '{new_model.name}' exists")
        self.catalog.delete(old_name)
        self.catalog.insert(new_model)
        self._undo.append(UndoOpRename(Snapshot(old_name, old_model), new_model.name))

    # Validation --------------------------------------------------------------
    def validate(self):
        models = {m.name: m for m in self.repo.list()}
        return validate_models(models)

    # Lifecycle ---------------------------------------------------------------
    def commit(self):
        issues = self.validate()
        if issues:
            raise ValueError("Validation failed:\n" + "\n".join(issues))
        existing_files = {f.stem for f in self.repo.store.yaml_files()}
        current_names = set()
        for m in self.repo.list():
            self.repo.store.write(m)
            current_names.add(m.name)
        for name in existing_files - current_names:
            self.repo.store.delete(name)
        self._undo.clear()
        self.close()

    def rollback(self):
        while self._undo:
            op = self._undo.pop()
            if isinstance(op, UndoOpAdd):
                self.catalog.delete(op.name)
            elif isinstance(op, UndoOpDelete):
                self.catalog.insert(op.snap.model)
            elif isinstance(op, UndoOpUpdate):
                self.catalog.delete(op.snap.name)
                self.catalog.insert(op.snap.model)
            elif isinstance(op, UndoOpRename):
                self.catalog.delete(op.new_name)
                self.catalog.insert(op.old.model)
        self.close()

    # Granular undo ---------------------------------------------------------
    def undo_last(self) -> bool:
        """Undo only the most recent mutation.

        Returns True if an operation was undone, False if there was nothing to undo.
        Leaves the UnitOfWork open for further staging or eventual commit/rollback.
        Raises RuntimeError if the UnitOfWork is already closed.
        """
        if self._closed:
            raise RuntimeError("UnitOfWork is closed")
        if not self._undo:
            return False
        op = self._undo.pop()
        if isinstance(op, UndoOpAdd):
            self.catalog.delete(op.name)
        elif isinstance(op, UndoOpDelete):
            self.catalog.insert(op.snap.model)
        elif isinstance(op, UndoOpUpdate):
            self.catalog.delete(op.snap.name)
            self.catalog.insert(op.snap.model)
        elif isinstance(op, UndoOpRename):
            self.catalog.delete(op.new_name)
            self.catalog.insert(op.old.model)
        else:  # pragma: no cover - defensive programming
            raise RuntimeError(f"Unknown undo op: {op!r}")
        return True

    def close(self):
        if not self._closed:
            self._closed = True
            self.repo._end_uow()


__all__ = [
    "UnitOfWork",
    "Snapshot",
    "UndoOpAdd",
    "UndoOpDelete",
    "UndoOpUpdate",
    "UndoOpRename",
]
