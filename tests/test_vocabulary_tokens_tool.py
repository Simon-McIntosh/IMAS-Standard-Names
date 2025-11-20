"""Tests for the vocabulary management tool."""

import pytest

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.vocabulary import VocabularyTool
from imas_standard_names.tools.vocabulary_tokens import VocabularyTokensTool


@pytest.fixture
def vocabulary_tool():
    """Create a VocabularyTool instance with test catalog."""
    catalog = StandardNameCatalog()
    return VocabularyTool(catalog)


@pytest.fixture
def vocabulary_tokens_tool():
    """Create a VocabularyTokensTool instance for testing."""
    catalog = StandardNameCatalog()
    return VocabularyTokensTool(catalog)


class TestVocabularyManageTool:
    """Test suite for manage_vocabulary tool with discriminated union."""

    @pytest.mark.anyio
    async def test_list_all_vocabularies(self, vocabulary_tokens_tool):
        """Test listing all vocabularies."""
        result = await vocabulary_tokens_tool.get_vocabulary_tokens()

        assert "segments" in result
        assert "summary" in result

        segments = result["segments"]

        # Check that expected grammar segments are present
        expected_segments = [
            "component",
            "subject",
            "geometric_base",
            "object",
            "geometry",
            "position",
            "process",
        ]
        for segment in expected_segments:
            assert segment in segments, f"Missing segment: {segment}"

        # Verify segment structure
        component_data = segments["component"]
        assert "tokens" in component_data
        assert isinstance(component_data["tokens"], list)
        assert "radial" in component_data["tokens"]
        assert "toroidal" in component_data["tokens"]

    @pytest.mark.anyio
    async def test_list_specific_vocabulary(self, vocabulary_tokens_tool):
        """Test listing a specific segment vocabulary."""
        result = await vocabulary_tokens_tool.get_vocabulary_tokens(segment="component")

        assert "component" in result

        component_data = result["component"]
        assert isinstance(component_data["tokens"], list)
        assert len(component_data["tokens"]) > 0
        assert "radial" in component_data["tokens"]

    @pytest.mark.anyio
    async def test_audit_detects_missing_tokens(self, vocabulary_tool):
        """Test audit action detects missing vocabulary tokens."""
        result = await vocabulary_tool.manage_vocabulary(
            payload={
                "action": "audit",
            }
        )

        assert result["action"] == "audit"
        assert "recommendations" in result
        assert "summary" in result

        # Check structure of recommendations - grouped by priority
        recommendations = result["recommendations"]
        assert "high" in recommendations
        assert "medium" in recommendations
        assert "low" in recommendations

        # Summary should have clear counts
        summary = result["summary"]
        assert "total_missing_tokens" in summary
        assert "by_priority" in summary
        assert "by_vocabulary" in summary

    @pytest.mark.anyio
    async def test_check_name_returns_result(self, vocabulary_tool):
        """Test check action returns proper structure."""
        result = await vocabulary_tool.manage_vocabulary(
            payload={
                "action": "check",
                "name": "area_at_fictional_location",
            }
        )

        assert result["action"] == "check"
        assert "name" in result
        assert result["name"] == "area_at_fictional_location"
        assert "has_vocabulary_gap" in result
        assert "current_parse" in result
        assert "gap_details" in result

        # Check returns boolean gap flag and optional details
        assert isinstance(result["has_vocabulary_gap"], bool)
        # gap_details is None if no gap, or MissingToken dict if gap exists
        if result["has_vocabulary_gap"]:
            assert result["gap_details"] is not None
            assert "token" in result["gap_details"]
            assert "frequency" in result["gap_details"]
        else:
            assert result["gap_details"] is None


class TestVocabularyToolIntegration:
    """Integration tests with real catalog data."""

    @pytest.mark.anyio
    async def test_with_standard_names_catalog(self, vocabulary_tokens_tool):
        """Test vocabulary tool with actual standard names catalog."""
        # Test that we can list all vocabularies
        result = await vocabulary_tokens_tool.get_vocabulary_tokens()

        assert "segments" in result
        assert "summary" in result

        # Should have reasonable number of segments
        segments = result["segments"]
        assert len(segments) >= 10

        # Should have some vocabulary tokens
        summary = result["summary"]
        assert "total_tokens" in summary
        assert summary["total_tokens"] > 0

    @pytest.mark.anyio
    async def test_audit_with_catalog(self, vocabulary_tool):
        """Test audit action with real catalog."""
        # Audit the catalog
        result = await vocabulary_tool.manage_vocabulary(
            payload={
                "action": "audit",
            }
        )

        assert result["action"] == "audit"
        assert "recommendations" in result
        assert "summary" in result

        # Check that recommendations are grouped by priority
        recommendations = result["recommendations"]
        assert "high" in recommendations
        assert "medium" in recommendations
        assert "low" in recommendations

    @pytest.mark.anyio
    async def test_check_real_name(self):
        """Test check action with a real standard name."""
        catalog = StandardNameCatalog()
        vocab_tool = VocabularyTool(catalog)

        result = await vocab_tool.manage_vocabulary(
            payload={
                "action": "check",
                "name": "radial_component_of_magnetic_field",
            }
        )

        assert result["action"] == "check"
        assert "has_vocabulary_gap" in result
        # Real name should have no gaps
        assert result["has_vocabulary_gap"] is False
        assert result["gap_details"] is None
