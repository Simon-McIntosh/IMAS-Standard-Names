"""Stateful editing catalog façade.

Provides persistent multi-call edit session semantics on top of the
`StandardNameCatalog` using a single lazily-created UnitOfWork and
semantic diffs between the last committed baseline and current staged
state.
"""

from __future__ import annotations

from typing import Any

from imas_standard_names.editing.edit_models import (
    AddInput,
    AddResult,
    ApplyInput,
    ApplyResult,
    DeleteInput,
    DeleteResult,
    ModifyInput,
    ModifyResult,
    RenameInput,
    RenameResult,
    parse_apply_input,
)
from imas_standard_names.schema import StandardName, create_standard_name
from imas_standard_names.unit_of_work import UnitOfWork

ModelDict = dict[str, Any]


def serialize_model(model: StandardName) -> ModelDict:
    return model.model_dump()  # type: ignore[attr-defined]


class EditCatalog:
    """Facade adding stateful edit semantics on top of a catalog."""

    def __init__(self, catalog: Any):
        self.catalog = catalog
        self._uow: UnitOfWork | None = None
        self._baseline_snapshot: dict[str, ModelDict] = self._take_snapshot()
        self._renames: list[tuple[str, str]] = []
        self._dirty_names: set[str] = set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @property
    def uow(self) -> UnitOfWork:
        if self._uow is None or self._uow._closed:  # noqa: SLF001
            self._uow = self.catalog.start_uow()
        assert self._uow is not None
        return self._uow

    def _take_snapshot(self) -> dict[str, ModelDict]:
        return {m.name: serialize_model(m) for m in self.catalog.list()}

    def _mark_dirty(self, *names: str):
        self._dirty_names.update(names)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def add(self, model_data: dict):
        model = create_standard_name(model_data)
        self.uow.add(model)
        self._mark_dirty(model.name)
        return model

    def modify(self, name: str, model_data: dict):
        model = create_standard_name(model_data)
        self.uow.update(name, model)
        self._mark_dirty(name, model.name)
        return model

    def rename(self, old_name: str, model_data: dict):
        model = create_standard_name(model_data)
        if model.name == old_name:
            return self.modify(old_name, model_data)
        self.uow.rename(old_name, model)
        self._renames.append((old_name, model.name))
        self._mark_dirty(old_name, model.name)
        return model

    def delete(self, name: str):
        before = self.catalog.get(name)
        self.uow.remove(name)
        if before:
            self._mark_dirty(name)
        return before is not None

    # ------------------------------------------------------------------
    # Undo / lifecycle
    # ------------------------------------------------------------------
    def undo_last(self) -> bool:
        if not self._uow:
            return False
        return self._uow.undo_last()

    def rollback(self):
        if self._uow:
            self._uow.rollback()
        self._uow = None
        self._renames.clear()
        self._dirty_names.clear()
        self._baseline_snapshot = self._take_snapshot()

    def commit(self):
        if not self._uow:
            return {"ok": True, "committed": False, "reason": "no_active_uow"}
        issues = self._uow.validate()
        if issues:
            return {
                "ok": False,
                "committed": False,
                "issues": issues,
                "error": "validation_failed",
            }
        self._uow.commit()
        self._uow = None
        self._baseline_snapshot = self._take_snapshot()
        self._renames.clear()
        self._dirty_names.clear()
        return {"ok": True, "committed": True}

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------
    def diff(self) -> dict[str, Any]:
        current = {m.name: serialize_model(m) for m in self.catalog.list()}
        baseline = self._baseline_snapshot
        added: list[ModelDict] = []
        removed: list[ModelDict] = []
        updated: list[dict[str, ModelDict | str]] = []
        renamed_pairs = set(self._renames)
        renamed_from = {o for o, _ in renamed_pairs}
        renamed_to = {n for _, n in renamed_pairs}
        baseline_names = set(baseline)
        current_names = set(current)
        for name in sorted(current_names - baseline_names - renamed_to):
            added.append({"name": name, "model": current[name]})
        for name in sorted(baseline_names - current_names - renamed_from):
            removed.append({"name": name, "model": baseline[name]})
        for name in sorted(
            (baseline_names & current_names) - renamed_from - renamed_to
        ):
            if baseline[name] != current[name]:
                updated.append(
                    {"name": name, "before": baseline[name], "after": current[name]}
                )
        renamed = [
            {"from": old, "to": new, "after": current.get(new)}
            for (old, new) in renamed_pairs
            if new in current
        ]
        counts = {
            "added": len(added),
            "removed": len(removed),
            "updated": len(updated),
            "renamed": len(renamed),
            "total_pending": len(added) + len(removed) + len(updated) + len(renamed),
        }
        return {
            "added": added,
            "removed": removed,
            "updated": updated,
            "renamed": renamed,
            "counts": counts,
        }

    # ------------------------------------------------------------------
    # Apply (union dispatch)
    # ------------------------------------------------------------------
    def apply(self, apply_input: dict | ApplyInput) -> ApplyResult:
        """Apply an edit and return a typed result model.

        Accepts either a raw dict (parsed only if a dict is provided) or an
        already constructed ApplyInput. Uses structural pattern matching for
        clarity. Returns an ApplyResult instance; callers that require a plain
        dictionary can call ``.model_dump()``.
        """
        if isinstance(apply_input, dict):
            apply_input = parse_apply_input(apply_input)

        match apply_input:
            case AddInput():
                model = self.add(apply_input.model.model_dump())  # type: ignore[attr-defined]
                return AddResult(model=model)
            case ModifyInput():
                existing = self.catalog.get(apply_input.name)
                old_model = (
                    existing.model_copy(deep=True) if existing else None  # type: ignore[attr-defined]
                )
                model = self.modify(
                    apply_input.name,
                    apply_input.model.model_dump(),  # type: ignore[attr-defined]
                )
                if old_model is None:
                    # Treat as add fallback (should rarely happen if validated earlier)
                    return AddResult(model=model)
                return ModifyResult(old_model=old_model, new_model=model)
            case RenameInput():
                existing = self.catalog.get(apply_input.old_name)
                if not existing:
                    raise KeyError(apply_input.old_name)
                cloned = existing.model_copy(deep=True)  # type: ignore[attr-defined]
                cloned.name = apply_input.new_name  # type: ignore[attr-defined]
                model = self.rename(
                    apply_input.old_name,
                    cloned.model_dump(),  # type: ignore[attr-defined]
                )
                return RenameResult(old_name=apply_input.old_name, new_name=model.name)
            case DeleteInput():
                existing = self.catalog.get(apply_input.name)
                existed = self.delete(apply_input.name)
                return DeleteResult(old_model=existing, existed=existed)
            case _:  # pragma: no cover - defensive
                raise RuntimeError("Unhandled edit input")

    # Metadata ----------------------------------------------------------
    def has_pending_changes(self) -> bool:
        return self.diff()["counts"]["total_pending"] > 0

    def pending_counts(self) -> dict[str, int]:
        return self.diff()["counts"].copy()

    def active_uow(self) -> bool:
        return self._uow is not None and not self._uow._closed  # noqa: SLF001


__all__ = ["EditCatalog"]
