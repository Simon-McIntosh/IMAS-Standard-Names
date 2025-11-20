"""Tests for metadata kind standard name entries.

Tests cover:
- Valid metadata entry creation
- Unit field exclusion from metadata entries
- Provenance validation (should be rejected)
- Schema validation
- Catalog round-trip
- Integration with tools (fetch, list, search)
"""

import pytest

from imas_standard_names.models import (
    StandardNameMetadataEntry,
    create_standard_name_entry,
)


def test_metadata_entry_basic_creation():
    """Test creating a basic metadata entry."""
    entry = StandardNameMetadataEntry(
        name="test_metadata",
        description="Test metadata entry.",
        documentation="Extended documentation for test metadata entry.",
        tags=["equilibrium"],
    )
    assert entry.kind == "metadata"
    assert entry.name == "test_metadata"
    assert entry.description == "Test metadata entry."
    # Metadata entries don't expose unit attribute


def test_metadata_entry_without_unit():
    """Test that metadata entries work without unit field."""
    entry_dict = {
        "name": "plasma_boundary",
        "kind": "metadata",
        "description": "Definition of plasma boundary.",
        "documentation": "Metadata defining the plasma boundary surface.",
        "tags": ["equilibrium"],
    }
    entry = create_standard_name_entry(entry_dict)
    assert isinstance(entry, StandardNameMetadataEntry)
    assert entry.kind == "metadata"
    # Metadata entries don't have unit field exposed


def test_metadata_entry_model_dump_excludes_unit():
    """Test that model_dump excludes unit field for metadata entries."""
    entry = StandardNameMetadataEntry(
        name="test_metadata",
        description="Test metadata entry.",
        documentation="Extended documentation.",
        tags=["equilibrium"],
    )
    dumped = entry.model_dump()
    # Check that unit is excluded from serialization
    assert "unit" not in dumped
    assert dumped["kind"] == "metadata"
    assert dumped["name"] == "test_metadata"


def test_metadata_entry_with_documentation():
    """Test metadata entry with full documentation."""
    entry = StandardNameMetadataEntry(
        name="confined_region",
        description="Definition of confined plasma region.",
        documentation=(
            "The confined region refers to the volume enclosed by the last "
            "closed flux surface where particles and energy are magnetically confined."
        ),
        tags=["equilibrium"],
        status="draft",
    )
    assert entry.kind == "metadata"
    assert "confined" in entry.documentation
    assert entry.status == "draft"


def test_metadata_entry_rejects_provenance():
    """Test that metadata entries cannot have provenance."""
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        StandardNameMetadataEntry(
            name="test_metadata",
            description="Test metadata entry.",
            documentation="Documentation for test metadata.",
            tags=["equilibrium"],
            provenance={
                "mode": "operator",
                "operators": ["gradient"],
                "base": "electron_temperature",
            },
        )


def test_metadata_entry_with_links():
    """Test metadata entry with internal and external links."""
    entry = StandardNameMetadataEntry(
        name="plasma_boundary",
        description="Definition of plasma boundary.",
        documentation="Metadata defining the plasma boundary with references.",
        tags=["equilibrium"],
        links=[
            "name:minor_radius_of_flux_surface",
            "https://example.org/plasma-boundary-definition",
        ],
    )
    assert len(entry.links) == 2
    assert entry.links[0].startswith("name:")
    assert entry.links[1].startswith("https://")


def test_metadata_entry_discriminator():
    """Test that discriminated union properly routes to metadata entry."""
    # Test with explicit kind
    data = {
        "name": "test_metadata",
        "kind": "metadata",
        "description": "Test metadata entry.",
        "documentation": "Documentation for discriminator test.",
        "tags": ["equilibrium"],
    }
    entry = create_standard_name_entry(data)
    assert isinstance(entry, StandardNameMetadataEntry)
    assert entry.kind == "metadata"


def test_metadata_entry_all_optional_fields():
    """Test metadata entry with all optional fields populated."""
    entry = StandardNameMetadataEntry(
        name="scrape_off_layer",
        description="Definition of scrape-off layer region.",
        documentation="Region outside the last closed flux surface.",
        status="active",
        tags=["equilibrium", "spatial-profile"],
        links=["name:plasma_boundary"],
        validity_domain="edge_plasma",
        constraints=["flux_surface > separatrix"],
    )
    assert entry.kind == "metadata"
    assert entry.status == "active"
    assert "spatial-profile" in entry.tags
    assert len(entry.constraints) == 1
    assert entry.validity_domain == "edge_plasma"


def test_metadata_entry_governance_fields():
    """Test metadata entry with governance fields."""
    entry = StandardNameMetadataEntry(
        name="old_plasma_boundary_definition",
        description="Deprecated definition of plasma boundary.",
        documentation="Old definition superseded by newer standard.",
        tags=["equilibrium"],
        status="deprecated",
        superseded_by="plasma_boundary",
    )
    assert entry.status == "deprecated"
    assert entry.superseded_by == "plasma_boundary"
