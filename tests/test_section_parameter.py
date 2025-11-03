"""Tests for section parameter on overview tools."""

import pytest

from imas_standard_names.tools.naming_grammar import NamingGrammarTool
from imas_standard_names.tools.schema import SchemaTool

pytestmark = pytest.mark.anyio


@pytest.fixture
def grammar_tool(sample_catalog):
    """Create NamingGrammarTool with sample catalog."""
    return NamingGrammarTool(sample_catalog)


@pytest.fixture
def schema_tool(sample_catalog):
    """Create SchemaTool with sample catalog (examples catalog)."""
    return SchemaTool(sample_catalog)


class TestGrammarSection:
    """Test section parameter on get_naming_grammar tool."""

    async def test_section_none_returns_overview(self, grammar_tool):
        """When section=None, return concise overview."""
        result = await grammar_tool.get_naming_grammar(section=None)

        # Check for key overview components
        assert "canonical_pattern" in result
        assert "quick_start" in result
        assert "version" in result
        assert "segment_usage" in result
        assert "common_patterns" in result
        # Should NOT contain full vocabularies with token lists
        assert (
            "vocabulary" not in result
            or isinstance(result.get("vocabulary"), dict)
            and "overview" in str(result.get("vocabulary"))
        )

    async def test_section_all_returns_full_output(self, grammar_tool):
        """When section='all', return complete grammar structure including applicability and examples."""
        result = await grammar_tool.get_naming_grammar(section="all")

        assert "applicability" in result
        assert "grammar_structure" in result
        assert "vocabulary" in result
        assert "validation_rules" in result
        assert "examples" in result
        assert "version" in result

    async def test_section_segments_returns_vocabulary(self, grammar_tool):
        """When section='segments', return vocabulary tokens."""
        result = await grammar_tool.get_naming_grammar(section="segments")

        assert result["section"] == "segments"
        assert "vocabulary" in result
        assert "component" in result["vocabulary"] or "subject" in result["vocabulary"]

    async def test_section_rules_returns_validation_rules(self, grammar_tool):
        """When section='rules', return validation rules."""
        result = await grammar_tool.get_naming_grammar(section="rules")

        assert result["section"] == "rules"
        assert "validation_rules" in result
        assert "composition_rules" in result

    async def test_section_examples_returns_composition_examples(self, grammar_tool):
        """When section='examples', return composition examples."""
        result = await grammar_tool.get_naming_grammar(section="examples")

        assert result["section"] == "examples"
        assert "composition_examples" in result

    async def test_section_statistics_returns_error(self, grammar_tool):
        """When section='statistics', return error since it's not a valid section."""
        result = await grammar_tool.get_naming_grammar(section="statistics")

        assert "error" in result
        assert result["error"] == "Invalid section"
        assert "available_sections" in result
        # statistics is NOT a valid section for grammar tool
        assert "statistics" not in result.get("available_sections", [])
        assert "segments" in result.get("available_sections", [])
        assert "examples" in result.get("available_sections", [])

    async def test_invalid_section_returns_error(self, grammar_tool):
        """When section is invalid, return error with available sections."""
        result = await grammar_tool.get_naming_grammar(section="invalid_section")

        assert "error" in result
        assert result["error"] == "Invalid section"
        assert "available_sections" in result
        assert "segments" in result["available_sections"]


class TestCatalogSchemaSection:
    """Test kind parameter on get_schema tool."""

    async def test_kind_none_returns_overview(self, schema_tool):
        """When kind=None, return comprehensive overview with schemas (80/20 pattern)."""
        result = await schema_tool.get_schema(kind=None)

        assert "base_schema" in result
        assert "entry_types" in result
        assert "examples" in result  # Now serving unified examples
        assert "workflow" in result
        # Base schema structure
        assert "provenance_definitions" in result

    async def test_kind_scalar_returns_scalar_schema(self, schema_tool):
        """When kind='scalar', return complete scalar schema."""
        result = await schema_tool.get_schema(kind="scalar")

        assert "kind" in result
        assert result["kind"] == "scalar"
        assert "field_schemas" in result
        assert "required_fields" in result
        assert "optional_fields" in result
        assert "examples" in result  # Now serving unified examples

    async def test_kind_vector_returns_vector_schema(self, schema_tool):
        """When kind='vector', return complete vector schema."""
        result = await schema_tool.get_schema(kind="vector")

        assert "kind" in result
        assert result["kind"] == "vector"
        assert "field_schemas" in result
        assert "required_fields" in result
        assert "examples" in result  # Now serving unified examples

    async def test_kind_metadata_returns_metadata_schema(self, schema_tool):
        """When kind='metadata', return complete metadata schema."""
        result = await schema_tool.get_schema(kind="metadata")

        assert "kind" in result
        assert result["kind"] == "metadata"
        assert "field_schemas" in result
        assert "required_fields" in result
        # Metadata doesn't have provenance
        if "provenance_definitions" in result:
            assert False, "metadata should not have provenance_definitions"

    async def test_invalid_kind_returns_error(self, schema_tool):
        """When kind is invalid, return error with available kinds."""
        result = await schema_tool.get_schema(kind="invalid_kind")

        assert "error" in result
        assert result["error"] == "Invalid kind"
        assert "available_kinds" in result
        assert "scalar" in result["available_kinds"]
        assert "vector" in result["available_kinds"]
        assert "metadata" in result["available_kinds"]


class TestKindParameterTokenSavings:
    """Test that kind parameter provides appropriate schemas."""

    async def test_overview_is_smaller_than_specific_kinds(self, grammar_tool):
        """Verify overview response is significantly smaller than full output."""
        overview = await grammar_tool.get_naming_grammar(section=None)
        full = await grammar_tool.get_naming_grammar(section="all")

        overview_str = str(overview)
        full_str = str(full)

        # Overview should be smaller than full (contains summary info vs detailed segments/examples)
        assert len(overview_str) < len(full_str), (
            f"Overview ({len(overview_str)} chars) not smaller than full ({len(full_str)} chars)"
        )

    async def test_catalog_overview_includes_all_kinds(self, schema_tool):
        """Verify catalog overview includes information about all entry types.

        Overview (kind=None) shows base schema + differences for all kinds.
        """
        overview = await schema_tool.get_schema(kind=None)

        # Overview should contain entry_types showing all kinds
        assert "entry_types" in overview
        assert "scalar" in str(overview["entry_types"])
        assert "vector" in str(overview["entry_types"])
        assert "metadata" in str(overview["entry_types"])

    async def test_kind_specific_is_focused(self, schema_tool):
        """Verify kind-specific response is focused on that kind only."""
        scalar_schema = await schema_tool.get_schema(kind="scalar")
        overview = await schema_tool.get_schema(kind=None)

        # Scalar schema should be focused on scalar only
        assert scalar_schema["kind"] == "scalar"
        # Overview should show all kinds
        assert "entry_types" in overview
