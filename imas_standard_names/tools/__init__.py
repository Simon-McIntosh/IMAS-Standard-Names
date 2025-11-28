import logging

from fastmcp import FastMCP

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.check import CheckTool
from imas_standard_names.tools.compose import ComposeTool
from imas_standard_names.tools.create import CreateTool
from imas_standard_names.tools.edit import CatalogTool
from imas_standard_names.tools.fetch import FetchTool
from imas_standard_names.tools.list_standard_names import ListTool
from imas_standard_names.tools.naming_grammar import NamingGrammarTool
from imas_standard_names.tools.schema import SchemaTool
from imas_standard_names.tools.search import SearchTool
from imas_standard_names.tools.tokamak_parameters import TokamakParametersTool
from imas_standard_names.tools.validate_catalog import ValidateCatalogTool
from imas_standard_names.tools.vocabulary import VocabularyTool
from imas_standard_names.tools.vocabulary_tokens import VocabularyTokensTool
from imas_standard_names.tools.write import WriteTool


class Tools:
    """Main Tools class that delegates to individual tool implementations."""

    def __init__(self, catalog_root: str | None = None):
        """Initialize the Standard Names tools provider.

        Args:
            catalog_root: Optional custom directory for the standard names catalog.
                         If None, uses auto-discovery (env vars, installed package, or examples).
        """
        # Try to load main catalog, but don't fail if unavailable
        self._catalog_available = False
        try:
            # Create shared in-memory standard name repository
            # Always use permissive mode for MCP tools to ensure tools are available to fix issues
            self.catalog = StandardNameCatalog(
                root=catalog_root, permissive=True, allow_empty=False
            )
            self._catalog_available = True
        except ValueError as e:
            # No catalog available - some tools still work
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Catalog not available: {e}")
            logger.warning("Only grammar, schema, and compose tools will be available")
            self.catalog = None

        # Always load examples catalog (bundled, always available for grammar tools)
        self.examples_catalog = StandardNameCatalog(
            root="./imas_standard_names/resources/standard_name_examples",
            permissive=True,
        )

        # Grammar/schema tools (work without main catalog)
        self.grammar_tool = NamingGrammarTool(self.examples_catalog)
        self.schema_tool = SchemaTool(self.examples_catalog)
        self.compose_tool = ComposeTool()
        self.vocabulary_tokens_tool = VocabularyTokensTool(self.examples_catalog)
        self.tokamak_parameters_tool = TokamakParametersTool()

        # Catalog-dependent tools (only if catalog available)
        if self._catalog_available:
            # Read-only catalog tools (query and validate catalog entries)
            self.search_tool = SearchTool(self.catalog)
            self.check_tool = CheckTool(self.catalog)
            self.fetch_tool = FetchTool(self.catalog)
            self.validate_catalog_tool = ValidateCatalogTool(self.catalog)

            # Write tools (only if catalog is writable)
            if not self.catalog.read_only:
                self.edit_catalog = EditCatalog(self.catalog)
                self.list_tool = ListTool(self.catalog, self.edit_catalog)
                self.catalog_tool = CatalogTool(self.catalog, self.edit_catalog)
                self.create_tool = CreateTool(self.catalog, self.edit_catalog)
                self.write_tool = WriteTool(self.catalog, self.edit_catalog)

                # Quality/vocabulary tools (if available)
                from imas_standard_names.capabilities import check_write_capabilities

                capabilities = check_write_capabilities()
                if capabilities["vocabulary_management"]:
                    self.vocabulary_tool = VocabularyTool(self.catalog)
            else:
                # Read-only mode: list tool without edit capabilities
                self.list_tool = ListTool(self.catalog, None)

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

        Only registers tools that are available based on catalog availability
        and write capabilities.
        """

        # Always available tools (work without main catalog)
        always_available = [
            self.grammar_tool,
            self.schema_tool,
            self.compose_tool,
            self.vocabulary_tokens_tool,
            self.tokamak_parameters_tool,
        ]

        # Catalog-dependent tools
        catalog_tools = []
        if self._catalog_available:
            catalog_tools = [
                self.search_tool,
                self.check_tool,
                self.fetch_tool,
                self.list_tool,
                self.validate_catalog_tool,
            ]

            # Write tools (if catalog is writable)
            if hasattr(self, "catalog_tool"):
                catalog_tools.extend(
                    [
                        self.catalog_tool,
                        self.create_tool,
                        self.write_tool,
                    ]
                )

            # Vocabulary tool (if quality deps available)
            if hasattr(self, "vocabulary_tool"):
                catalog_tools.append(self.vocabulary_tool)

        # Register all available tools
        for tool in always_available + catalog_tools:
            for attr_name in dir(tool):  # introspect public + private
                if attr_name.startswith("_"):
                    continue  # skip dunder/private helpers
                attr = getattr(tool, attr_name)
                if callable(attr) and getattr(attr, "_mcp_tool", False):
                    description = getattr(attr, "_mcp_description", "")
                    mcp.tool(description=description)(attr)
