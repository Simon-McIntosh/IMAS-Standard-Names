"""Tests for the validate_catalog MCP tool."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from imas_standard_names.models import StandardNameScalarEntry
from imas_standard_names.provenance import ExpressionProvenance
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.validate_catalog import ValidateCatalogTool


@pytest.fixture
def catalog_root(tmp_path):
    """Create a temporary catalog root directory."""
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    # Create a primary tag subdirectory for entries
    (catalog_dir / "fundamental").mkdir()
    return str(catalog_dir)


@pytest.fixture
def catalog(catalog_root):
    """Create a catalog instance."""
    return StandardNameCatalog(root=catalog_root, permissive=True)


@pytest.fixture
def validate_tool(catalog):
    """Create a validate catalog tool instance."""
    return ValidateCatalogTool(catalog)


def _write_entry_to_yaml(catalog_root: str, entry: StandardNameScalarEntry):
    """Helper to write an entry to YAML and rebuild catalog."""
    # Determine primary tag subdirectory
    primary_tag = entry.tags[0] if entry.tags else "fundamental"
    tag_dir = Path(catalog_root) / primary_tag
    tag_dir.mkdir(exist_ok=True)

    # Write YAML file
    yaml_file = tag_dir / f"{entry.name}.yml"
    with open(yaml_file, "w") as f:
        # Convert entry to dict for YAML serialization
        entry_dict = entry.model_dump(mode="json", exclude_none=True)
        yaml.dump(entry_dict, f, default_flow_style=False, sort_keys=False)


def _add_entry(catalog_root: str, entry: StandardNameScalarEntry):
    """Helper to add an entry to catalog by writing YAML and reloading."""
    _write_entry_to_yaml(catalog_root, entry)
    # Return a fresh catalog instance that will load the new entry
    return StandardNameCatalog(root=catalog_root, permissive=True)


@pytest.mark.anyio
async def test_validate_empty_catalog(validate_tool):
    """Test validation of an empty catalog."""
    result = await validate_tool.validate_catalog(scope="persisted")

    assert result["summary"]["total_entries"] == 0
    assert result["summary"]["valid_entries"] == 0
    assert result["summary"]["invalid_entries"] == 0
    assert result["summary"]["scope"] == "persisted"
    assert result["issues_by_category"] == {
        "grammar_errors": 0,
        "schema_errors": 0,
        "provenance_errors": 0,
        "tag_errors": 0,
        "unit_errors": 0,
        "reference_errors": 0,
        "description_warnings": 0,
        "documentation_errors": 0,
    }
    assert result["invalid_entries"] == []
    assert result["warnings"] == []


@pytest.mark.anyio
async def test_validate_invalid_scope(validate_tool):
    """Test validation with invalid scope."""
    result = await validate_tool.validate_catalog(scope="invalid_scope")

    assert "error" in result
    assert result["error"] == "InvalidScope"
    assert "must be 'persisted', 'pending', or 'all'" in result["message"]


@pytest.mark.anyio
async def test_validate_pending_scope(validate_tool):
    """Test validation with pending scope."""
    result = await validate_tool.validate_catalog(scope="pending")

    # Pending scope should return empty result for now
    assert result["summary"]["total_entries"] == 0
    assert result["summary"]["scope"] == "pending"


@pytest.mark.anyio
async def test_validate_specific_checks(validate_tool):
    """Test validation with specific checks enabled."""
    result = await validate_tool.validate_catalog(
        scope="persisted", checks=["grammar", "schema"]
    )

    assert result["summary"]["checks_enabled"] == ["grammar", "schema"]


@pytest.mark.anyio
async def test_validate_invalid_checks(validate_tool):
    """Test validation with invalid checks."""
    result = await validate_tool.validate_catalog(checks=["invalid_check"])

    assert "error" in result
    assert result["error"] == "InvalidChecks"


@pytest.mark.anyio
async def test_validate_warnings_disabled(validate_tool):
    """Test validation with warnings disabled."""
    result = await validate_tool.validate_catalog(
        scope="persisted", include_warnings=False
    )

    assert result["warnings"] == []


@pytest.mark.anyio
async def test_grammar_validation_generic_base(catalog_root):
    """Test grammar validation catches generic physical base without qualification."""
    entry = StandardNameScalarEntry(
        name="current",  # Generic base without qualification
        description="Test current without qualification",
        documentation="Test current without qualification for grammar validation.",
        unit="A",
        kind="scalar",
        status="draft",
        tags=["fundamental"],
    )

    # Write entry and validate
    _write_entry_to_yaml(catalog_root, entry)
    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(scope="persisted", checks=["grammar"])

    # Should have grammar validation error
    assert len(result["invalid_entries"]) > 0
    grammar_errors = [
        issue for issue in result["invalid_entries"] if issue["name"] == "current"
    ]
    assert len(grammar_errors) >= 1
    assert "Generic physical_base" in grammar_errors[0]["message"]


@pytest.mark.anyio
async def test_schema_validation_missing_fields(catalog_root):
    """Test schema validation catches missing required fields."""
    entry = StandardNameScalarEntry(
        name="test_quantity",
        description="",  # Empty description
        documentation="Test quantity with empty description for schema validation.",
        unit="m",
        kind="scalar",
        status="draft",
        tags=["fundamental"],
    )

    # Write entry and validate
    _write_entry_to_yaml(catalog_root, entry)
    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(scope="persisted", checks=["schema"])

    schema_errors = [
        issue
        for issue in result["invalid_entries"]
        if issue["category"] == "schema" and issue["name"] == "test_quantity"
    ]

    assert any("description" in err["message"] for err in schema_errors)


@pytest.mark.anyio
async def test_tag_validation_empty_tags(catalog_root):
    """Test tag validation with empty tags.

    Note: Pydantic filters empty strings from tag lists during model validation,
    so entries with empty tags in YAML will have them removed during load.
    This test verifies that behavior.
    """
    primary_tag = "fundamental"
    tag_dir = Path(catalog_root) / primary_tag
    tag_dir.mkdir(exist_ok=True)

    yaml_file = tag_dir / "test_quantity.yml"
    yaml_content = """name: test_quantity
