from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import BaseTool


class SearchTool(BaseTool):
    """Tool for searching the Standard Names Catalog using service composition.

    Behavior:
        * Always performs search with metadata (repository.with_meta=True).
        * Transforms the repository list-of-dicts meta results into a mapping
          keyed by standard name => {score, highlight_documentation, standard_name}.
          This provides O(1) lookups by canonical name for downstream tooling.
    """

    @property
    def tool_name(self) -> str:
        """Return the name of this tool."""
        return "search_standard_names"

    @mcp_tool(
        description=(
            "Ranked full-text + fuzzy search over the IMAS Standard Names catalog. "
            "Input: free-text query (case-insensitive tokens / partial tokens). "
            "Output: up to 20 best matches with metadata (name, units, description, "
            "provenance, dependencies). Empty or no matches -> {}. Use to discover "
            "canonical variable identifiers for downstream tooling and validation."
        )
    )
    async def search_standard_names(
        self,
        query: str,
        ctx: Context | None = None,
    ):
        # Underlying repository returns list[ {name, score, highlight_documentation, standard_name} ]
        raw = self.repository.search(query, with_meta=True)
        return {r["name"]: {k: v for k, v in r.items() if k != "name"} for r in raw}
