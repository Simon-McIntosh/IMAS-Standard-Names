"""Tests for D5 senior-review vocabulary additions and grammar changes."""

import pytest

from imas_standard_names.grammar.model import (
    StandardName,
    compose_standard_name,
    parse_standard_name,
)
from imas_standard_names.grammar.model_types import (
    Object,
    Position,
    Process,
    Subject,
    Transformation,
)
from imas_standard_names.grammar.support import (
    normalize_standard_name,
    validate_forbidden_patterns,
)

# ---------------------------------------------------------------------------
# Vocabulary token existence tests
# ---------------------------------------------------------------------------


class TestD5SubjectTokens:
    """Verify D5 subject vocabulary additions."""

    def test_pfirsch_schlueter_in_subject_enum(self):
        assert Subject("pfirsch_schlueter") == Subject.PFIRSCH_SCHLUETER

    def test_pfirsch_schlueter_current_parse(self):
        parsed = parse_standard_name("pfirsch_schlueter_current")
        assert parsed.subject == Subject.PFIRSCH_SCHLUETER
        assert parsed.physical_base == "current"

    def test_pfirsch_schlueter_current_round_trip(self):
        name = "pfirsch_schlueter_current"
        parsed = parse_standard_name(name)
        assert compose_standard_name(parsed) == name


class TestD5ProcessTokens:
    """Verify D5 process vocabulary additions."""

    def test_viscous_heat_flux_in_process_enum(self):
        assert Process("viscous_heat_flux") == Process.VISCOUS_HEAT_FLUX

    def test_inertial_in_process_enum(self):
        assert Process("inertial") == Process.INERTIAL

    def test_power_due_to_viscous_heat_flux_round_trip(self):
        name = "power_due_to_viscous_heat_flux"
        parsed = parse_standard_name(name)
        assert parsed.process == Process.VISCOUS_HEAT_FLUX
        assert parsed.physical_base == "power"
        assert compose_standard_name(parsed) == name

    def test_energy_due_to_inertial_round_trip(self):
        name = "energy_due_to_inertial"
        parsed = parse_standard_name(name)
        assert parsed.process == Process.INERTIAL
        assert parsed.physical_base == "energy"
        assert compose_standard_name(parsed) == name


class TestD5ObjectTokens:
    """Verify D5 object vocabulary additions."""

    @pytest.mark.parametrize(
        "token,enum_member",
        [
            ("magnetic_field_probe", Object.MAGNETIC_FIELD_PROBE),
            ("mse", Object.MSE),
            ("iron_core_segment", Object.IRON_CORE_SEGMENT),
            ("pickup_coil", Object.PICKUP_COIL),
            ("plasma_filament", Object.PLASMA_FILAMENT),
        ],
    )
    def test_object_enum_membership(self, token, enum_member):
        assert Object(token) == enum_member

    def test_voltage_of_pickup_coil_round_trip(self):
        name = "voltage_of_pickup_coil"
        parsed = parse_standard_name(name)
        assert parsed.object == Object.PICKUP_COIL
        assert parsed.physical_base == "voltage"
        assert compose_standard_name(parsed) == name

    def test_area_of_iron_core_segment_round_trip(self):
        name = "area_of_iron_core_segment"
        parsed = parse_standard_name(name)
        assert parsed.object == Object.IRON_CORE_SEGMENT
        assert parsed.physical_base == "area"
        assert compose_standard_name(parsed) == name

    def test_mse_voltage_as_device(self):
        name = "mse_voltage"
        parsed = parse_standard_name(name)
        assert parsed.device == Object.MSE
        assert parsed.physical_base == "voltage"
        assert compose_standard_name(parsed) == name


class TestD5PositionTokens:
    """Verify D5 position vocabulary additions."""

    @pytest.mark.parametrize(
        "token,enum_member",
        [
            ("tearing_mode_center", Position.TEARING_MODE_CENTER),
            ("normalized_poloidal_flux", Position.NORMALIZED_POLOIDAL_FLUX),
        ],
    )
    def test_position_enum_membership(self, token, enum_member):
        assert Position(token) == enum_member

    def test_temperature_at_tearing_mode_center(self):
        name = "electron_temperature_at_tearing_mode_center"
        parsed = parse_standard_name(name)
        assert parsed.position == Position.TEARING_MODE_CENTER
        assert parsed.subject == Subject.ELECTRON
        assert parsed.physical_base == "temperature"
        assert compose_standard_name(parsed) == name