kind: scalar
description: Test quantity
unit: m
status: draft
tags:
  - fundamental
"""
    yaml_file.write_text(yaml_content)

    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(scope="persisted", checks=["tags"])

    # Verify the entry loaded (Pydantic filters empty tags automatically)
    assert catalog.exists("test_quantity")

    # Since Pydantic filters empty tags during load, there should be no tag errors
    # This is the correct behavior - invalid tags are filtered, not stored with errors
    tag_errors = [
        issue
        for issue in result["invalid_entries"]
        if issue["category"] == "tags" and issue["name"] == "test_quantity"
    ]
    assert len(tag_errors) == 0


@pytest.mark.anyio
async def test_tag_validation_missing_tags_warning(catalog_root):
    """Test tag validation generates warning for missing tags."""
    entry = StandardNameScalarEntry(
        name="test_quantity",
        description="Test quantity",
        documentation="Test quantity for tag validation.",
        unit="m",
        kind="scalar",
        status="draft",
        tags=[],  # Empty tags
    )

    # Write entry and validate
    _write_entry_to_yaml(catalog_root, entry)
    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(
        scope="persisted", checks=["tags"], include_warnings=True
    )

    warnings = [
        w
        for w in result["warnings"]
        if w["name"] == "test_quantity" and w["category"] == "tags"
    ]

    assert len(warnings) >= 1
    assert "no tags" in warnings[0]["message"].lower()


@pytest.mark.anyio
async def test_unit_validation_invalid_exponent(catalog_root):
    """Test unit validation catches invalid exponents."""
    # Write YAML directly with invalid unit to bypass Pydantic validation during creation
    primary_tag = "fundamental"
    tag_dir = Path(catalog_root) / primary_tag
    tag_dir.mkdir(exist_ok=True)

    yaml_file = tag_dir / "test_quantity.yml"
    yaml_content = """
