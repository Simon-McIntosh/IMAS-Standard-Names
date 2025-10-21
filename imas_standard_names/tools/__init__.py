from fastmcp import FastMCP

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.check import CheckTool
from imas_standard_names.tools.create import CreateTool
from imas_standard_names.tools.edit import CatalogTool
from imas_standard_names.tools.fetch import FetchTool
from imas_standard_names.tools.names import NamesTool
from imas_standard_names.tools.overview import OverviewTool
from imas_standard_names.tools.search import SearchTool
from imas_standard_names.tools.write import WriteTool


class Tools:
    """Main Tools class that delegates to individual tool implementations."""

    def __init__(self, catalog_root: str | None = None):
        """Initialize the Standard Names tools provider.

        Args:
            catalog_root: Optional custom directory for the standard names catalog.
                         If None, uses the default packaged resources directory.
        """
        # Create shared in-memory standard name repository
        self.catalog = StandardNameCatalog(root=catalog_root)
        # Editing facade (persistent multi-call edit session support)
        self.edit_catalog = EditCatalog(self.catalog)
        # Initialize individual tools with shared standard names catalog
        self.search_tool = SearchTool(self.catalog)
        self.overview_tool = OverviewTool(self.catalog)
        # Give overview tool access to edit catalog for diff classification when tests attach it
        # (Tests may also set tool.edit_catalog directly.)
        self.catalog_tool = CatalogTool(self.catalog, self.edit_catalog)
        self.names_tool = NamesTool(self.catalog)
        self.check_tool = CheckTool(self.catalog)
        self.fetch_tool = FetchTool(self.catalog)
        self.write_tool = WriteTool(self.catalog, self.edit_catalog)
        self.create_tool = CreateTool(self.catalog, self.edit_catalog)

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
            self.check_tool,
            self.fetch_tool,
            self.write_tool,
            self.create_tool,
        ]

        for tool in tool_instances:
            for attr_name in dir(tool):  # introspect public + private
                if attr_name.startswith("_"):
                    continue  # skip dunder/private helpers
                attr = getattr(tool, attr_name)
                if callable(attr) and getattr(attr, "_mcp_tool", False):
                    description = getattr(attr, "_mcp_description", "")
                    mcp.tool(description=description)(attr)
