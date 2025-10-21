"""
Create tool for adding new standard name entries to the catalog.

This tool provides batch and single-entry creation with validation,
dependency ordering, and dry-run support.
"""

from __future__ import annotations

import time
from typing import Any

from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.editing.batch_utils import topological_sort_operations
from imas_standard_names.models import StandardNameEntry, create_standard_name_entry
from imas_standard_names.tools.base import BaseTool


class CreateTool(BaseTool):
    """Tool for creating new standard name entries."""

    def __init__(self, catalog: Any, edit_catalog: Any):
        """Initialize CreateTool with catalog and edit_catalog.

        Args:
            catalog: StandardNameCatalog instance
            edit_catalog: EditCatalog instance for staging changes
        """
        super().__init__(catalog)
        self.edit_catalog = edit_catalog

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "standard-name-create"

    @mcp_tool(
        description=(
            "Create new standard name entries (single or batch). "
            "Validates entries before adding to catalog. Supports batch creation with "
            "automatic dependency ordering based on provenance. "
            "Changes are kept in-memory (pending) until write_standard_names is called. "
            "Use dry_run=true to validate without adding. "
            "Mode 'atomic' rolls back all on first error; 'continue' processes all entries."
        )
    )
    async def create_standard_names(
        self,
        entries: list[dict[str, Any]],
        dry_run: bool = False,
        mode: str = "continue",
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Create new standard name entries.

        Args:
            entries: List of entry dicts with name, kind, description, etc.
            dry_run: If True, validate but don't add to catalog
            mode: 'continue' (process all, accumulate errors) or 'atomic' (rollback on error)

        Returns:
            {
                "action": "batch",
                "summary": {
                    "total": n,
                    "successful": n,
                    "failed": n,
                    "skipped": n,
                    "duration_ms": n,
                    "mode": str,
                    "dry_run": bool
                },
                "results": [...],  # Per-entry results
                "last_successful_index": n
            }
        """
        start_time = time.time()

        # Validate entries before processing
        validated_entries: list[StandardNameEntry] = []
        validation_errors: list[dict] = []

        for i, entry_data in enumerate(entries):
            try:
                # This will raise if entry is invalid
                entry = create_standard_name_entry(entry_data)
                validated_entries.append(entry)
            except Exception as e:
                validation_errors.append(
                    {
                        "index": i,
                        "entry": entry_data,
                        "type": type(e).__name__,
                        "message": str(e),
                    }
                )
                # In 'atomic' mode, return early on first error
                if mode == "atomic":
                    return {
                        "action": "batch",
                        "summary": {
                            "total": len(entries),
                            "successful": 0,
                            "failed": len(entries),
                            "skipped": 0,
                            "duration_ms": int((time.time() - start_time) * 1000),
                            "mode": mode,
                            "dry_run": dry_run,
                        },
                        "error": validation_errors[0],
                    }
                # In 'continue' mode, accumulate errors and keep processing

        # Dependency ordering - Create simple wrapper objects for topological_sort_operations
        # It expects objects with 'model' attribute that has 'name' and 'provenance'
        class OpWrapper:
            def __init__(self, model: StandardNameEntry):
                self.model = model
                self.action = "add"

        wrapped_ops = [OpWrapper(entry) for entry in validated_entries]
        sorted_ops, circular_errors = topological_sort_operations(wrapped_ops)  # type: ignore[arg-type]

        if circular_errors:
            return {
                "action": "batch",
                "summary": {
                    "total": len(entries),
                    "successful": 0,
                    "failed": len(entries),
                    "skipped": 0,
                    "circular_dependencies": circular_errors,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "mode": mode,
                    "dry_run": dry_run,
                },
                "results": [],
            }

        sorted_entries = [op.model for op in sorted_ops]

        results = []
        successful_count = 0
        failed_count = 0
        last_successful_index: int | None = None
        snapshot = None

        # For atomic mode, take snapshot before starting
        if mode == "atomic" and not dry_run:
            snapshot = self.edit_catalog._take_snapshot()  # noqa: SLF001

        # Process each entry
        for idx, entry in enumerate(sorted_entries):
            try:
                if dry_run:
                    # Validate without adding - check both catalog and pending changes
                    if self.catalog.get(entry.name) or self.edit_catalog.uow.has(
                        entry.name
                    ):  # type: ignore[attr-defined]
                        raise ValueError(f"Entry '{entry.name}' already exists")  # type: ignore[attr-defined]
                    results.append(
                        {
                            "index": idx,
                            "status": "success",
                            "name": entry.name,  # type: ignore[attr-defined]
                        }
                    )
                else:
                    # Check if entry already exists in catalog or pending changes
                    if self.catalog.get(entry.name) or self.edit_catalog.uow.has(
                        entry.name
                    ):  # type: ignore[attr-defined]
                        raise ValueError(f"Entry '{entry.name}' exists")  # type: ignore[attr-defined]
                    # Add to catalog
                    self.edit_catalog.add(entry.model_dump())  # type: ignore[attr-defined]
                    results.append(
                        {
                            "index": idx,
                            "status": "success",
                            "name": entry.name,  # type: ignore[attr-defined]
                        }
                    )

                successful_count += 1
                last_successful_index = idx

            except Exception as e:
                # Capture error
                results.append(
                    {
                        "index": idx,
                        "status": "error",
                        "name": entry.name if hasattr(entry, "name") else "unknown",  # type: ignore[attr-defined]
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e),
                        },
                    }
                )
                failed_count += 1

                # Handle atomic mode failure
                if mode == "atomic":
                    # Rollback
                    if not dry_run and snapshot:
                        self.edit_catalog._baseline_snapshot = snapshot  # noqa: SLF001
                        self.edit_catalog.rollback()

                    # Mark remaining as skipped
                    for remaining_idx in range(idx + 1, len(sorted_entries)):
                        results.append(
                            {
                                "index": remaining_idx,
                                "status": "skipped",
                                "name": sorted_entries[remaining_idx].name,  # type: ignore[attr-defined]
                            }
                        )
                    break

        duration_ms = int((time.time() - start_time) * 1000)

        # Build return dict with validation errors if any
        result = {
            "action": "batch",
            "summary": {
                "total": len(entries),
                "successful": successful_count,
                "failed": failed_count + len(validation_errors),
                "skipped": len(entries)
                - successful_count
                - failed_count
                - len(validation_errors),
                "duration_ms": duration_ms,
                "mode": mode,
                "dry_run": dry_run,
            },
            "results": results,
            "last_successful_index": last_successful_index,
        }

        # Include validation errors if any occurred
        if validation_errors:
            result["validation_errors"] = validation_errors

        return result


__all__ = ["CreateTool"]
