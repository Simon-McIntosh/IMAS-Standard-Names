"""Tests for description validation."""

import pytest

from imas_standard_names.validation.description import validate_description


@pytest.fixture
def test_entry():
    """Create a minimal test entry."""
    return {
        "name": "test_quantity",
        "kind": "scalar",
        "unit": "m",
        "status": "draft",
        "description": "Test description",
        "documentation": "Test description for validation testing.",
    }


class TestDescriptionValidation:
    """Test description validation helper function."""

    def test_clean_description_no_warnings(self, test_entry):
        """Clean description should not generate warnings."""
        issues = validate_description(test_entry)
        assert issues == []

    def test_structural_phrase_detection(self, test_entry):
        """Detect structural metadata phrases."""
        test_entry["description"] = "Data stored on profiles_1d grid"
        issues = validate_description(test_entry)
        assert len(issues) >= 1  # May match multiple patterns
        assert any("stored on" in issue.get("pattern", "") for issue in issues)

    def test_multiple_issues(self, test_entry):
        """Detect multiple issues in one description."""
        test_entry["description"] = "Radial profile stored on profiles_1d"
        issues = validate_description(test_entry)
        assert len(issues) == 2
