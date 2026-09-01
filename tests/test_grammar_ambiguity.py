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

_XFAIL_VOCAB_GAP = pytest.mark.xfail(
    reason="vocabulary gap: compound base not registered (drift_velocity, cyclotron_frequency)",
    strict=True,
)


class TestDiamagneticAmbiguity:
    """diamagnetic: physical_base prefix only.

    As of v0.7.0rc8, `diamagnetic` is removed from the Component vocabulary.
    The diamagnetic drift is a physics concept (v_dia = B × ∇p / (qnB²)),
    not a spatial projection axis. Any use of `diamagnetic` must appear in
    the physical_base (e.g. `diamagnetic_drift_velocity`,
    `diamagnetic_flux`), never as a `<axis>_component_of_<base>` component.

    Note: The D.3 senior review (2026-04) ruled that `diamagnetic` should be
    restored to Component. This is deferred because the `coordinate` segment
    shares the Component vocabulary (bare prefix match), causing
    `diamagnetic_` to match as a coordinate on names like
    `electron_diamagnetic_drift_velocity`. A parser refactoring to separate
    component/coordinate vocabularies is required first.
    """

    def test_radial_component_of_diamagnetic_velocity(self):
        """diamagnetic is a channel-qualifier (channel_qualifiers.yml); with a
        real projection axis it peels into the channel_qualifier segment and the
        base is velocity. The name round-trips unchanged."""
        parsed = parse_standard_name("radial_diamagnetic_velocity")
        assert parsed.component.value == "radial"
        assert parsed.channel_qualifier is not None
        assert parsed.channel_qualifier.value == "diamagnetic"
        assert parsed.physical_base == "velocity"
        assert parsed.coordinate is None
        assert compose_standard_name(parsed) == "radial_diamagnetic_velocity"

    @_XFAIL_VOCAB_GAP
    def test_diamagnetic_is_not_a_component(self):
        """`diamagnetic_component_of_<X>` must not parse as a component form.

        With `diamagnetic` removed from Component, the parser no longer
        recognises it as a valid projection axis. The string falls through
        to physical_base as a whole (which higher-level validation then
        rejects as malformed).
        """
        parsed = parse_standard_name("diamagnetic_component_of_magnetic_field")
        assert parsed.component is None

    def test_round_trip_with_component_prefix(self):
        """Compose -> parse round-trip for radial_diamagnetic_velocity. The
        compose form authored with diamagnetic in physical_base and the form
        authored with the channel_qualifier segment both render to the same
        name; parsing yields the channel_qualifier segment."""
        parts = {"component": "radial", "physical_base": "diamagnetic_velocity"}
        name = compose_standard_name(parts)
        assert name == "radial_diamagnetic_velocity"
        parsed = parse_standard_name(name)
        assert parsed.component.value == "radial"
        assert parsed.channel_qualifier is not None
        assert parsed.channel_qualifier.value == "diamagnetic"
        assert parsed.physical_base == "velocity"

    @_XFAIL_VOCAB_GAP
    def test_bare_diamagnetic_drift_velocity(self):
        """Bare `diamagnetic_drift_velocity` — pure physical_base, no ambiguity."""
        parsed = parse_standard_name("diamagnetic_drift_velocity")
        assert parsed.component is None
        assert parsed.coordinate is None
        assert parsed.physical_base == "diamagnetic_drift_velocity"

    @_XFAIL_VOCAB_GAP
    def test_electron_diamagnetic_drift_velocity(self):
        """Subject + diamagnetic drift velocity — the common form in transport physics."""
        parsed = parse_standard_name("electron_diamagnetic_drift_velocity")
        assert parsed.subject.value == "electron"
        assert parsed.physical_base == "diamagnetic_drift_velocity"
        assert parsed.component is None

    @_XFAIL_VOCAB_GAP
    def test_ion_diamagnetic_drift_velocity(self):
        """Subject + diamagnetic drift velocity for ion species."""
        parsed = parse_standard_name("ion_diamagnetic_drift_velocity")
        assert parsed.subject.value == "ion"
        assert parsed.physical_base == "diamagnetic_drift_velocity"
        assert parsed.component is None


class TestIonAmbiguity:
    """ion: Subject ∩ physical_base prefix — already works correctly."""

    def test_ion_temperature(self):
        parsed = parse_standard_name("ion_temperature")
        assert parsed.subject.value == "ion"
        assert parsed.physical_base == "temperature"

    @_XFAIL_VOCAB_GAP
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
        parsed = parse_standard_name("vertical_magnetic_field")
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
        """outline is a geometric_base; the target goes in the geometry segment."""
        parsed = parse_standard_name("outline_of_plasma_boundary")
        assert parsed.geometric_base.value == "outline"
        assert parsed.geometry.value == "plasma_boundary"
