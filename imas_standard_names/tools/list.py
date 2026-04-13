from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import CatalogTool


class ListTool(CatalogTool):
    """Tool for listing and filtering standard names.

    Provides catalog querying functionality to enumerate names with optional filters
    by unit, tags, kind, and status.
    """

    def __init__(self, catalog):  # type: ignore[no-untyped-def]
        super().__init__(catalog)

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "list"

    @mcp_tool(
        description=(
            "List standard names with optional field filters. "
            "Optional filters: unit (exact match), tags (contains any), kind (scalar/vector), status (draft/active/deprecated/superseded). "
            "Returns list of standard name identifiers matching the filters. "
            "Use this when you need to enumerate/browse all available names or filter by fields. "
            "For finding specific names by concept use search_standard_names; for details of known names use fetch_standard_names."
        )
    )
    async def list_standard_names(
        self,
        unit: str | int | None = None,
        tags: str | list[str] | None = None,
        kind: str | None = None,
        status: str | None = None,
        ctx: Context | None = None,
    ):  # noqa: D401
        """Return standard name identifiers with optional filters.

        Optional filters applied to all name sets:
            unit: exact match on unit field (numeric 1 converted to string "1")
            tags: match if entry contains any of the specified tags
            kind: scalar or vector
            status: draft, active, deprecated, or superseded
        """
        # Normalize unit filter: convert numeric 1 to string "1"
        if unit is not None and (unit == 1 or unit == 1.0):
            unit = "1"

        # Apply filters using repository filter method
        if unit is None and tags is None and kind is None and status is None:
            names = self.catalog.list_names()
        else:
            filtered_entries = self.catalog.list(
                unit=unit, tags=tags, kind=kind, status=status
            )
            names = sorted([e.name for e in filtered_entries])

        return {
            "names": names,
            "count": len(names),
        }
