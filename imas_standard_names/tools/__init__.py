from fastmcp import FastMCP

from imas_standard_names.repository import StandardNameRepository
from imas_standard_names.tools.overview import OverviewTool
from imas_standard_names.tools.search import SearchTool


class Tools:
    """Main Tools class that delegates to individual tool implementations."""

    def __init__(self):
        """Initialize the Standard Names tools provider."""

        # Create shared in-memory standard name repository
        self.repository = StandardNameRepository()
        # Initialize individual tools with shared standard names repository
        self.search_tool = SearchTool(self.repository)
        self.overview_tool = OverviewTool(self.repository)

    @property
    def name(self) -> str:
        """Provider name for logging and identification."""
        return "tools"

    def register(self, mcp: FastMCP):
        """Register all IMAS tools with the MCP server.

        Discovers methods on tool instances that have been marked with the
        ``_mcp_tool`` attribute (set by the ``mcp_tool`` decorator) and
        registers each with FastMCP, passing through the stored description.
        This keeps registration declarative and avoids manual duplication.
        """

        tool_instances = [self.search_tool, self.overview_tool]

        for tool in tool_instances:
            for attr_name in dir(tool):  # introspect public + private
                if attr_name.startswith("_"):
                    continue  # skip dunder/private helpers
                attr = getattr(tool, attr_name)
                # Only register callables explicitly marked as MCP tools
                if callable(attr) and getattr(attr, "_mcp_tool", False):
                    description = getattr(attr, "_mcp_description", "")
                    # FastMCP.tool returns a decorator expecting the function
                    mcp.tool(description=description)(attr)
