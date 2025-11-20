"""
Write tool for persisting in-memory catalog changes to disk.

This tool provides a simple interface to commit all unsaved changes
(new, modified, renamed, deleted entries) to YAML files on disk.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import CatalogTool


class WriteTool(CatalogTool):
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
            "Always get explicit user permission before calling this tool. "
            "Use list_standard_names(scope='pending') to review changes before writing. "
            "Validates all changes before writing. If validation fails, entries are preserved "
            "in memory for correction. Clears pending changes after successful write and reloads catalog."
        )
    )
    async def write_standard_names(
        self,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Write pending in-memory changes to disk.

        Returns:
            Dictionary with write status and summary:
            {
                "success": bool,
                "written": bool,
                "validation_passed": bool,
                "counts": {"added": n, "modified": n, "renamed": n, "deleted": n},
                "issues": [...] if validation failed
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
            }

        # Write to disk (includes validation)
        result = self.edit_catalog.write()

        if result["ok"]:
            # Get fresh counts after write (should show 0 pending)
            post_write_counts = self.edit_catalog.diff()["counts"]
            return {
                "success": True,
                "written": True,
                "validation_passed": True,
                "counts": post_write_counts,
                "message": f"Successfully wrote {counts['total_pending']} changes to disk",
            }
        else:
            # Keep entries in memory so user can edit and retry
            return {
                "success": False,
                "written": False,
                "validation_passed": False,
                "counts": counts,
                "issues": result.get("issues", []),
                "error": result.get("error", "unknown_error"),
                "message": "Write failed - entries preserved in memory. Fix validation issues and retry write_standard_names()",
            }


__all__ = ["WriteTool"]
