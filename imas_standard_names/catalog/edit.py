"""Stateful editing catalog façade.

Provides persistent multi-call edit session semantics on top of the
`StandardNameCatalog` using a single lazily-created UnitOfWork and
semantic diffs between the last persisted baseline and current pending
state (in-memory vs on-disk).
"""

from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

from imas_standard_names.editing.batch_utils import topological_sort_operations
from imas_standard_names.editing.edit_models import (
    ApplyInput,
    ApplyResult,
    BatchDeleteInput,
    BatchDeleteResult,
    BatchInput,
    BatchResult,
    DeleteInput,
    DeleteResult,
    ErrorDetail,
    ModifyInput,
    ModifyResult,
    OperationResult,
    RenameInput,
    RenameResult,
    parse_apply_input,
)
from imas_standard_names.models import StandardNameEntry, create_standard_name_entry
from imas_standard_names.unit_of_work import UnitOfWork

ModelDict = dict[str, Any]


def serialize_model(model: StandardNameEntry) -> ModelDict:
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
        model = create_standard_name_entry(model_data)
        self.uow.add(model)
        self._mark_dirty(model.name)
        return model

    def modify(self, name: str, model_data: dict):
        model = create_standard_name_entry(model_data)
        self.uow.update(name, model)
        self._mark_dirty(name, model.name)
        return model

    def rename(self, old_name: str, model_data: dict):
        model = create_standard_name_entry(model_data)
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

    def discard_pending(self):
        """Discard all pending in-memory changes and reset to persisted state.

        Alias: rollback() for backward compatibility.
        """
        if self._uow:
            self._uow.rollback()
        self._uow = None
        self._renames.clear()
        self._dirty_names.clear()
        self._baseline_snapshot = self._take_snapshot()

    def rollback(self):
        """Backward compatibility alias for discard_pending()."""
        return self.discard_pending()

    def write(self):
        """Write pending in-memory changes to disk as YAML files.

        Validates all changes, persists to disk, then reloads the catalog
        to sync in-memory state with on-disk state.

        Returns:
            dict with keys:
                - ok (bool): True if write succeeded
                - written (bool): True if changes were persisted
                - issues (list): Validation errors if any
                - error (str): Error type if failed
        """
        if not self._uow:
            return {"ok": True, "written": False, "reason": "no_pending_changes"}
        issues = self._uow.validate()
        if issues:
            return {
                "ok": False,
                "written": False,
                "issues": issues,
                "error": "validation_failed",
            }
        self._uow.commit()  # Internal UoW method writes to disk
        self._uow = None
        # Reload catalog from disk to sync in-memory SQLite with persisted YAML files
        self.catalog.reload_from_disk()
        self._baseline_snapshot = self._take_snapshot()
        self._renames.clear()
        self._dirty_names.clear()
        return {"ok": True, "written": True}

    def commit(self):
        """Backward compatibility alias for write()."""
        result = self.write()
        # Map 'written' back to 'committed' for backward compatibility
        if "written" in result:
            result["committed"] = result["written"]
        return result

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------
    def diff(self) -> dict[str, Any]:
        """Compute diff between persisted (on-disk) and pending (in-memory) state."""
        current = {m.name: serialize_model(m) for m in self.catalog.list()}
        baseline = self._baseline_snapshot  # Persisted state
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
    def apply_batch(self, batch_input: BatchInput) -> BatchResult:
        """Process a batch of operations with optional dependency ordering.

        Supports:
        - Automatic dependency ordering via provenance
        - Continue-on-error or atomic transaction modes
        - Dry-run validation without committing
        - Resume from specific index
        """
        start_time = time.time()
        operations = batch_input.operations
        mode = batch_input.mode
        dry_run = batch_input.dry_run
        resume_from = batch_input.resume_from_index

        # Dependency ordering
        sorted_ops, circular_errors = topological_sort_operations(operations)
        if circular_errors:
            # Return immediately with circular dependency errors
            return BatchResult(
                summary={
                    "total": len(operations),
                    "successful": 0,
                    "failed": len(operations),
                    "skipped": 0,
                    "circular_dependencies": circular_errors,
                    "duration_ms": int((time.time() - start_time) * 1000),
                },
                results=[],
            )

        operations = sorted_ops
        results: list[OperationResult] = []
        successful_count = 0
        failed_count = 0
        skipped_count = 0
        last_successful_index: int | None = None

        # For atomic mode, create snapshot before starting
        snapshot = None
        snapshot_uow_state = None
        if mode == "atomic" and not dry_run:
            snapshot = self._take_snapshot()
            snapshot_uow_state = deepcopy(self._uow) if self._uow else None

        # Process each operation
        for idx, op in enumerate(operations):
            # Skip if before resume point
            if idx < resume_from:
                skipped_count += 1
                results.append(
                    OperationResult(
                        index=idx,
                        operation=op,
                        status="skipped",
                    )
                )
                continue

            try:
                if dry_run:
                    # Validate without committing
                    result = self._validate_operation(op)
                    results.append(
                        OperationResult(
                            index=idx,
                            operation=op,
                            status="success",
                            result=result,
                        )
                    )
                    successful_count += 1
                    last_successful_index = idx
                else:
                    # Apply operation
                    result = self.apply(op)
                    results.append(
                        OperationResult(
                            index=idx,
                            operation=op,
                            status="success",
                            result=result,
                        )
                    )
                    successful_count += 1
                    last_successful_index = idx

            except Exception as e:
                # Capture error details
                error = ErrorDetail(
                    type=type(e).__name__,
                    message=str(e),
                    field=self._extract_error_field(e),
                    suggestion=self._generate_error_suggestion(e, op),
                )
                results.append(
                    OperationResult(
                        index=idx,
                        operation=op,
                        status="error",
                        error=error,
                    )
                )
                failed_count += 1

                # Handle atomic mode failure
                if mode == "atomic":
                    # Rollback all changes
                    if not dry_run and snapshot is not None:
                        self._baseline_snapshot = snapshot
                        self._uow = snapshot_uow_state
                        if self._uow:
                            self._uow.rollback()
                        self._renames.clear()
                        self._dirty_names.clear()

                    # Mark remaining operations as skipped
                    for remaining_idx in range(idx + 1, len(operations)):
                        skipped_count += 1
                        results.append(
                            OperationResult(
                                index=remaining_idx,
                                operation=operations[remaining_idx],
                                status="skipped",
                            )
                        )
                    break

        duration_ms = int((time.time() - start_time) * 1000)

        return BatchResult(
            summary={
                "total": len(operations),
                "successful": successful_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "duration_ms": duration_ms,
                "mode": mode,
                "dry_run": dry_run,
            },
            results=results,
            last_successful_index=last_successful_index,
        )

    def _validate_operation(
        self, op: ModifyInput | RenameInput | DeleteInput
    ) -> ApplyResult:
        """Validate an operation without committing (for dry-run mode)."""
        # Create a temporary shallow copy to test validation
        # without actually mutating the catalog
        match op:
            case ModifyInput():
                existing = self.catalog.get(op.name)
                if not existing:
                    raise KeyError(f"Entry '{op.name}' not found")
                return ModifyResult(old_model=existing, new_model=op.model)
            case RenameInput():
                existing = self.catalog.get(op.old_name)
                if not existing:
                    raise KeyError(f"Entry '{op.old_name}' not found")
                if self.catalog.get(op.new_name):
                    raise ValueError(f"Target name '{op.new_name}' already exists")
                # Check dependencies if dry_run
                dependencies = (
                    self._find_dependencies(op.old_name) if op.dry_run else None
                )
                return RenameResult(
                    old_name=op.old_name,
                    new_name=op.new_name,
                    dry_run=op.dry_run,
                    dependencies=dependencies,
                )
            case DeleteInput():
                existing = self.catalog.get(op.name)
                # Check dependencies if dry_run
                dependencies = self._find_dependencies(op.name) if op.dry_run else None
                return DeleteResult(
                    old_model=existing,
                    existed=existing is not None,
                    dry_run=op.dry_run,
                    dependencies=dependencies,
                )
            case _:
                raise RuntimeError(f"Unknown operation type: {type(op)}")

    def _find_dependencies(self, name: str) -> list[str]:
        """Find all entries that depend on the given name via provenance."""
        dependencies = []
        for entry in self.catalog.list():
            if hasattr(entry, "provenance") and entry.provenance:  # type: ignore[attr-defined]
                # Check if this entry's provenance references the target name
                prov = entry.provenance  # type: ignore[attr-defined]
                if hasattr(prov, "dependencies") and prov.dependencies:  # type: ignore[attr-defined]
                    if name in prov.dependencies:  # type: ignore[attr-defined]
                        dependencies.append(entry.name)  # type: ignore[attr-defined]
        return dependencies

    def _extract_error_field(self, error: Exception) -> str | None:
        """Extract field name from validation errors when possible."""
        error_str = str(error)
        # Try to extract field from Pydantic validation errors
        if "provenance" in error_str.lower():
            if "base" in error_str.lower():
                return "provenance.base"
            return "provenance"
        if "name" in error_str.lower():
            return "name"
        return None

    def _generate_error_suggestion(
        self,
        error: Exception,
        op: ModifyInput | RenameInput | DeleteInput,
    ) -> str | None:
        """Generate helpful suggestions for common errors."""
        error_str = str(error)

        # Provenance base mismatch
        if "provenance base mismatch" in error_str.lower():
            return "Ensure provenance.base matches the base segment extracted from the name"

        # Entry not found
        if "not found" in error_str.lower():
            return "Ensure the entry exists in the catalog before modifying/renaming/deleting"

        return None

    def apply_batch_delete(
        self, batch_delete_input: BatchDeleteInput
    ) -> BatchDeleteResult:
        """Delete multiple entries in a batch operation.

        Returns summary with list of (name, existed, dependencies) tuples.
        If dry_run is True, validates and shows dependencies without deleting.
        """
        start_time = time.time()
        names = batch_delete_input.names
        dry_run = batch_delete_input.dry_run

        results: list[tuple[str, bool, list[str] | None]] = []
        successful = 0
        failed = 0

        for name in names:
            try:
                existing = self.catalog.get(name)
                existed = existing is not None
                dependencies = self._find_dependencies(name) if dry_run else None

                if not dry_run and existed:
                    self.delete(name)

                results.append((name, existed, dependencies))
                if existed:
                    successful += 1
            except Exception:
                failed += 1
                results.append((name, False, None))

        duration_ms = int((time.time() - start_time) * 1000)

        return BatchDeleteResult(
            summary={
                "total": len(names),
                "successful": successful,
                "failed": failed,
                "duration_ms": duration_ms,
                "dry_run": dry_run,
            },
            results=results,
            dry_run=dry_run,
        )

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
            case BatchInput():
                return self.apply_batch(apply_input)
            case BatchDeleteInput():
                return self.apply_batch_delete(apply_input)
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
                    raise KeyError(f"Entry '{apply_input.name}' not found")
                return ModifyResult(old_model=old_model, new_model=model)
            case RenameInput():
                existing = self.catalog.get(apply_input.old_name)
                if not existing:
                    raise KeyError(apply_input.old_name)

                # Handle dry_run
                if apply_input.dry_run:
                    dependencies = self._find_dependencies(apply_input.old_name)
                    return RenameResult(
                        old_name=apply_input.old_name,
                        new_name=apply_input.new_name,
                        dry_run=True,
                        dependencies=dependencies,
                    )

                cloned = existing.model_copy(deep=True)  # type: ignore[attr-defined]
                cloned.name = apply_input.new_name  # type: ignore[attr-defined]
                model = self.rename(
                    apply_input.old_name,
                    cloned.model_dump(),  # type: ignore[attr-defined]
                )
                return RenameResult(old_name=apply_input.old_name, new_name=model.name)
            case DeleteInput():
                existing = self.catalog.get(apply_input.name)

                # Handle dry_run
                if apply_input.dry_run:
                    dependencies = self._find_dependencies(apply_input.name)
                    return DeleteResult(
                        old_model=existing,
                        existed=existing is not None,
                        dry_run=True,
                        dependencies=dependencies,
                    )

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
