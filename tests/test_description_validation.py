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


class TestDescriptionNotation:
    """Descriptions are plain text; LaTeX/math markup belongs in documentation."""

    def test_latex_inline_math_warns(self, test_entry):
        """Inline LaTeX math ($\\phi$) in a description is flagged."""
        test_entry["description"] = "Toroidal angle $\\phi$ of the field line."
        issues = validate_description(test_entry)
        assert any(issue["severity"] == "warning" for issue in issues)
        assert any(issue["field"] == "description" for issue in issues)

    def test_dollar_delimiter_warns(self, test_entry):
        """A bare $ math delimiter is flagged."""
        test_entry["description"] = "Pressure $p$ at the boundary."
        issues = validate_description(test_entry)
        assert any(
            issue["severity"] == "warning" and "$" in issue.get("pattern", "")
            for issue in issues
        )

    def test_latex_backslash_command_warns(self, test_entry):
        """A LaTeX backslash command is flagged even without $ delimiters."""
        test_entry["description"] = "Gradient \\nabla of the temperature."
        issues = validate_description(test_entry)
        assert any(
            issue["severity"] == "warning" and "\\nabla" in issue.get("pattern", "")
            for issue in issues
        )

    def test_unicode_greek_warns(self, test_entry):
        """A Unicode Greek character is flagged."""
        test_entry["description"] = "Toroidal angle φ of the field line."
        issues = validate_description(test_entry)
        assert any(
            issue["severity"] == "warning" and issue["field"] == "description"
            for issue in issues
        )

    def test_greek_word_no_warning(self, test_entry):
        """Greek letters written as words (phi, theta, rho) are correct."""
        test_entry["description"] = (
            "Toroidal angle phi in the (R, phi, Z) coordinate frame; "
            "poloidal angle theta and normalized radius rho."
        )
        issues = validate_description(test_entry)
        assert issues == []

    def test_clean_plain_description_no_notation_warning(self, test_entry):
        """A clean plain-text description produces no notation warnings."""
        test_entry["description"] = "Electron temperature at the magnetic axis."
        issues = validate_description(test_entry)
        assert issues == []
