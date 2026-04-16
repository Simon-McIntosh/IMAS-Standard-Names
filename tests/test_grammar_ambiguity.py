"""Tests for grammar ambiguity resolution.

Covers the 9 known ambiguous tokens identified in the unified vocabulary plan.
Categories:
- Parser fixes: tokens where the prefix parser needed correction
- Verified correct: tokens that already parse correctly
- Documentation-only: design gaps documented, not parser bugs
"""

import pytest

from imas_standard_names.grammar.model import (
    StandardName,
    compose_standard_name,
    parse_standard_name,
)
from imas_standard_names.grammar.support import (
    _PREFIX_EXCLUSIVE_PAIRS,
    _is_prefix_exclusive_with,
    parse_standard_name as parse_parts,
)


class TestPrefixExclusivityHelper:
    """Unit tests for the prefix-only exclusivity helper."""

    def test_prefix_exclusive_pairs_contains_component_coordinate(self):
        assert ("component", "coordinate") in _PREFIX_EXCLUSIVE_PAIRS

    def test_prefix_exclusive_pairs_excludes_cross_boundary(self):
        """Pairs with one side outside PREFIX_SEGMENTS are excluded."""
        assert ("device", "object") not in _PREFIX_EXCLUSIVE_PAIRS
        assert ("geometric_base", "physical_base") not in _PREFIX_EXCLUSIVE_PAIRS
        assert ("geometry", "position") not in _PREFIX_EXCLUSIVE_PAIRS

    def test_is_prefix_exclusive_with_component_blocks_coordinate(self):
        assert _is_prefix_exclusive_with("coordinate", {"component"}) is True

    def test_is_prefix_exclusive_with_coordinate_blocks_component(self):
        assert _is_prefix_exclusive_with("component", {"coordinate"}) is True

    def test_is_prefix_exclusive_with_unrelated_segment(self):
        assert _is_prefix_exclusive_with("subject", {"component"}) is False

    def test_is_prefix_exclusive_with_empty_set(self):
        assert _is_prefix_exclusive_with("coordinate", set()) is False


class TestDiamagneticAmbiguity:
    """diamagnetic: Component ∩ physical_base prefix."""

    def test_radial_component_of_diamagnetic_velocity(self):
        """When component is already matched, diamagnetic stays in physical_base."""
        parsed = parse_standard_name("radial_component_of_diamagnetic_velocity")
        assert parsed.component.value == "radial"
        assert parsed.physical_base == "diamagnetic_velocity"
        assert parsed.coordinate is None

    def test_diamagnetic_component_of_magnetic_field(self):
        """diamagnetic as explicit component via template."""
        parsed = parse_standard_name("diamagnetic_component_of_magnetic_field")
        assert parsed.component.value == "diamagnetic"
        assert parsed.physical_base == "magnetic_field"

    def test_round_trip_with_component_prefix(self):
        """Compose -> parse round-trip for diamagnetic in physical_base."""
        parts = {"component": "radial", "physical_base": "diamagnetic_velocity"}
        name = compose_standard_name(parts)
        assert name == "radial_component_of_diamagnetic_velocity"
        parsed = parse_standard_name(name)
        assert parsed.component.value == "radial"
        assert parsed.physical_base == "diamagnetic_velocity"

    def test_bare_diamagnetic_velocity(self):
        """Bare diamagnetic_velocity: diamagnetic consumed as coordinate prefix.

        This is a known limitation. Without additional context, the parser
        sees diamagnetic in the Component vocabulary (shared with coordinate)
        and matches it as coordinate (bare prefix, no template). The ambiguity
        only matters when there's already a component prefix.
        """
        parsed = parse_parts("diamagnetic_velocity")
        assert parsed.get("coordinate") == "diamagnetic"
        assert parsed.get("physical_base") == "velocity"


class TestIonAmbiguity:
    """ion: Subject ∩ physical_base prefix — already works correctly."""

    def test_ion_temperature(self):
        parsed = parse_standard_name("ion_temperature")
        assert parsed.subject.value == "ion"
        assert parsed.physical_base == "temperature"

    def test_ion_cyclotron_frequency(self):
        """ion consumed as subject, cyclotron_frequency as physical_base."""
        parsed = parse_standard_name("ion_cyclotron_frequency")
        assert parsed.subject.value == "ion"
        assert parsed.physical_base == "cyclotron_frequency"


class TestNeutralAmbiguity:
    """neutral: Subject ∩ physical_base prefix — already works correctly."""

    def test_neutral_density(self):
        parsed = parse_standard_name("neutral_density")
        assert parsed.subject.value == "neutral"
        assert parsed.physical_base == "density"

    def test_neutral_pressure(self):
        parsed = parse_standard_name("neutral_pressure")
        assert parsed.subject.value == "neutral"
        assert parsed.physical_base == "pressure"


class TestVerticalAmbiguity:
    """vertical: Component ∩ position qualifier — template disambiguates."""

    def test_vertical_component_of_magnetic_field(self):
        parsed = parse_standard_name("vertical_component_of_magnetic_field")
        assert parsed.component.value == "vertical"
        assert parsed.physical_base == "magnetic_field"

    def test_vertical_position_of_magnetic_axis(self):
        parsed = parse_standard_name("vertical_position_of_magnetic_axis")
        assert parsed.coordinate.value == "vertical"
        assert parsed.geometric_base.value == "position"
        assert parsed.geometry.value == "magnetic_axis"

    def test_vertical_component_round_trip(self):
        parts = {"component": "vertical", "physical_base": "magnetic_field"}
        name = compose_standard_name(parts)
        parsed = parse_standard_name(name)
        assert parsed.component.value == "vertical"
        assert parsed.physical_base == "magnetic_field"


class TestNonGrammarAmbiguities:
    """Document-only ambiguities — not parser bugs."""

    def test_measured_vs_reconstructed_is_provenance(self):
        """Provenance (measured vs reconstructed) is metadata, not grammar.

        Standard names describe the quantity, not how it was obtained.
        """
        parsed = parse_standard_name("electron_temperature")
        assert parsed.physical_base == "temperature"
        assert parsed.subject.value == "electron"

    def test_outline_is_geometric_base(self):
        """outline is a geometric_base; the target goes in the object segment."""
        parsed = parse_standard_name("outline_of_plasma_boundary")
        assert parsed.geometric_base.value == "outline"
        assert parsed.geometry.value == "plasma_boundary"
