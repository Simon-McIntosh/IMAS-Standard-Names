"""Tests for fetch_standard_names tool.

Validates comprehensive standard name retrieval including:
- Full metadata fetching
- Grammar component breakdown
- Provenance extraction
- Batch fetching
"""

import asyncio

import pytest

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.fetch import FetchTool


def invoke(tool, *args, **kwargs):
    """Helper to run async tool methods."""
    return asyncio.run(tool.fetch_standard_names(*args, **kwargs))


@pytest.fixture
def fetch_tool(sample_catalog):
    """Create FetchTool with sample catalog."""
    return FetchTool(sample_catalog)


@pytest.fixture
def catalog(sample_catalog):
    """Alias for sample_catalog fixture."""
    return sample_catalog


class TestFetchSingleName:
    """Tests for fetching individual standard names."""

    def test_fetch_existing_name(self, fetch_tool, catalog):
        """Test fetching a name that exists in the catalog."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        result = invoke(fetch_tool, test_name)

        assert result["summary"]["total_requested"] == 1
        assert result["summary"]["retrieved"] == 1
        assert result["summary"]["not_found"] == 0
        assert result["summary"]["not_found_names"] == []

        entry = result["entries"][0]
        assert entry["name"] == test_name
        assert "description" in entry
        assert "documentation" in entry
        assert "unit" in entry
        assert "status" in entry
        assert "kind" in entry
        assert "grammar" in entry
        assert "provenance" in entry
        assert "tags" in entry
        assert "links" in entry

    def test_fetch_nonexistent_name(self, fetch_tool):
        """Test fetching a name that doesn't exist."""
        result = invoke(fetch_tool, "nonexistent_standard_name")

        assert result["summary"]["total_requested"] == 1
        assert result["summary"]["retrieved"] == 0
        assert result["summary"]["not_found"] == 1
        assert result["summary"]["not_found_names"] == ["nonexistent_standard_name"]
        assert result["entries"] == []

    def test_fetch_scalar_entry(self, fetch_tool, catalog):
        """Test fetching a scalar entry."""
        all_entries = catalog.list()
        scalars = [e for e in all_entries if e.kind == "scalar"]
        if not scalars:
            pytest.skip("No scalar entries in catalog")

        scalar = scalars[0]
        result = invoke(fetch_tool, scalar.name)

        entry = result["entries"][0]
        assert entry["kind"] == "scalar"
        assert entry["status"] in ["draft", "active", "deprecated", "superseded"]
        assert isinstance(entry["description"], str)
        assert isinstance(entry["unit"], str)

    def test_fetch_vector_entry(self, fetch_tool, catalog):
        """Test fetching a vector entry."""
        all_entries = catalog.list()
        vectors = [e for e in all_entries if e.kind == "vector"]
        if not vectors:
            pytest.skip("No vector entries in catalog")

        vector = vectors[0]
        result = invoke(fetch_tool, vector.name)

        entry = result["entries"][0]
        assert entry["kind"] == "vector"
        assert entry["status"] in ["draft", "active", "deprecated", "superseded"]


class TestFetchMetadata:
    """Tests for comprehensive metadata fetching."""

    def test_fetch_grammar_breakdown(self, fetch_tool, catalog):
        """Test grammar component breakdown."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        result = invoke(fetch_tool, test_name)

        entry = result["entries"][0]
        grammar = entry["grammar"]

        # Grammar should be parsed (or None if parsing failed)
        if grammar is not None:
            assert "base" in grammar
            # Base should always be present
            assert isinstance(grammar["base"], str)
            assert len(grammar["base"]) > 0
            # Grammar dict only contains keys with non-None values
            # so we just verify it's a valid dict with base
            assert isinstance(grammar, dict)

    def test_fetch_provenance(self, fetch_tool, catalog):
        """Test provenance information."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        result = invoke(fetch_tool, test_name)

        entry = result["entries"][0]
        provenance = entry["provenance"]

        assert isinstance(provenance, dict)
        assert "superseded_by" in provenance
        assert "deprecates" in provenance
        assert "derived_from" in provenance
        assert isinstance(provenance["derived_from"], list)

    def test_fetch_with_operator_provenance(self, fetch_tool, catalog):
        """Test fetching entry with operator provenance."""
        # Look for an entry with operator provenance (likely gradient, time_derivative)
        all_entries = catalog.list()
        operator_entries = [
            e
            for e in all_entries
            if e.provenance
            and hasattr(e.provenance, "mode")
            and e.provenance.mode == "operator"  # type: ignore[attr-defined]
        ]
        if not operator_entries:
            pytest.skip("No entries with operator provenance")

        entry_obj = operator_entries[0]
        result = invoke(fetch_tool, entry_obj.name)

        entry = result["entries"][0]
        derived_from = entry["provenance"]["derived_from"]
        assert isinstance(derived_from, list)
        assert len(derived_from) > 0  # Should have a base

    def test_fetch_constraints_and_validity(self, fetch_tool, catalog):
        """Test constraints and validity domain."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        result = invoke(fetch_tool, test_name)

        entry = result["entries"][0]
        assert "constraints" in entry
        assert isinstance(entry["constraints"], list)
        assert "validity_domain" in entry
        assert isinstance(entry["validity_domain"], str)

    def test_fetch_tags_and_links(self, fetch_tool, catalog):
        """Test tags and links."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        result = invoke(fetch_tool, test_name)

        entry = result["entries"][0]
        assert "tags" in entry
        assert isinstance(entry["tags"], list)
        assert "links" in entry
        assert isinstance(entry["links"], list)
        # Links should be list of dicts with url key
        for link in entry["links"]:
            assert isinstance(link, dict)
            assert "url" in link


