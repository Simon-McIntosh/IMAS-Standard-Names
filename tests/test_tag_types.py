"""Tests for tag type generation and validation.

Tests cover:
- Tag type generation from tags.yml
- Tag validation in models
- Tag vocabulary structure
- Primary/secondary tag constraints
"""

import pytest
from pydantic import ValidationError

from imas_standard_names.grammar.tag_types import (
    PRIMARY_TAG_DESCRIPTIONS,
    PRIMARY_TAGS,
    SECONDARY_TAG_DESCRIPTIONS,
    SECONDARY_TAGS,
    PrimaryTag,
    SecondaryTag,
    Tag,
)
from imas_standard_names.grammar_codegen.tag_spec import TagSpec
from imas_standard_names.models import (
    StandardNameScalarEntry,
    StandardNameVectorEntry,
    create_standard_name_entry,
)

# ============================================================================
# Tag Type Generation Tests
# ============================================================================


def test_tag_spec_loads_from_yaml():
    """Test that TagSpec can load tags.yml successfully."""
    spec = TagSpec.load()
    assert len(spec.primary_tags) > 0
    assert len(spec.secondary_tags) > 0
    assert "fundamental" in spec.primary_tags
    assert "measured" in spec.secondary_tags


def test_tag_spec_has_metadata():
    """Test that TagSpec preserves metadata from YAML."""
    spec = TagSpec.load()

    # Primary tags should have descriptions
    assert len(spec.primary_metadata) > 0
    assert "fundamental" in spec.primary_metadata
    assert "description" in spec.primary_metadata["fundamental"]

    # Secondary tags should have descriptions
    assert len(spec.secondary_metadata) > 0
    assert "measured" in spec.secondary_metadata
    assert "description" in spec.secondary_metadata["measured"]


def test_generated_primary_tags_constant():
    """Test that PRIMARY_TAGS constant is generated correctly."""
    assert isinstance(PRIMARY_TAGS, tuple)
    assert len(PRIMARY_TAGS) > 0
    assert "fundamental" in PRIMARY_TAGS
    assert "equilibrium" in PRIMARY_TAGS
    assert "core-physics" in PRIMARY_TAGS


def test_generated_secondary_tags_constant():
    """Test that SECONDARY_TAGS constant is generated correctly."""
    assert isinstance(SECONDARY_TAGS, tuple)
    assert len(SECONDARY_TAGS) > 0
    assert "measured" in SECONDARY_TAGS
    assert "time-dependent" in SECONDARY_TAGS
    assert "spatial-profile" in SECONDARY_TAGS


def test_generated_tag_descriptions():
    """Test that tag descriptions are generated."""
    # Primary tag descriptions
    assert isinstance(PRIMARY_TAG_DESCRIPTIONS, dict)
    assert len(PRIMARY_TAG_DESCRIPTIONS) == len(PRIMARY_TAGS)
    assert all(tag in PRIMARY_TAG_DESCRIPTIONS for tag in PRIMARY_TAGS)
    assert PRIMARY_TAG_DESCRIPTIONS["fundamental"]  # Non-empty description

    # Secondary tag descriptions
    assert isinstance(SECONDARY_TAG_DESCRIPTIONS, dict)
    assert len(SECONDARY_TAG_DESCRIPTIONS) == len(SECONDARY_TAGS)
    assert all(tag in SECONDARY_TAG_DESCRIPTIONS for tag in SECONDARY_TAGS)
    assert SECONDARY_TAG_DESCRIPTIONS["measured"]  # Non-empty description


def test_primary_tags_unique():
    """Test that primary tags have no duplicates."""
    assert len(PRIMARY_TAGS) == len(set(PRIMARY_TAGS))


def test_secondary_tags_unique():
    """Test that secondary tags have no duplicates."""
    assert len(SECONDARY_TAGS) == len(set(SECONDARY_TAGS))


def test_no_tag_overlap_between_primary_and_secondary():
    """Test that primary and secondary tags don't overlap."""
    primary_set = set(PRIMARY_TAGS)
    secondary_set = set(SECONDARY_TAGS)
    overlap = primary_set & secondary_set
    assert len(overlap) == 0, f"Tags appear in both primary and secondary: {overlap}"


# ============================================================================
# Tag Validation Tests
# ============================================================================


def test_valid_primary_tag_only():
    """Test that entries can be created with just a primary tag."""
    entry = StandardNameScalarEntry(
        name="test_quantity",
        description="Test quantity",
        documentation="Test quantity for tag validation.",
        unit="m",
        tags=["fundamental"],
    )
    assert entry.tags == ["fundamental"]


