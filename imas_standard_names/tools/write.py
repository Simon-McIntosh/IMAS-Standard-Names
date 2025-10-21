"""
Write tool for persisting in-memory catalog changes to disk.

This tool provides a simple interface to commit all unsaved changes
(new, modified, renamed, deleted entries) to YAML files on disk.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import BaseTool


class WriteTool(BaseTool):
    """Tool for persisting catalog changes to disk."""

    def __init__(self, catalog: Any, edit_catalog: Any):
        """Initialize WriteTool with catalog and edit_catalog.

        Args:
            catalog: StandardNameCatalog instance
            edit_catalog: EditCatalog instance with unsaved changes
        """
        super().__init__(catalog)
        self.edit_catalog = edit_catalog

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "standard-name-write"

    @mcp_tool(
        description=(
            "Write pending in-memory standard names to disk as YAML files. "
            "Validates all changes, writes new/modified entries, deletes removed entries. "
            "Clears pending changes after successful write and reloads catalog from disk. "
            "Use dry_run=true to validate without writing. "
            "Use list_standard_names(scope='pending') to review changes before writing."
        )
    )
    async def write_standard_names(
        self,
        dry_run: bool = False,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Write pending in-memory changes to disk.

        Args:
            dry_run: If True, validate but don't write files

        Returns:
            Dictionary with write status and summary:
            {
                "success": bool,
                "written": bool,
                "validation_passed": bool,
                "counts": {"added": n, "modified": n, "renamed": n, "deleted": n},
                "issues": [...] if validation failed,
                "dry_run": bool
            }
        """
        # Get current diff to show what will be written
        diff = self.edit_catalog.diff()
        counts = diff["counts"]

        # Check if there are any changes to write
        if counts["total_pending"] == 0:
            return {
                "success": True,
                "written": False,
                "validation_passed": True,
                "counts": counts,
                "message": "No pending changes to write",
                "dry_run": dry_run,
            }

        if dry_run:
            # Validate without writing
            issues = self.edit_catalog.uow.validate()
            if issues:
                return {
                    "success": False,
                    "written": False,
                    "validation_passed": False,
                    "counts": counts,
                    "issues": issues,
                    "dry_run": True,
                }
            return {
                "success": True,
                "written": False,
                "validation_passed": True,
                "counts": counts,
                "message": "Validation passed - ready to write",
                "dry_run": True,
            }

        # Actually write to disk
        result = self.edit_catalog.write()

        if result["ok"]:
            return {
                "success": True,
                "written": True,
                "validation_passed": True,
                "counts": counts,
                "message": f"Successfully wrote {counts['total_pending']} changes to disk",
                "dry_run": False,
            }
        else:
            # Keep entries in memory so user can edit and retry
            # Do NOT rollback - user wants to preserve changes for editing
            return {
                "success": False,
                "written": False,
                "validation_passed": False,
                "counts": counts,
                "issues": result.get("issues", []),
                "error": result.get("error", "unknown_error"),
                "message": "Write failed - entries preserved in memory. Fix validation issues and retry write_standard_names()",
                "dry_run": False,
            }


__all__ = ["WriteTool"]
