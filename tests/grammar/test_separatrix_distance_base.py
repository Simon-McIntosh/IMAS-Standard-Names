"""The ``separatrix_distance`` physical base.

A measurement position's distance from the magnetic separatrix, positive
outside it. The base says what a distance is measured from; the ``separatrix``
zone says where a quantity sits; the ``separatrix`` locus names a reference
position. Adding the base must leave the zone and locus readings untouched.
"""

from __future__ import annotations

from imas_standard_names.grammar import compose_standard_name, parse_standard_name

RADIAL_SEPARATRIX_DISTANCE = "radial_separatrix_distance_at_outboard_midplane"


def test_radial_separatrix_distance_decomposes_to_component_base_and_position() -> None:
    model = parse_standard_name(RADIAL_SEPARATRIX_DISTANCE)
    assert model.component == "radial"
    assert model.physical_base == "separatrix_distance"
    assert model.position is not None
    assert model.position.value == "outboard_midplane"


def test_radial_separatrix_distance_round_trips() -> None:
    model = parse_standard_name(RADIAL_SEPARATRIX_DISTANCE)
    assert compose_standard_name(model) == RADIAL_SEPARATRIX_DISTANCE
    assert model.physical_base == "separatrix_distance"


def test_separatrix_zone_name_keeps_its_parse() -> None:
    model = parse_standard_name("separatrix_density")
    assert model.physical_base == "density"
    assert tuple(zone.value for zone in model.zone) == ("separatrix",)
    assert compose_standard_name(model) == "separatrix_density"


def test_separatrix_locus_name_keeps_its_parse() -> None:
    model = parse_standard_name("temperature_at_separatrix")
    assert model.physical_base == "temperature"
    assert model.position is not None
    assert model.position.value == "separatrix"
    assert compose_standard_name(model) == "temperature_at_separatrix"