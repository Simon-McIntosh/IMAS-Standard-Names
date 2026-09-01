"""The flux-surface metric coefficients must each be expressible and distinct.

An equilibrium code publishes a family of flux-surface-averaged metric
coefficients — ``<1/R^2>``, ``<1/B^2>``, ``<B^2>``, ``<1/R>``,
``<|grad rho|^2>``, ``<|grad rho|>`` — that are SEVEN distinct quantities
spanning FOUR dimensionalities. Each needs its own name carrying its own
unit; one shared name recording unit ``1`` for members of different
dimension is a semantic collapse.

Two of the family turn on |grad rho|. ``rho`` (the toroidal flux coordinate) is
a LENGTH, so its gradient is dimensionless — and although ``rho`` is
constant on a flux surface, its gradient is not, so the gradient base must
never carry ``constant_on_flux_surface``: flagging it would trip the
flux-surface reduction gate against exactly the ``flux_surface_averaged``
prefix these names need.

The gradient cannot be spelled with the ``gradient`` operator, because a
transformation may not apply to a geometry carrier and ``toroidal_flux_coordinate``
is one — ``gradient_of_toroidal_flux_coordinate`` raises. The vector base carries
it instead.
"""

from __future__ import annotations

import pytest

from imas_standard_names import compose, parse
from imas_standard_names.grammar.parser import ParseError
from imas_standard_names.grammar.vocab_loaders import load_physical_bases

# Each member of the family, with the DD unit it must carry. Distinct units are
# the point: a single name cannot serve two of these rows.
EXPRESSIBLE = [
    ("flux_surface_averaged_inverse_of_square_of_major_radius", "m^-2"),
    (
        "flux_surface_averaged_inverse_of_square_of_magnetic_field_magnitude",
        "T^-2",
    ),
    ("flux_surface_averaged_square_of_magnetic_field_magnitude", "T^2"),
    ("flux_surface_averaged_inverse_of_major_radius", "m^-1"),
    ("flux_surface_averaged_toroidal_flux_coordinate_gradient_magnitude", "1"),
    (
        "flux_surface_averaged_square_of_toroidal_flux_coordinate_gradient_magnitude",
        "1",
    ),
]


@pytest.mark.parametrize(("name", "unit"), EXPRESSIBLE)
def test_metric_coefficient_parses(name: str, unit: str) -> None:
    """Every member strictly validates and round-trips losslessly."""
    result = parse(name, strict=True)
    assert compose(result.ir) == name, unit


@pytest.mark.parametrize(
    "name",
    [
        "flux_surface_averaged_inverse_square_major_radius",
        "flux_surface_averaged_inverse_square_magnetic_field_magnitude",
        "flux_surface_averaged_square_magnetic_field_magnitude",
        "flux_surface_averaged_inverse_major_radius",
        ("flux_surface_averaged_square_toroidal_flux_coordinate_gradient_magnitude"),
    ],
)
def test_glued_metric_operator_spellings_are_not_canonical(name: str) -> None:
    with pytest.raises(ParseError, match="operator spelling"):
        parse(name, strict=True)


def test_metric_coefficient_names_are_distinct() -> None:
    """No two members of the family share a name."""
    names = [name for name, _ in EXPRESSIBLE]
    assert len(set(names)) == len(names)


def test_toroidal_flux_coordinate_gradient_is_a_registered_vector_base() -> None:
    """The |grad rho| carrier is a vector base, so ``magnitude`` applies."""
    base = load_physical_bases().bases["toroidal_flux_coordinate_gradient"]
    assert base.kind == "vector"


def test_toroidal_flux_coordinate_gradient_is_not_a_flux_function() -> None:
    """rho is constant on a flux surface; its gradient is not.

    Flagging the gradient would make the flux-surface reduction gate reject
    the averaged names, which are the only reason the base exists.
    """
    base = load_physical_bases().bases["toroidal_flux_coordinate_gradient"]
    assert not base.constant_on_flux_surface


def test_toroidal_flux_coordinate_gradient_is_dimensionless() -> None:
    """|grad rho| is a length gradient, so it carries no SI unit."""
    base = load_physical_bases().bases["toroidal_flux_coordinate_gradient"]
    assert not base.inherently_dimensional


def test_flux_surface_average_of_the_gradient_is_not_gated_as_a_no_op() -> None:
    """The reduction gate must let the gradient through.

    Contrast ``flux_surface_averaged_toroidal_flux_coordinate``, which the gate
    correctly refuses because the flux label itself is a flux function.
    """
    assert parse(
        "flux_surface_averaged_toroidal_flux_coordinate_gradient_magnitude",
        strict=True,
    )
    with pytest.raises(ParseError, match="constant on a flux surface"):
        parse("flux_surface_averaged_toroidal_flux_coordinate", strict=True)
