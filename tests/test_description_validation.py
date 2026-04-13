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
        "physics_domain": "equilibrium",
        "tags": ["spatial-profile"],  # Primary + secondary tags
        "description": "Test description",
        "documentation": "Test description for validation testing.",
    }


class TestDescriptionValidation:
    """Test description validation helper function."""

    def test_clean_description_no_warnings(self, test_entry):
        """Clean description should not generate warnings."""
        issues = validate_description(test_entry)
        assert issues == []

    def test_spatial_profile_redundancy(self, test_entry):
        """Detect 'radial profile' redundancy with spatial-profile tag."""
        test_entry["description"] = "Radial profile of plasma temperature"
        issues = validate_description(test_entry)
        assert len(issues) >= 1  # May match multiple patterns
        assert any("spatial-profile" in issue["message"] for issue in issues)

    def test_time_dependent_redundancy(self, test_entry):
        """Detect time-related phrases with time-dependent tag."""
        test_entry["tags"] = ["time-dependent"]
        test_entry["description"] = "Time evolution of plasma temperature"
        issues = validate_description(test_entry)
        assert len(issues) == 1
        assert "time-dependent" in issues[0]["message"]

    def test_flux_surface_average_redundancy(self, test_entry):
        """Detect 'flux surface average' redundancy with tag."""
        test_entry["tags"] = ["flux-surface-average"]
        test_entry["description"] = "Flux surface average of pressure"
        issues = validate_description(test_entry)
        assert len(issues) == 1
        assert "flux-surface-average" in issues[0]["message"]

    def test_volume_average_redundancy(self, test_entry):
        """Detect 'volume average' redundancy with tag."""
        test_entry["tags"] = ["volume-average"]
        test_entry["description"] = "Volume averaged density"
        issues = validate_description(test_entry)
        assert len(issues) == 1
        assert "volume-average" in issues[0]["message"]

    def test_line_integrated_redundancy(self, test_entry):
        """Detect 'line integrated' redundancy with tag."""
        test_entry["tags"] = ["line-integrated"]
        test_entry["description"] = "Line integrated electron density"
        issues = validate_description(test_entry)
        assert len(issues) == 1
        assert "line-integrated" in issues[0]["message"]

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