def test_valid_primary_and_secondary_tags():
    """Test that entries can be created with primary and secondary tags."""
    entry = StandardNameScalarEntry(
        name="test_quantity",
        description="Test quantity",
        documentation="Test quantity with multiple tags.",
        unit="m",
        tags=["fundamental", "measured", "time-dependent"],
    )
    assert entry.tags == ["fundamental", "measured", "time-dependent"]


def test_valid_multiple_secondary_tags():
    """Test that multiple secondary tags are allowed."""
    entry = StandardNameScalarEntry(
        name="test_quantity",
        description="Test quantity",
        documentation="Test quantity with many secondary tags.",
        unit="m",
        tags=["equilibrium", "steady-state", "reconstructed", "validated"],
    )
    assert len(entry.tags) == 4
    assert entry.tags[0] == "equilibrium"  # Primary
    assert all(tag in SECONDARY_TAGS for tag in entry.tags[1:])


def test_invalid_primary_tag_rejected():
    """Test that invalid primary tags are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        StandardNameScalarEntry(
            name="test_quantity",
            description="Test quantity",
            tags=["invalid_primary_tag", "measured"],
        )

    error = exc_info.value
    assert "Unknown tag(s): invalid_primary_tag" in str(error)
    assert "Valid tags are defined in grammar/vocabularies/tags.yml" in str(error)


def test_invalid_secondary_tag_rejected():
    """Test that invalid secondary tags are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        StandardNameScalarEntry(
            name="test_quantity",
            description="Test quantity",
            tags=["fundamental", "invalid_secondary_tag"],
        )

    error = exc_info.value
    assert "Unknown tag(s): invalid_secondary_tag" in str(error)
    assert "Valid tags are defined in grammar/vocabularies/tags.yml" in str(error)


def test_empty_tags_allowed():
    """Test that empty tag list is allowed."""
    entry = StandardNameScalarEntry(
        name="test_quantity",
        description="Test quantity",
        documentation="Test quantity with empty tags.",
        unit="m",
        tags=[],
    )
    assert entry.tags == []


def test_primary_tag_validation_position_specific():
    """Test that tags are auto-reordered to put primary tag first."""
    # Valid: primary tag in first position
    entry = StandardNameScalarEntry(
        name="test_quantity",
        description="Test quantity",
        documentation="Test quantity for tag order validation.",
        unit="m",
        tags=["fundamental", "measured"],
    )
    assert entry.tags[0] == "fundamental"

    # Auto-reordering: secondary tag in first position gets reordered
    entry2 = StandardNameScalarEntry(
        name="test_quantity",
        description="Test quantity",
        documentation="Test quantity for tag auto-reordering.",
        unit="m",
        tags=["measured", "fundamental"],  # Will be auto-reordered
    )

    # Verify that fundamental (primary) was moved to position 0
    assert entry2.tags[0] == "fundamental"
    assert "measured" in entry2.tags[1:]


def test_tag_whitespace_normalization():
    """Test that tags are normalized (whitespace stripped)."""
    entry = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "test_quantity",
            "description": "Test quantity",
            "documentation": "Test quantity for tag normalization.",
            "unit": "m",
            "tags": ["  fundamental  ", " measured ", ""],
        }
    )
    assert entry.tags == ["fundamental", "measured"]


def test_vector_entry_tag_validation():
    """Test that vector entries also validate tags correctly."""
    # Valid
    entry = StandardNameVectorEntry(
        name="test_vector",
        description="Test vector",
        documentation="Test vector for tag validation.",
        unit="m.s^-1",
        tags=["transport", "spatial-profile"],
    )
    assert entry.tags == ["transport", "spatial-profile"]

    # Invalid
    with pytest.raises(ValidationError):
        StandardNameVectorEntry(
            name="test_vector",
            description="Test vector",
            tags=["invalid_tag"],
        )


# ============================================================================
# Tag Vocabulary Structure Tests
# ============================================================================


def test_fundamental_tag_exists():
    """Test that 'fundamental' primary tag exists."""
    assert "fundamental" in PRIMARY_TAGS
    assert "fundamental" in PRIMARY_TAG_DESCRIPTIONS


def test_equilibrium_tag_exists():
    """Test that 'equilibrium' primary tag exists."""
    assert "equilibrium" in PRIMARY_TAGS
    assert "equilibrium" in PRIMARY_TAG_DESCRIPTIONS