class TestD5TransformationTokens:
    """Verify D5 transformation vocabulary additions."""

    @pytest.mark.parametrize(
        "token,enum_member",
        [
            ("per_toroidal_mode", Transformation.PER_TOROIDAL_MODE),
            ("cumulative", Transformation.CUMULATIVE),
            ("amplitude_of", Transformation.AMPLITUDE_OF),
        ],
    )
    def test_transformation_enum_membership(self, token, enum_member):
        assert Transformation(token) == enum_member

    def test_per_toroidal_mode_power_round_trip(self):
        name = "per_toroidal_mode_power"
        parsed = parse_standard_name(name)
        assert parsed.transformation == Transformation.PER_TOROIDAL_MODE
        assert parsed.physical_base == "power"
        assert compose_standard_name(parsed) == name

    def test_cumulative_energy_round_trip(self):
        name = "cumulative_energy"
        parsed = parse_standard_name(name)
        assert parsed.transformation == Transformation.CUMULATIVE
        assert parsed.physical_base == "energy"
        assert compose_standard_name(parsed) == name

    def test_amplitude_of_magnetic_field_round_trip(self):
        name = "amplitude_of_magnetic_field"
        parsed = parse_standard_name(name)
        assert parsed.transformation == Transformation.AMPLITUDE_OF
        assert parsed.physical_base == "magnetic_field"
        assert compose_standard_name(parsed) == name


# ---------------------------------------------------------------------------
# Synonym rewrite tests
# ---------------------------------------------------------------------------


class TestSynonymRewrites:
    """Verify synonym rewrite map normalizes names."""

    def test_per_toroidal_mode_number_rewrite(self):
        result = normalize_standard_name("power_per_toroidal_mode_number")
        assert result == "power_per_toroidal_mode"

    def test_field_probe_rewrite(self):
        result = normalize_standard_name("voltage_of_poloidal_field_probe")
        assert result == "voltage_of_poloidal_magnetic_field_probe"

    def test_no_rewrite_for_canonical_name(self):
        canonical = "electron_temperature"
        assert normalize_standard_name(canonical) == canonical

    def test_over_not_rewritten_globally(self):
        """over_ is not globally rewritten to avoid breaking decomposition tokens."""
        name = "m_over_n_equals_2_over_1_magnetic_field"
        assert normalize_standard_name(name) == name

    def test_parse_applies_synonym_rewrite(self):
        """Parser should normalize before parsing."""
        parsed = parse_standard_name("electron_per_toroidal_mode_power")
        # After rewrite: electron_per_toroidal_mode_power
        # per_toroidal_mode is a transformation token
        assert parsed.transformation == Transformation.PER_TOROIDAL_MODE


# ---------------------------------------------------------------------------
# Forbidden suffix tests
# ---------------------------------------------------------------------------


class TestForbiddenPatterns:
    """Verify forbidden suffix patterns raise clear errors."""

    def test_per_toroidal_mode_number_forbidden(self):
        with pytest.raises(ValueError, match="per_toroidal_mode"):
            validate_forbidden_patterns("power_per_toroidal_mode_number")

    def test_canonical_name_passes(self):
        # Should not raise
        validate_forbidden_patterns("electron_temperature")

    def test_per_toroidal_mode_passes(self):
        # Canonical form should not raise
        validate_forbidden_patterns("power_per_toroidal_mode")

    def test_valid_over_in_transformations(self):
        # over_ in transformation tokens should not be forbidden
        validate_forbidden_patterns("maximum_over_flux_surface_temperature")

    def test_valid_over_in_decomposition(self):
        # over_ in decomposition tokens should not be forbidden
        validate_forbidden_patterns("m_over_n_equals_2_over_1_magnetic_field")


# ---------------------------------------------------------------------------
# Existing round-trip integrity (regression)
# ---------------------------------------------------------------------------


class TestExistingRoundTrips:
    """Verify existing names still parse and compose correctly."""

    @pytest.mark.parametrize(
        "name",
        [
            "electron_temperature",
            "radial_component_of_magnetic_field",
            "flux_loop_voltage",
            "area_of_flux_loop",
            "electron_temperature_at_magnetic_axis",
            "major_radius_of_plasma_boundary",
            "power_due_to_ohmic",
            "flux_surface_averaged_density",
            "real_part_of_magnetic_field",
            "cumulative_inside_flux_surface_power",
        ],
    )
    def test_round_trip(self, name):
        parsed = parse_standard_name(name)
        composed = compose_standard_name(parsed)
        assert composed == name
