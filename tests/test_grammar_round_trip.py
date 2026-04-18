from imas_standard_names.grammar import (
    Component,
    Position,
    Process,
    StandardName,
    compose_name,
    parse_name,
)


def test_compose_and_parse_minimal_base():
    parts = StandardName(physical_base="magnetic_field")
    name = compose_name(parts)
    assert name == "magnetic_field"
    round_trip = parse_name(name)
    assert round_trip.model_dump_compact() == {"physical_base": "magnetic_field"}


def test_with_component_subject_no_basis():
    parts = {"component": "radial", "subject": "electron", "physical_base": "heat_flux"}
    name = compose_name(parts)
    assert name == "radial_component_of_electron_heat_flux"
    parsed = parse_name(name)
    assert parsed.component == Component.RADIAL
    assert parsed.subject == "electron"
    assert parsed.physical_base == "heat_flux"


def test_with_position_process():
    parts = {
        "physical_base": "magnetic_field",
        "position": "plasma_boundary",
        "process": "external_coil",
    }
    name = compose_name(parts)
    assert name == "magnetic_field_at_plasma_boundary_due_to_external_coil"
    back = parse_name(name)
    assert back.physical_base == "magnetic_field"
    assert back.position == Position.PLASMA_BOUNDARY
    assert back.process == Process.EXTERNAL_COIL


def test_invalid_order_raises():
    bad = "electron_radial_heat_flux"  # wrong order; component must be first
    try:
        parse_name(bad)
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- D.3 senior review (2026-04) vocabulary additions ---


class TestD3ComponentAdditions:
    """Round-trip tests for D.3 component tokens."""

    def test_normalized_radial_component(self):
        parts = {
            "component": "normalized_radial",
            "physical_base": "magnetic_field",
        }
        name = compose_name(parts)
        assert name == "normalized_radial_component_of_magnetic_field"
        parsed = parse_name(name)
        assert parsed.component == Component.NORMALIZED_RADIAL
        assert parsed.physical_base == "magnetic_field"

    def test_normalized_vertical_component(self):
        parts = {
            "component": "normalized_vertical",
            "physical_base": "magnetic_field",
        }
        name = compose_name(parts)
        assert name == "normalized_vertical_component_of_magnetic_field"
        parsed = parse_name(name)
        assert parsed.component == Component.NORMALIZED_VERTICAL
        assert parsed.physical_base == "magnetic_field"


class TestD3ProcessAdditions:
    """Round-trip tests for D.3 process tokens."""

    def test_ohmic_dissipation(self):
        parts = {
            "subject": "electron",
            "physical_base": "power_density",
            "process": "ohmic_dissipation",
        }
        name = compose_name(parts)
        assert name == "electron_power_density_due_to_ohmic_dissipation"
        parsed = parse_name(name)
        assert parsed.physical_base == "power_density"
        assert parsed.process == Process.OHMIC_DISSIPATION

    def test_resistive_diffusion(self):
        parts = {
            "physical_base": "magnetic_flux",
            "process": "resistive_diffusion",
        }
        name = compose_name(parts)
        assert name == "magnetic_flux_due_to_resistive_diffusion"
        parsed = parse_name(name)
        assert parsed.process == Process.RESISTIVE_DIFFUSION

    def test_neoclassical_tearing_mode(self):
        parts = {
            "physical_base": "magnetic_island_width",
            "process": "neoclassical_tearing_mode",
        }
        name = compose_name(parts)
        assert name == "magnetic_island_width_due_to_neoclassical_tearing_mode"
        parsed = parse_name(name)
        assert parsed.process == Process.NEOCLASSICAL_TEARING_MODE


class TestD3PositionAndGeometryAdditions:
    """Round-trip tests for D.3 position and geometry tokens."""

    def test_position_at_x_point(self):
        parts = {"physical_base": "temperature", "position": "x_point"}
        name = compose_name(parts)
        assert name == "temperature_at_x_point"
        parsed = parse_name(name)
        assert parsed.physical_base == "temperature"
        assert parsed.position == Position.X_POINT

    def test_geometry_of_strike_point(self):
        parts = {"geometric_base": "position", "geometry": "strike_point"}
        name = compose_name(parts)
        assert name == "position_of_strike_point"
        parsed = parse_name(name)
        assert parsed.geometric_base.value == "position"
        assert parsed.geometry.value == "strike_point"

    def test_position_at_sawtooth_inversion_radius(self):
        parts = {
            "physical_base": "electron_temperature",
            "position": "sawtooth_inversion_radius",
        }
        name = compose_name(parts)
        assert name == "electron_temperature_at_sawtooth_inversion_radius"
        parsed = parse_name(name)
        assert parsed.position == Position.SAWTOOTH_INVERSION_RADIUS


class TestD3TransformationAdditions:
    """Round-trip tests for D.3 transformation tokens."""

    def test_variation_of(self):
        from imas_standard_names.grammar import Transformation

        parts = {
            "transformation": "variation_of",
            "physical_base": "electron_temperature",
        }
        name = compose_name(parts)
        assert name == "variation_of_electron_temperature"
        parsed = parse_name(name)
        assert parsed.transformation == Transformation.VARIATION_OF
        assert parsed.physical_base == "electron_temperature"

    def test_cumulative_inside_flux_surface(self):
        from imas_standard_names.grammar import Transformation

        parts = {
            "transformation": "cumulative_inside_flux_surface",
            "physical_base": "current",
        }
        name = compose_name(parts)
        assert name == "cumulative_inside_flux_surface_current"
        parsed = parse_name(name)
        assert parsed.transformation == Transformation.CUMULATIVE_INSIDE_FLUX_SURFACE
        assert parsed.physical_base == "current"

    def test_per_toroidal_mode_number(self):
        from imas_standard_names.grammar import Transformation

        parts = {
            "transformation": "per_toroidal_mode_number",
            "physical_base": "magnetic_field",
        }
        name = compose_name(parts)
        assert name == "per_toroidal_mode_number_magnetic_field"
        parsed = parse_name(name)
        assert parsed.transformation == Transformation.PER_TOROIDAL_MODE_NUMBER


class TestD3ObjectAdditions:
    """Round-trip tests for D.3 object tokens."""

    def test_electron_cyclotron_beam(self):
        from imas_standard_names.grammar import Object

        parts = {
            "physical_base": "power",
            "object": "electron_cyclotron_beam",
        }
        name = compose_name(parts)
        assert name == "power_of_electron_cyclotron_beam"
        parsed = parse_name(name)
        assert parsed.object == Object.ELECTRON_CYCLOTRON_BEAM

    def test_fiber_optic_current_sensor(self):
        from imas_standard_names.grammar import Object

        parts = {
            "physical_base": "current",
            "object": "fiber_optic_current_sensor",
        }
        name = compose_name(parts)
        assert name == "current_of_fiber_optic_current_sensor"
        parsed = parse_name(name)
        assert parsed.object == Object.FIBER_OPTIC_CURRENT_SENSOR

    def test_passive_structure(self):
        from imas_standard_names.grammar import Object

        parts = {"physical_base": "current", "object": "passive_structure"}
        name = compose_name(parts)
        assert name == "current_of_passive_structure"
        parsed = parse_name(name)
        assert parsed.object == Object.PASSIVE_STRUCTURE
