"""Tests for check_standard_names tool.

Validates the fast batch validation functionality including:
- Existence checks
- Grammar validation
- Basic metadata retrieval
- Batch processing
"""

import asyncio

import pytest

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.check import CheckTool


def invoke(tool, *args, **kwargs):
    """Helper to run async tool methods."""
    return asyncio.run(tool.check_standard_names(*args, **kwargs))


@pytest.fixture
def check_tool(sample_catalog):
    """Create CheckTool with sample catalog."""
    return CheckTool(sample_catalog)


@pytest.fixture
def catalog(sample_catalog):
    """Alias for sample_catalog fixture."""
    return sample_catalog


class TestCheckSingleName:
    """Tests for checking individual standard names."""

    def test_check_existing_name(self, check_tool, catalog):
        """Test checking a name that exists in the catalog."""
        # Pick a name we know exists
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        result = invoke(check_tool, test_name)

        assert result["summary"]["total"] == 1
        assert result["summary"]["found"] == 1
        assert result["summary"]["not_found"] == 0
        assert result["summary"]["invalid"] == 0

        check_result = result["results"][0]
        assert check_result["name"] == test_name
        assert check_result["exists"] is True
        assert check_result["grammar_valid"] is True
        assert check_result["grammar_errors"] == []
        assert check_result["status"] is not None
        assert check_result["kind"] is not None
        assert check_result["unit"] is not None

    def test_check_nonexistent_valid_grammar(self, check_tool):
        """Test checking a name with valid grammar but doesn't exist."""
        result = invoke(check_tool, "electron_density_at_midplane")

        assert result["summary"]["total"] == 1
        assert result["summary"]["found"] == 0
        assert result["summary"]["not_found"] == 1
        assert result["summary"]["invalid"] == 0

        check_result = result["results"][0]
        assert check_result["name"] == "electron_density_at_midplane"
        assert check_result["exists"] is False
        assert check_result["grammar_valid"] is True
        assert check_result["grammar_errors"] == []
        assert check_result["status"] is None
        assert check_result["kind"] is None
        assert check_result["unit"] is None

    def test_check_invalid_grammar(self, check_tool):
        """Test checking a name with invalid grammar."""
        result = invoke(check_tool, "Invalid__Name__Here")

        assert result["summary"]["total"] == 1
        assert result["summary"]["found"] == 0
        assert result["summary"]["not_found"] == 1
        assert result["summary"]["invalid"] == 1

        check_result = result["results"][0]
        assert check_result["name"] == "Invalid__Name__Here"
        assert check_result["exists"] is False
        assert check_result["grammar_valid"] is False
        assert len(check_result["grammar_errors"]) > 0
        assert check_result["status"] is None
        assert check_result["kind"] is None
        assert check_result["unit"] is None


class TestCheckBatchNames:
    """Tests for batch checking multiple names."""

    def test_check_multiple_existing(self, check_tool, catalog):
        """Test checking multiple existing names."""
        all_names = catalog.list_names()
        if len(all_names) < 2:
            pytest.skip("Need at least 2 names in catalog")

        test_names = all_names[:2]
        result = invoke(check_tool, test_names)

        assert result["summary"]["total"] == 2
        assert result["summary"]["found"] == 2
        assert result["summary"]["not_found"] == 0
        assert result["summary"]["invalid"] == 0

        for check_result, expected_name in zip(
            result["results"], test_names, strict=True
        ):
            assert check_result["name"] == expected_name
            assert check_result["exists"] is True
            assert check_result["grammar_valid"] is True

    def test_check_mixed_batch(self, check_tool, catalog):
        """Test batch with mix of existing, nonexistent, and invalid names."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_names = [
            all_names[0],  # exists
            "nonexistent_but_valid_name",  # doesn't exist but valid grammar
            "Invalid__Grammar",  # invalid grammar
        ]
        result = invoke(check_tool, test_names)

        assert result["summary"]["total"] == 3
        assert result["summary"]["found"] == 1
        assert result["summary"]["not_found"] == 2
        assert result["summary"]["invalid"] == 1

        # First result - exists
        assert result["results"][0]["exists"] is True
        assert result["results"][0]["grammar_valid"] is True

        # Second result - doesn't exist but valid
        assert result["results"][1]["exists"] is False
        assert result["results"][1]["grammar_valid"] is True

        # Third result - invalid grammar
        assert result["results"][2]["exists"] is False
        assert result["results"][2]["grammar_valid"] is False
        assert len(result["results"][2]["grammar_errors"]) > 0

    def test_check_space_delimited_string(self, check_tool, catalog):
        """Test checking names provided as space-delimited string."""
        all_names = catalog.list_names()
        if len(all_names) < 2:
            pytest.skip("Need at least 2 names in catalog")

        test_names_str = f"{all_names[0]} {all_names[1]}"
        result = invoke(check_tool, test_names_str)

        assert result["summary"]["total"] == 2
        assert result["summary"]["found"] == 2
        assert result["results"][0]["name"] == all_names[0]
        assert result["results"][1]["name"] == all_names[1]


class TestCheckMetadata:
    """Tests for metadata returned by check tool."""

    def test_scalar_metadata(self, check_tool, catalog):
        """Test metadata for scalar entries."""
        # Find a scalar entry
        all_entries = catalog.list()
        scalars = [e for e in all_entries if e.kind == "scalar"]
        if not scalars:
            pytest.skip("No scalar entries in catalog")

        scalar = scalars[0]
        result = invoke(check_tool, scalar.name)

        check_result = result["results"][0]
        assert check_result["kind"] == "scalar"
        assert check_result["status"] in ["draft", "active", "deprecated", "superseded"]
        assert isinstance(check_result["unit"], str)

    def test_vector_metadata(self, check_tool, catalog):
        """Test metadata for vector entries."""
        # Find a vector entry
        all_entries = catalog.list()
        vectors = [e for e in all_entries if e.kind == "vector"]
        if not vectors:
            pytest.skip("No vector entries in catalog")

        vector = vectors[0]
        result = invoke(check_tool, vector.name)

        check_result = result["results"][0]
        assert check_result["kind"] == "vector"
        assert check_result["status"] in ["draft", "active", "deprecated", "superseded"]


class TestCheckEdgeCases:
    """Tests for edge cases and error handling."""

    def test_check_empty_list(self, check_tool):
        """Test checking an empty list."""
        result = invoke(check_tool, [])

        assert result["summary"]["total"] == 0
        assert result["summary"]["found"] == 0
        assert result["summary"]["not_found"] == 0
        assert result["summary"]["invalid"] == 0
        assert result["results"] == []

    def test_check_duplicate_names(self, check_tool, catalog):
        """Test checking duplicate names in batch."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        # Check same name twice
        test_name = all_names[0]
        result = invoke(check_tool, [test_name, test_name])

        assert result["summary"]["total"] == 2
        assert result["summary"]["found"] == 2
        # Both results should be for the same name
        assert result["results"][0]["name"] == test_name
        assert result["results"][1]["name"] == test_name

    def test_check_whitespace_handling(self, check_tool, catalog):
        """Test handling of extra whitespace in string input."""
        all_names = catalog.list_names()
        if len(all_names) < 2:
            pytest.skip("Need at least 2 names in catalog")

        # String with extra whitespace
        test_names_str = f"  {all_names[0]}   {all_names[1]}  "
        result = invoke(check_tool, test_names_str)

        # Should handle whitespace gracefully
        assert result["summary"]["total"] == 2
        assert result["results"][0]["name"] == all_names[0]
        assert result["results"][1]["name"] == all_names[1]
