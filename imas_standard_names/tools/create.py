"""
Create tool for adding new standard name entries to the catalog.

This tool provides batch and single-entry creation with validation,
dependency ordering, dry-run support, and upsert mode for incremental
enrichment of existing entries.
"""

from __future__ import annotations

import time
from typing import Any

from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.editing.batch_utils import topological_sort_operations
from imas_standard_names.grammar.field_schemas import UPSERT_GUIDANCE
from imas_standard_names.models import StandardNameEntry, create_standard_name_entry
from imas_standard_names.tools.base import CatalogTool
from imas_standard_names.validation.description import validate_description


class CreateTool(CatalogTool):
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

    def _build_merge_guidance(
        self, existing: dict[str, Any], proposed: dict[str, Any]
    ) -> dict[str, Any]:
        """Build merge guidance for LLM to combine existing and proposed entries.

        Args:
            existing: The existing entry data from the catalog
            proposed: The proposed new entry data

        Returns:
            Structured guidance for LLM to merge the entries
        """
        merge_strategy = (
            UPSERT_GUIDANCE.get("merge_strategy", {}) if UPSERT_GUIDANCE else {}
        )

        guidance = {
            "action": "upsert_required",
            "message": (
                f"Entry '{existing.get('name')}' already exists. "
                "Read both versions and compose a merged result."
            ),
            "existing": existing,
            "proposed": proposed,
            "merge_guidance": {
                "instructions": [
                    "Read both existing and proposed entries carefully",
                    "Compose a merged version that incorporates insights from both",
                    "Use edit_standard_names to apply the merged result",
                ],
                "field_strategies": merge_strategy,
                "workflow": (
                    UPSERT_GUIDANCE.get("workflow", []) if UPSERT_GUIDANCE else []
                ),
                "example_edit_call": {
                    "action": "modify",
                    "name": existing.get("name"),
                    "updates": {
                        "description": "<merged description>",
                        "documentation": "<merged documentation>",
                        "ids_paths": "<existing ids_paths + new ids_paths>",
                        "constraints": "<merged constraints>",
                    },
                },
            },
        }
        return guidance

    @mcp_tool(
        description=(
            "Create new standard name entries (single or batch). "
            "Validates entries before adding to catalog. Supports batch creation with "
            "automatic dependency ordering based on provenance. "
            "Changes are kept in-memory (pending) until write_standard_names is called. "
            "Use dry_run=true to validate without adding. "
            "Mode 'atomic' rolls back all on first error; 'continue' processes all entries; "
            "'upsert' returns existing entry with merge guidance for LLM-driven enrichment."
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
            mode: 'continue' (process all, accumulate errors),
                  'atomic' (rollback on error),
                  'upsert' (return merge guidance if entry exists)

        Returns:
            For mode='continue'/'atomic':
                {
                    "action": "batch",
                    "summary": {...},
                    "results": [...],
                    "last_successful_index": n
                }
            For mode='upsert' when entry exists:
                {
                    "action": "upsert_required",
                    "message": "...",
                    "existing": {...},
                    "proposed": {...},
                    "merge_guidance": {...}
                }
        """
        start_time = time.time()

        # Validate entries before processing
        validated_entries: list[StandardNameEntry] = []
        validation_errors: list[dict] = []
        description_warnings: dict[int, list[dict]] = {}  # index -> warnings

        for i, entry_data in enumerate(entries):
            try:
                # This will raise if entry is invalid
                entry = create_standard_name_entry(entry_data)

                # Validate description for metadata leakage (warnings only)
                description_issues = validate_description(entry_data)
                if description_issues:
                    description_warnings[i] = description_issues

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
        upsert_results = []  # For upsert mode - entries that need merging
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
                # Get original index for warnings lookup
                orig_idx = next(
                    (i for i, e in enumerate(validated_entries) if e == entry), idx
                )
                warnings = description_warnings.get(orig_idx, [])

                # Check if entry already exists
                existing = self.catalog.get(entry.name)  # type: ignore[attr-defined]
                pending_exists = self.edit_catalog.uow.has(entry.name)  # type: ignore[attr-defined]

                if existing or pending_exists:
                    if mode == "upsert":
                        # Return merge guidance instead of erroring
                        existing_data = (
                            existing.model_dump()
                            if existing
                            else self.edit_catalog.uow.get(entry.name).model_dump()  # type: ignore[attr-defined]
                        )
                        proposed_data = entry.model_dump()  # type: ignore[attr-defined]
                        upsert_results.append(
                            self._build_merge_guidance(existing_data, proposed_data)
                        )
                        # Don't count as failure or success in upsert mode
                        continue
                    else:
                        raise ValueError(f"Entry '{entry.name}' already exists")  # type: ignore[attr-defined]

                if dry_run:
                    result = {
                        "index": idx,
                        "status": "success",
                        "name": entry.name,  # type: ignore[attr-defined]
                    }
                    if warnings:
                        result["warnings"] = warnings
                    results.append(result)
                else:
                    # Add to catalog
                    self.edit_catalog.add(entry.model_dump())  # type: ignore[attr-defined]
                    result = {
                        "index": idx,
                        "status": "success",
                        "name": entry.name,  # type: ignore[attr-defined]
                    }
                    if warnings:
                        result["warnings"] = warnings
                    results.append(result)

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
        result_dict: dict[str, Any] = {
            "action": "batch",
            "summary": {
                "total": len(entries),
                "successful": successful_count,
                "failed": failed_count + len(validation_errors),
                "skipped": len(entries)
                - successful_count
                - failed_count
                - len(validation_errors)
                - len(upsert_results),
                "duration_ms": duration_ms,
                "mode": mode,
                "dry_run": dry_run,
            },
            "results": results,
            "last_successful_index": last_successful_index,
        }

        # Include upsert results if any (entries that need merging)
        if upsert_results:
            result_dict["upsert_required"] = upsert_results
            result_dict["summary"]["upsert_required"] = len(upsert_results)

        # Include validation errors if any occurred
        if validation_errors:
            result_dict["validation_errors"] = validation_errors

        return result_dict


__all__ = ["CreateTool"]