class TestFetchBatch:
    """Tests for batch fetching multiple names."""

    def test_fetch_multiple_existing(self, fetch_tool, catalog):
        """Test fetching multiple existing names."""
        all_names = catalog.list_names()
        if len(all_names) < 2:
            pytest.skip("Need at least 2 names in catalog")

        test_names = all_names[:2]
        result = invoke(fetch_tool, test_names)

        assert result["summary"]["total_requested"] == 2
        assert result["summary"]["retrieved"] == 2
        assert result["summary"]["not_found"] == 0
        assert len(result["entries"]) == 2

        for entry, expected_name in zip(result["entries"], test_names, strict=True):
            assert entry["name"] == expected_name

    def test_fetch_mixed_batch(self, fetch_tool, catalog):
        """Test batch with mix of existing and nonexistent names."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_names = [
            all_names[0],  # exists
            "nonexistent_name_one",  # doesn't exist
            "nonexistent_name_two",  # doesn't exist
        ]
        result = invoke(fetch_tool, test_names)

        assert result["summary"]["total_requested"] == 3
        assert result["summary"]["retrieved"] == 1
        assert result["summary"]["not_found"] == 2
        assert len(result["entries"]) == 1
        assert result["entries"][0]["name"] == all_names[0]
        assert set(result["summary"]["not_found_names"]) == {
            "nonexistent_name_one",
            "nonexistent_name_two",
        }

    def test_fetch_space_delimited_string(self, fetch_tool, catalog):
        """Test fetching names provided as space-delimited string."""
        all_names = catalog.list_names()
        if len(all_names) < 2:
            pytest.skip("Need at least 2 names in catalog")

        test_names_str = f"{all_names[0]} {all_names[1]}"
        result = invoke(fetch_tool, test_names_str)

        assert result["summary"]["total_requested"] == 2
        assert result["summary"]["retrieved"] == 2
        assert result["entries"][0]["name"] == all_names[0]
        assert result["entries"][1]["name"] == all_names[1]


class TestFetchEdgeCases:
    """Tests for edge cases and error handling."""

    def test_fetch_empty_list(self, fetch_tool):
        """Test fetching an empty list."""
        result = invoke(fetch_tool, [])

        assert result["summary"]["total_requested"] == 0
        assert result["summary"]["retrieved"] == 0
        assert result["summary"]["not_found"] == 0
        assert result["summary"]["not_found_names"] == []
        assert result["entries"] == []

    def test_fetch_duplicate_names(self, fetch_tool, catalog):
        """Test fetching duplicate names in batch."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        result = invoke(fetch_tool, [test_name, test_name])

        assert result["summary"]["total_requested"] == 2
        assert result["summary"]["retrieved"] == 2
        # Should return two entries, even though they're the same
        assert len(result["entries"]) == 2
        assert result["entries"][0]["name"] == test_name
        assert result["entries"][1]["name"] == test_name

    def test_fetch_all_nonexistent(self, fetch_tool):
        """Test fetching only nonexistent names."""
        test_names = ["fake_one", "fake_two", "fake_three"]
        result = invoke(fetch_tool, test_names)

        assert result["summary"]["total_requested"] == 3
        assert result["summary"]["retrieved"] == 0
        assert result["summary"]["not_found"] == 3
        assert set(result["summary"]["not_found_names"]) == set(test_names)
        assert result["entries"] == []

    def test_fetch_whitespace_handling(self, fetch_tool, catalog):
        """Test handling of extra whitespace in string input."""
        all_names = catalog.list_names()
        if len(all_names) < 2:
            pytest.skip("Need at least 2 names in catalog")

        test_names_str = f"  {all_names[0]}   {all_names[1]}  "
        result = invoke(fetch_tool, test_names_str)

        assert result["summary"]["total_requested"] == 2
        assert result["summary"]["retrieved"] == 2
        assert result["entries"][0]["name"] == all_names[0]
        assert result["entries"][1]["name"] == all_names[1]


class TestFetchComparison:
    """Tests comparing fetch results with catalog data."""

    def test_fetch_matches_catalog_get(self, fetch_tool, catalog):
        """Test that fetch returns same data as catalog.get()."""
        all_names = catalog.list_names()
        if not all_names:
            pytest.skip("No names in catalog")

        test_name = all_names[0]
        catalog_entry = catalog.get(test_name)
        fetch_result = invoke(fetch_tool, test_name)

        assert fetch_result["summary"]["retrieved"] == 1
        fetched_entry = fetch_result["entries"][0]

        # Compare key fields
        assert fetched_entry["name"] == catalog_entry.name
        assert fetched_entry["description"] == catalog_entry.description
        assert fetched_entry["documentation"] == catalog_entry.documentation
        assert fetched_entry["unit"] == str(catalog_entry.unit)
        assert fetched_entry["status"] == catalog_entry.status
        assert fetched_entry["kind"] == catalog_entry.kind
