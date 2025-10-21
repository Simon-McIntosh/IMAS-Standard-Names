from imas_standard_names.grammar import (
    Component,
    Position,
    Process,
    StandardName,
    compose_name,
    parse_name,
)


def test_compose_and_parse_minimal_base():
    parts = StandardName(physical_base="temperature")
    name = compose_name(parts)
    assert name == "temperature"
    round_trip = parse_name(name)
    assert round_trip.model_dump_compact() == {"physical_base": "temperature"}


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
