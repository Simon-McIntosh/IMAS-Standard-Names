"""Integration test: MCP server registers only read-only tools.

Verifies the read-only architecture by instantiating the full Tools class
and checking which tools are registered with the MCP server. Write tools
(create, edit, write) must be completely absent, and the supporting write
infrastructure modules must not exist.
"""

import importlib
from unittest.mock import MagicMock

import pytest

from imas_standard_names.tools import Tools

# ---------------------------------------------------------------------------
# Expected tool surfaces
# ---------------------------------------------------------------------------

READONLY_TOOLS = {
    "get_grammar",
    "get_schema",
    "compose_standard_name",
    "parse_standard_name",
    "search_standard_names",
    "check_standard_names",
    "fetch_standard_names",
    "list_standard_names",
    "validate_catalog",
    "get_vocabulary",
    "get_tokamak_parameters",
}

# Vocabulary audit tool is optional (requires spacy)
OPTIONAL_TOOLS = {
    "manage_vocabulary",
}

WRITE_TOOLS = {
    "create_standard_names",
    "edit_standard_names",
    "write_standard_names",
}

WRITE_MODULES = [
    "imas_standard_names.unit_of_work",
    "imas_standard_names.catalog.edit",
    "imas_standard_names.capabilities",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_registered_tool_names(tools: Tools) -> set[str]:
    """Register tools on a mock MCP server and return the tool names."""
    registered = {}

    def fake_tool(description=""):
        def decorator(fn):
            registered[fn.__name__] = description
            return fn

        return decorator

    mock_mcp = MagicMock()
    mock_mcp.tool = fake_tool
    tools.register(mock_mcp)
    return set(registered.keys())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def registered_tools(copy_examples, tmp_path):
    """Instantiate Tools with a populated catalog and collect registered names."""
    catalog_dir = tmp_path / "readonly_catalog"
    catalog_dir.mkdir()
    copy_examples(catalog_dir, count=5)
    tools = Tools(catalog_root=str(catalog_dir))
    return _collect_registered_tool_names(tools)


class TestReadOnlyToolRegistration:
    """The MCP server must expose only read-only tools."""

    def test_all_readonly_tools_registered(self, registered_tools):
        """Every expected read-only tool is present."""
        missing = READONLY_TOOLS - registered_tools
        assert not missing, f"Read-only tools missing from server: {missing}"

    def test_no_write_tools_registered(self, registered_tools):
        """Write-capable tools must not be registered."""
        leaked = WRITE_TOOLS & registered_tools
        assert not leaked, f"Write tools leaked into server: {leaked}"

    def test_no_unexpected_tools(self, registered_tools):
        """Only known read-only (and optional) tools are registered."""
        allowed = READONLY_TOOLS | OPTIONAL_TOOLS
        unexpected = registered_tools - allowed
        assert not unexpected, f"Unexpected tools registered: {unexpected}"


class TestWriteInfrastructureAbsent:
    """Write-mode infrastructure modules must not exist."""

    @pytest.mark.parametrize("module_path", WRITE_MODULES)
    def test_write_module_does_not_exist(self, module_path):
        """Importing a write-mode module must raise ImportError."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            importlib.import_module(module_path)
