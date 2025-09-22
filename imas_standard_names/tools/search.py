from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import BaseTool


class SearchTool(BaseTool):
    """Tool for searching the Standard Names Catalog using service composition."""

    @property
    def tool_name(self) -> str:
        """Return the name of this tool."""
        return "search_standard_names"

    @mcp_tool(
        description=(
            "Ranked full-text + fuzzy search over the IMAS Standard Names catalog. "
            "Input: free-text query (case-insensitive tokens / partial tokens). "
            "Output: up to 20 best matches with metadata (name, units, description, "
            "provenance, dependencies). Empty or no matches -> []. Use to discover "
            "canonical variable identifiers for downstream tooling and validation."
        )
    )
    async def search_standard_names(
        self,
        query: str,
        ctx: Context | None = None,
    ):
        return self.repository.search(query, with_meta=True)
