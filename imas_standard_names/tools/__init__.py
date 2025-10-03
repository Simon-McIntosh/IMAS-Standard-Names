from fastmcp import FastMCP

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.edit import CatalogTool
from imas_standard_names.tools.names import NamesTool
from imas_standard_names.tools.overview import OverviewTool
from imas_standard_names.tools.search import SearchTool


class Tools:
    """Main Tools class that delegates to individual tool implementations."""

    def __init__(self):
        """Initialize the Standard Names tools provider."""
        # Create shared in-memory standard name repository
        self.catalog = StandardNameCatalog()
        # Editing facade (persistent multi-call edit session support)
        self.edit_catalog = EditCatalog(self.catalog)
        # Initialize individual tools with shared standard names catalog
        self.search_tool = SearchTool(self.catalog)
        self.overview_tool = OverviewTool(self.catalog)
        # Give overview tool access to edit catalog for diff classification when tests attach it
        # (Tests may also set tool.edit_catalog directly.)
        self.catalog_tool = CatalogTool(self.catalog, self.edit_catalog)
        self.names_tool = NamesTool(self.catalog)

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

        tool_instances = [
            self.search_tool,
            self.overview_tool,
            self.catalog_tool,
            self.names_tool,
        ]

        for tool in tool_instances:
            for attr_name in dir(tool):  # introspect public + private
                if attr_name.startswith("_"):
                    continue  # skip dunder/private helpers
                attr = getattr(tool, attr_name)
                if callable(attr) and getattr(attr, "_mcp_tool", False):
                    description = getattr(attr, "_mcp_description", "")
                    mcp.tool(description=description)(attr)
