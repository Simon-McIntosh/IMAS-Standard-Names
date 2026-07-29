"""Closed-vocabulary validation for binary operands."""

import pytest

from imas_standard_names.grammar import (
    NonCanonicalNameError,
    UnknownBaseTokenError,
    parse_standard_name,
)
from imas_standard_names.grammar.parser import parse


def test_literal_operand_fallback_is_diagnostic() -> None:
    result = parse("ratio_of_wibble_frobnicator_to_square_major_radius")

    assert any(
        diagnostic.category == "vocab_gap"
        and "wibble_frobnicator" in diagnostic.message
        for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize(
    "name",
    [
        "ratio_of_electron_to_ion_temperature",
        "ratio_of_electron_pressure_to_magnetic_pressure",
        (
            "flux_surface_averaged_ratio_of"
            "_square_toroidal_flux_radius_gradient_magnitude"
            "_to_square_major_radius"
        ),
        (
            "flux_surface_averaged_ratio_of"
            "_square_toroidal_flux_radius_gradient_magnitude"
            "_to_square_magnetic_field_magnitude"
        ),
    ],
)
def test_registered_or_elided_operands_are_valid(name: str) -> None:
    parse_standard_name(name)


@pytest.mark.parametrize(
    "name,operand",
    [
        (
            "ratio_of_wibble_frobnicator_to_square_major_radius",
            "wibble_frobnicator",
        ),
        ("ratio_of_substrate_to_electron_density", "substrate"),
    ],
)
def test_unregistered_binary_operand_is_rejected(name: str, operand: str) -> None:
    with pytest.raises(UnknownBaseTokenError) as excinfo:
        parse_standard_name(name)

    assert excinfo.value.token == operand


def test_un_normalized_poloidal_flux_coordinate_is_indexable() -> None:
    name = (
        "derivative_with_respect_to_poloidal_magnetic_flux_coordinate"
        "_of_poloidal_current_function"
    )

    assert parse_standard_name(name).transformation == (
        "derivative_with_respect_to_poloidal_magnetic_flux_coordinate"
    )


def test_toroidal_flux_coordinate_is_canonical() -> None:
    coordinate = parse_standard_name(
        "derivative_with_respect_to_toroidal_flux_coordinate_of_pressure"
    )
    assert coordinate.transformation == (
        "derivative_with_respect_to_toroidal_flux_coordinate"
    )

    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name(
            "derivative_with_respect_to_toroidal_flux_radius_of_pressure"
        )

    assert excinfo.value.canonical_form == (
        "derivative_with_respect_to_toroidal_flux_coordinate_of_pressure"
    )