def test_diagnostic_primary_tags_exist():
    """Test that diagnostic primary tags exist."""
    diagnostic_tags = [
        "magnetics",
        "thomson-scattering",
        "interferometry",
        "spectroscopy",
    ]
    for tag in diagnostic_tags:
        assert tag in PRIMARY_TAGS, f"Expected diagnostic tag '{tag}' not found"


def test_physics_primary_tags_exist():
    """Test that physics domain primary tags exist."""
    physics_tags = [
        "core-physics",
        "transport",
        "edge-physics",
        "mhd",
    ]
    for tag in physics_tags:
        assert tag in PRIMARY_TAGS, f"Expected physics tag '{tag}' not found"


def test_temporal_secondary_tags_exist():
    """Test that temporal secondary tags exist."""
    temporal_tags = [
        "time-dependent",
        "steady-state",
        "transient",
    ]
    for tag in temporal_tags:
        assert tag in SECONDARY_TAGS, f"Expected temporal tag '{tag}' not found"


def test_spatial_secondary_tags_exist():
    """Test that spatial secondary tags exist."""
    spatial_tags = [
        "spatial-profile",
        "flux-surface-average",
        "volume-average",
        "local-measurement",
        "global-quantity",
    ]
    for tag in spatial_tags:
        assert tag in SECONDARY_TAGS, f"Expected spatial tag '{tag}' not found"


def test_provenance_secondary_tags_exist():
    """Test that provenance secondary tags exist."""
    provenance_tags = [
        "measured",
        "reconstructed",
        "simulated",
        "derived",
        "validated",
    ]
    for tag in provenance_tags:
        assert tag in SECONDARY_TAGS, f"Expected provenance tag '{tag}' not found"


def test_quality_secondary_tags_exist():
    """Test that data quality secondary tags exist."""
    quality_tags = [
        "calibrated",
        "raw-data",
        "real-time",
        "post-shot-analysis",
    ]
    for tag in quality_tags:
        assert tag in SECONDARY_TAGS, f"Expected quality tag '{tag}' not found"


# ============================================================================
# Integration Tests
# ============================================================================


def test_common_tag_combinations():
    """Test common real-world tag combinations."""
    test_cases = [
        # Diagnostic measurement
        (["thomson-scattering", "measured", "spatial-profile", "calibrated"], True),
        # Equilibrium reconstruction
        (["equilibrium", "reconstructed", "steady-state"], True),
        # Derived transport quantity
        (["transport", "derived", "spatial-profile"], True),
        # Fundamental quantity
        (["fundamental", "global-quantity", "measured"], True),
        # Time-dependent measurement
        (["magnetics", "measured", "time-dependent", "raw-data"], True),
        # Invalid: wrong primary tag
        (["invalid", "measured"], False),
        # Invalid: wrong secondary tag
        (["fundamental", "invalid"], False),
    ]

    for tags, should_succeed in test_cases:
        if should_succeed:
            entry = StandardNameScalarEntry(
                name="test_quantity",
                description="Test quantity",
                documentation="Test quantity for tag combination validation.",
                unit="m",
                tags=tags,
            )
            assert entry.tags == tags
        else:
            with pytest.raises(ValidationError):
                StandardNameScalarEntry(
                    name="test_quantity",
                    description="Test quantity",
                    documentation="Test quantity for invalid tag validation.",
                    unit="m",
                    tags=tags,
                )


def test_tag_consistency_with_yaml_source():
    """Test that generated types match YAML source."""
    spec = TagSpec.load()

    # Check that all primary tags from YAML are in generated constants
    for tag in spec.primary_tags:
        assert tag in PRIMARY_TAGS, (
            f"Primary tag '{tag}' from YAML not in generated types"
        )

    # Check that all secondary tags from YAML are in generated constants
    for tag in spec.secondary_tags:
        assert tag in SECONDARY_TAGS, (
            f"Secondary tag '{tag}' from YAML not in generated types"
        )

    # Check lengths match
    assert len(PRIMARY_TAGS) == len(spec.primary_tags)
    assert len(SECONDARY_TAGS) == len(spec.secondary_tags)


def test_tag_descriptions_are_nonempty():
    """Test that all tags have non-empty descriptions."""
    for tag in PRIMARY_TAGS:
        desc = PRIMARY_TAG_DESCRIPTIONS[tag]
        assert desc and desc.strip(), f"Primary tag '{tag}' has empty description"

    for tag in SECONDARY_TAGS:
        desc = SECONDARY_TAG_DESCRIPTIONS[tag]
        assert desc and desc.strip(), f"Secondary tag '{tag}' has empty description"
