"""Tests for description validation in create and edit tools."""

import pytest

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.create import CreateTool
from imas_standard_names.tools.validate_catalog import ValidateCatalogTool
from imas_standard_names.validation.description import validate_description


@pytest.fixture
def test_entry():
    """Create a minimal test entry."""
    return {
        "name": "test_quantity",
        "kind": "scalar",
        "unit": "m",
        "status": "draft",
        "tags": ["equilibrium", "spatial-profile"],  # Primary + secondary tags
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


class TestCreateToolValidation:
    """Test validation integration in create tool."""

    @pytest.mark.anyio
    async def test_create_with_clean_description(self, temp_create_tool, test_entry):
        """Creating entry with clean description should succeed without warnings."""
        result = await temp_create_tool.create_standard_names(
            entries=[test_entry], dry_run=True
        )
        assert result["summary"]["total"] == 1
        assert result["summary"]["successful"] == 1
        # Check first result entry
        assert "warnings" not in result["results"][0]

    @pytest.mark.anyio
    async def test_create_with_problematic_description(
        self, temp_create_tool, test_entry
    ):
        """Creating entry with problematic description should include warnings."""
        test_entry["description"] = "Radial profile of plasma temperature"
        result = await temp_create_tool.create_standard_names(
            entries=[test_entry], dry_run=True
        )
        assert result["summary"]["total"] == 1
        assert result["summary"]["successful"] == 1
        # Check first result entry
        assert "warnings" in result["results"][0]
        assert len(result["results"][0]["warnings"]) > 0

    @pytest.mark.anyio
    async def test_batch_create_mixed_descriptions(self, temp_create_tool, test_entry):
        """Batch create with mixed descriptions attaches warnings correctly."""
        clean_entry = test_entry.copy()
        clean_entry["name"] = "clean_quantity"

        problematic_entry = test_entry.copy()
        problematic_entry["name"] = "problematic_quantity"
        problematic_entry["description"] = "Radial profile of density"

        result = await temp_create_tool.create_standard_names(
            entries=[clean_entry, problematic_entry], dry_run=True
        )

        assert result["summary"]["successful"] == 2
        # Clean entry should have no warnings
        assert "warnings" not in result["results"][0]
        # Problematic entry should have warnings
        assert "warnings" in result["results"][1]


class TestEditToolValidation:
    """Test validation integration in edit tool."""

    @pytest.fixture
    async def edit_catalog_with_entry(
        self, temp_catalog, temp_edit_catalog, temp_create_tool
    ):
        """Create an EditCatalog with a test entry added via CreateTool."""
        # Use create tool to add the entry properly
        entry_data = {
            "name": "test_quantity",
            "kind": "scalar",
            "unit": "m",
            "status": "draft",
            "tags": ["equilibrium", "spatial-profile"],
            "description": "Clean description",
            "documentation": "Clean description for edit validation testing.",
        }
        # Create entry (not dry run, so it's added to catalog)
        await temp_create_tool.create_standard_names(entries=[entry_data])

        # Reset baseline so modify operations show changes
        temp_edit_catalog._baseline_snapshot = {
            name: entry.model_copy(deep=True)
            for name, entry in ((e.name, e) for e in temp_catalog.list())
        }

        return temp_edit_catalog

    @pytest.mark.anyio
    async def test_modify_with_clean_description(self, edit_catalog_with_entry):
        """Modifying to a clean description should not generate warnings."""
        model, warnings = edit_catalog_with_entry.modify(
            "test_quantity", updates={"description": "Updated clean description"}
        )
        assert model.description == "Updated clean description"
        assert warnings is None

    @pytest.mark.anyio
    async def test_modify_with_problematic_description(self, edit_catalog_with_entry):
        """Modifying to problematic description should generate warnings."""
        model, warnings = edit_catalog_with_entry.modify(
            "test_quantity",
            updates={"description": "Radial profile of plasma temperature"},
        )
        assert model.description == "Radial profile of plasma temperature"
        assert warnings is not None
        assert len(warnings) > 0
        assert any("spatial-profile" in w["message"] for w in warnings)

    @pytest.mark.anyio
    async def test_modify_non_description_field_no_validation(
        self, edit_catalog_with_entry
    ):
        """Modifying non-description fields should not trigger validation."""
        model, warnings = edit_catalog_with_entry.modify(
            "test_quantity", updates={"unit": "kg"}
        )
        assert model.unit == "kg"
        assert warnings is None

    @pytest.mark.anyio
    async def test_full_replacement_with_problematic_description(
        self, edit_catalog_with_entry
    ):
        """Full model replacement with problematic description should warn."""
        new_model_data = {
            "name": "test_quantity",
            "kind": "scalar",
            "unit": "m",
            "status": "draft",
            "tags": ["equilibrium", "spatial-profile"],
            "description": "Radial profile of electron density",
            "documentation": "Radial profile of electron density for full replacement testing.",
        }
        model, warnings = edit_catalog_with_entry.modify(
            "test_quantity", model_data=new_model_data
        )
        assert warnings is not None
        assert len(warnings) > 0


class TestValidateCatalogToolIntegration:
    """Test description validation integration in validate_catalog tool."""

    @pytest.mark.anyio
    async def test_validate_catalog_with_descriptions_check(
        self, temp_catalog, temp_create_tool
    ):
        """Test that validate_catalog detects description issues."""
        # Add entry with problematic description
        problematic_entry = {
            "name": "test_problematic",
            "kind": "scalar",
            "unit": "m",
            "status": "draft",
            "tags": ["equilibrium", "spatial-profile"],
            "description": "Radial profile of plasma temperature",
            "documentation": "Radial profile of plasma temperature for description validation testing.",
        }
        await temp_create_tool.create_standard_names(entries=[problematic_entry])

        # Add entry with clean description
        clean_entry = {
            "name": "test_clean",
            "kind": "scalar",
            "unit": "m",
            "status": "draft",
            "tags": ["equilibrium"],
            "description": "Plasma temperature distribution",
            "documentation": "Plasma temperature distribution for description validation testing.",
        }
        await temp_create_tool.create_standard_names(entries=[clean_entry])

        # Run validation with description checks
        validate_tool = ValidateCatalogTool(temp_catalog)
        result = await validate_tool.validate_catalog(
            scope="persisted", checks=["descriptions"], include_warnings=True
        )

        # Verify structure
        assert "summary" in result
        assert "warnings" in result
        assert "issues_by_category" in result

        # Should have warnings for problematic entry
        assert result["summary"]["total_entries"] == 2
        assert len(result["warnings"]) > 0

        # Check that warning is for the problematic entry
        warning_names = [w["name"] for w in result["warnings"]]
        assert "test_problematic" in warning_names

    @pytest.mark.anyio
    async def test_validate_catalog_descriptions_disabled(
        self, temp_catalog, temp_create_tool
    ):
        """Test that description checks can be disabled."""
        # Add entry with problematic description
        entry = {
            "name": "test_entry",
            "kind": "scalar",
            "unit": "m",
            "status": "draft",
            "tags": ["equilibrium", "spatial-profile"],
            "description": "Radial profile of density",
        }
        await temp_create_tool.create_standard_names(entries=[entry])

        # Run validation WITHOUT description checks
        validate_tool = ValidateCatalogTool(temp_catalog)
        result = await validate_tool.validate_catalog(
            scope="persisted", checks=["grammar"], include_warnings=True
        )

        # Should not have description warnings
        desc_warnings = [
            w for w in result["warnings"] if w["category"] == "descriptions"
        ]
        assert len(desc_warnings) == 0
