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

    def test_unicode_greek_symbol_clean(self, test_entry):
        """Unicode Greek symbols are the canonical description notation."""
        test_entry["description"] = (
            "Toroidal angle φ in the (R, φ, Z) coordinate frame; "
            "poloidal angle θ and normalized radius ρ."
        )
        issues = validate_description(test_entry)
        assert issues == []


class TestCocosMention:
    """Sign/coordinate conventions are stated explicitly, never by COCOS number."""

    def test_cocos_in_documentation_warns(self, test_entry):
        """A COCOS mention in documentation is flagged."""
        test_entry["documentation"] = (
            "Safety factor. Sign convention (COCOS=11): positive when ..."
        )
        issues = validate_description(test_entry)
        assert any(
            issue["pattern"] == "cocos" and issue["field"] == "documentation"
            for issue in issues
        )

    def test_cocos_in_description_warns(self, test_entry):
        """A COCOS mention in the description is flagged."""
        test_entry["description"] = "Poloidal flux in the COCOS 17 convention."
        issues = validate_description(test_entry)
        assert any(issue["pattern"] == "cocos" for issue in issues)

    def test_explicit_convention_no_cocos_clean(self, test_entry):
        """Stating the convention explicitly, without a COCOS number, is clean."""
        test_entry["documentation"] = (
            "Positive when the toroidal magnetic field and plasma current are "
            "parallel; reverses if either alone is reversed."
        )
        issues = validate_description(test_entry)
        assert not any(issue["pattern"] == "cocos" for issue in issues)

    def test_greek_word_nudges_info(self, test_entry):
        """A spelled-out Greek letter word gets an info nudge toward the symbol."""
        test_entry["description"] = "Toroidal angle phi in the (R, phi, Z) frame."
        issues = validate_description(test_entry)
        assert any(
            issue["severity"] == "info" and issue.get("pattern") == "phi"
            for issue in issues
        )
        assert not any(issue["severity"] == "warning" for issue in issues)

    def test_clean_plain_description_no_notation_warning(self, test_entry):
        """A clean plain-text description produces no notation warnings."""
        test_entry["description"] = "Electron temperature at the magnetic axis."
        issues = validate_description(test_entry)
        assert issues == []


class TestUnitRestatement:
    """Documentation prose must not restate the entry's canonical unit."""

    def test_unit_in_prose_warns(self, test_entry):
        test_entry["unit"] = "m^-3"
        test_entry["documentation"] = "Number of particles per unit volume, in m^-3."
        issues = validate_description(test_entry)
        assert any(
            issue["severity"] == "warning"
            and issue["field"] == "documentation"
            and issue["pattern"] == "m^-3"
            for issue in issues
        )

    def test_unit_inside_math_region_clean(self, test_entry):
        test_entry["unit"] = "m^-3"
        test_entry["documentation"] = (
            "Electron number density $n_e$ with $n_e [m^-3]$ defined as "
            "$$n_e = N / V, \\quad [m^-3]$$ over the plasma volume."
        )
        issues = validate_description(test_entry)
        assert issues == []

    def test_single_letter_unit_inside_word_clean(self, test_entry):
        test_entry["unit"] = "m"
        test_entry["documentation"] = "Magnetic measurements of the plasma column."
        issues = validate_description(test_entry)
        assert issues == []

    def test_single_letter_unit_standalone_warns(self, test_entry):
        test_entry["unit"] = "m"
        test_entry["documentation"] = "Distance of 3 m from the magnetic axis."
        issues = validate_description(test_entry)
        assert any(
            issue["field"] == "documentation" and issue["pattern"] == "m"
            for issue in issues
        )

    def test_unit_embedded_in_compound_unit_clean(self, test_entry):
        test_entry["unit"] = "m^-3"
        test_entry["documentation"] = "Mass density is reported separately in kg.m^-3."
        issues = validate_description(test_entry)
        assert issues == []

    def test_dimensionless_unit_ignored(self, test_entry):
        test_entry["unit"] = "1"
        test_entry["documentation"] = "Ratio near 1 across the profile."
        issues = validate_description(test_entry)
        assert issues == []

    def test_missing_documentation_clean(self, test_entry):
        test_entry["unit"] = "m^-3"
        test_entry["documentation"] = ""
        issues = validate_description(test_entry)
        assert issues == []