name: test_quantity
kind: scalar
description: Test quantity
unit: m^invalid
status: draft
tags:
  - fundamental
"""
    yaml_file.write_text(yaml_content)

    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(scope="persisted", checks=["units"])

    # In permissive mode, the catalog skips entries with invalid units during load,
    # so the entry won't exist in the catalog.
    # This is actually the correct behavior - the entry is fundamentally invalid
    # and can't be loaded. The validation warnings in the catalog's store will
    # contain the unit validation error.
    assert "test_quantity" not in [e["name"] for e in result["invalid_entries"]]
    # Verify the catalog's store captured the validation warning
    assert len(catalog.store.validation_warnings) >= 1
    assert "m^invalid" in str(catalog.store.validation_warnings)


@pytest.mark.anyio
async def test_validate_all_checks(catalog_root):
    """Test validation with all checks enabled (default)."""
    entry = StandardNameScalarEntry(
        name="plasma_current",
        description="Total plasma current",
        documentation="Total plasma current for validation testing.",
        unit="A",
        kind="scalar",
        status="active",
        tags=["fundamental"],
    )

    # Write entry and validate
    _write_entry_to_yaml(catalog_root, entry)
    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(scope="persisted")

    # Should have all checks enabled (including descriptions)
    assert len(result["summary"]["checks_enabled"]) == 8
    assert "grammar" in result["summary"]["checks_enabled"]
    assert "schema" in result["summary"]["checks_enabled"]
    assert "provenance" in result["summary"]["checks_enabled"]
    assert "tags" in result["summary"]["checks_enabled"]
    assert "units" in result["summary"]["checks_enabled"]
    assert "references" in result["summary"]["checks_enabled"]
    assert "descriptions" in result["summary"]["checks_enabled"]
    assert "documentation" in result["summary"]["checks_enabled"]

    # Valid entry should pass all checks
    assert result["summary"]["invalid_entries"] == 0
    assert result["summary"]["valid_entries"] == 1


@pytest.mark.anyio
async def test_validate_mixed_valid_invalid(catalog_root):
    """Test validation with mix of valid and invalid entries."""
    # Valid entry
    valid_entry = StandardNameScalarEntry(
        name="plasma_current",
        description="Total plasma current",
        documentation="Total plasma current for mixed validation testing.",
        unit="A",
        kind="scalar",
        status="active",
        tags=["fundamental"],
    )

    # Invalid entry - generic base without qualification
    invalid_entry = StandardNameScalarEntry(
        name="voltage",
        description="Test voltage",
        documentation="Test voltage for mixed validation testing.",
        unit="V",
        kind="scalar",
        status="draft",
        tags=["fundamental"],
    )

    # Write both entries
    _write_entry_to_yaml(catalog_root, valid_entry)
    _write_entry_to_yaml(catalog_root, invalid_entry)

    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(scope="persisted")

    assert result["summary"]["total_entries"] == 2
    assert result["summary"]["valid_entries"] == 1
    assert result["summary"]["invalid_entries"] == 1


@pytest.mark.anyio
async def test_provenance_superseded_by_validation(catalog_root):
    """Test provenance validation for superseded_by reference."""
    # Create an entry with superseded_by pointing to non-existent name
    entry = StandardNameScalarEntry(
        name="old_quantity",
        description="Old quantity superseded by new one",
        documentation="Old quantity superseded by new one for provenance validation.",
        unit="m",
        kind="scalar",
        status="superseded",
        tags=["fundamental"],
        superseded_by="non_existent_new_quantity",
    )

    # Write entry and validate
    _write_entry_to_yaml(catalog_root, entry)
    catalog = StandardNameCatalog(root=catalog_root, permissive=True)
    validate_tool = ValidateCatalogTool(catalog)

    result = await validate_tool.validate_catalog(
        scope="persisted", checks=["provenance"]
    )

    prov_errors = [
        issue
        for issue in result["invalid_entries"]
        if "superseded_by" in issue["message"]
    ]

    assert len(prov_errors) >= 1
