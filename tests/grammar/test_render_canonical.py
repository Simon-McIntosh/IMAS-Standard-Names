"""Canonical rendering test for grammar vNext (plan 38 §A10, item 6).

Builds IR instances manually and asserts :func:`imas_standard_names.grammar.render.compose`
produces the exact canonical string described in plan §A2.

Canonical form rules (§A2):
- Operator wrapping: ``unary_prefix`` → ``<op>_of_<inner>``;
  ``unary_postfix`` → ``<inner>_<op>``; ``binary`` → ``<op>_of_<A>_<sep>_<B>``
- Projection prefix (canonical): ``<axis>_component_of_`` before qualifiers+base
  (component shape) or ``<axis>_coordinate_of_`` before carrier (coordinate shape)
- Locus suffix: ``_of_<tok>`` / ``_at_<tok>`` / ``_over_<tok>``
- Mechanism suffix: ``_due_to_<process>``
- Order: operators(outer→inner) → projection → qualifiers → base → locus → mechanism

Each test is labelled with the §A12 row or §A2 rule it verifies.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.ir import (
    AxisProjection,
    BaseKind,
    LocusRef,
    LocusRelation,
    LocusType,
    OperatorApplication,
    OperatorKind,
    Process,
    ProjectionShape,
    Qualifier,
    QuantityOrCarrier,
    StandardNameIR,
)
from imas_standard_names.grammar.render import RenderError, compose

# ---------------------------------------------------------------------------
# §A2 rule 1: bare base (no operators, no decorators)
# ---------------------------------------------------------------------------


def test_render_bare_quantity_base() -> None:
    """§A2: bare quantity base → its token unchanged."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY)
    )
    assert compose(ir) == "pressure"


def test_render_bare_geometry_carrier() -> None:
    """§A2: bare geometry carrier → its token unchanged."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="normalized_minor_radius", kind=BaseKind.GEOMETRY)
    )
    assert compose(ir) == "normalized_minor_radius"


# ---------------------------------------------------------------------------
# §A2 rule 2: unary prefix operator
# ---------------------------------------------------------------------------


def test_render_unary_prefix_operator() -> None:
    """§A2: ``unary_prefix`` → ``<op>_of_<inner>``."""
    ir = StandardNameIR(
        operators=[OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op="maximum")],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "maximum_of_pressure"


def test_render_unary_prefix_derivative() -> None:
    """§A2: ``derivative_of_X`` rendering."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op="derivative")
        ],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "derivative_of_pressure"


def test_render_unary_prefix_flux_surface_averaged() -> None:
    """``flux_surface_averaged`` prefix operator."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(
                kind=OperatorKind.UNARY_PREFIX, op="flux_surface_averaged"
            )
        ],
        base=QuantityOrCarrier(token="temperature", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "flux_surface_averaged_of_temperature"


# ---------------------------------------------------------------------------
# §A2 rule 3: unary postfix operator
# ---------------------------------------------------------------------------


def test_render_unary_postfix_magnitude() -> None:
    """§A2: ``unary_postfix`` → ``<inner>_<op>``."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(kind=OperatorKind.UNARY_POSTFIX, op="magnitude")
        ],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "pressure_magnitude"


def test_render_unary_postfix_gyroaveraged() -> None:
    """``gyroaveraged`` postfix operator (§A12 row 15 fragment)."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(kind=OperatorKind.UNARY_POSTFIX, op="gyroaveraged")
        ],
        base=QuantityOrCarrier(token="temperature", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "temperature_gyroaveraged"


def test_render_unary_postfix_moment() -> None:
    """``moment`` postfix operator."""
    ir = StandardNameIR(
        operators=[OperatorApplication(kind=OperatorKind.UNARY_POSTFIX, op="moment")],
        base=QuantityOrCarrier(token="temperature", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "temperature_moment"


# ---------------------------------------------------------------------------
# §A2 rule 4: binary operators
# ---------------------------------------------------------------------------


def test_render_binary_ratio() -> None:
    """§A2 binary: ``ratio_of_A_to_B``."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(
                kind=OperatorKind.BINARY,
                op="ratio",
                separator="to",
                args=[
                    StandardNameIR(
                        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY)
                    ),
                    StandardNameIR(
                        base=QuantityOrCarrier(
                            token="temperature", kind=BaseKind.QUANTITY
                        )
                    ),
                ],
            )
        ],
        base=QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "ratio_of_pressure_to_temperature"


def test_render_binary_product() -> None:
    """§A2 binary: ``product_of_A_and_B``."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(
                kind=OperatorKind.BINARY,
                op="product",
                separator="and",
                args=[
                    StandardNameIR(
                        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY)
                    ),
                    StandardNameIR(
                        base=QuantityOrCarrier(
                            token="temperature", kind=BaseKind.QUANTITY
                        )
                    ),
                ],
            )
        ],
        base=QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "product_of_pressure_and_temperature"


# ---------------------------------------------------------------------------
# §A2 rule 5: axis projection prefix (canonical form)
# ---------------------------------------------------------------------------


def test_render_projection_component_prefix() -> None:
    """§A2: component projection → ``<axis>_component_of_<base>``."""
    ir = StandardNameIR(
        projection=AxisProjection(axis="radial", shape=ProjectionShape.COMPONENT),
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "radial_component_of_pressure"


def test_render_projection_toroidal_component() -> None:
    """Toroidal component projection (§A12 row 24)."""
    ir = StandardNameIR(
        projection=AxisProjection(axis="toroidal", shape=ProjectionShape.COMPONENT),
        base=QuantityOrCarrier(token="magnetic_field", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "toroidal_component_of_magnetic_field"


def test_render_projection_coordinate_prefix() -> None:
    """§A2: coordinate projection → ``<axis>_coordinate_of_<carrier>``."""
    ir = StandardNameIR(
        projection=AxisProjection(axis="vertical", shape=ProjectionShape.COORDINATE),
        base=QuantityOrCarrier(token="normalized_minor_radius", kind=BaseKind.GEOMETRY),
    )
    assert compose(ir) == "vertical_coordinate_of_normalized_minor_radius"


def test_render_projection_normalized_toroidal_coordinate() -> None:
    """§A12 row 17: ``normalized_toroidal_flux_coordinate`` with axis projection."""
    ir = StandardNameIR(
        projection=AxisProjection(
            axis="normalized_toroidal", shape=ProjectionShape.COORDINATE
        ),
        base=QuantityOrCarrier(
            token="normalized_toroidal_flux_coordinate",
            kind=BaseKind.GEOMETRY,
        ),
    )
    # Axis 'normalized_toroidal' + coordinate shape
    assert compose(ir) == (
        "normalized_toroidal_coordinate_of_normalized_toroidal_flux_coordinate"
    )


# ---------------------------------------------------------------------------
# §A2 rule 6: locus suffix
# ---------------------------------------------------------------------------


def test_render_locus_of_entity() -> None:
    """§A12 row 1: ``elongation_of_plasma_boundary`` — entity locus with _of_."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="elongation", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.OF,
            token="plasma_boundary",
            type=LocusType.ENTITY,
        ),
    )
    assert compose(ir) == "elongation_of_plasma_boundary"


def test_render_locus_at_position() -> None:
    """Position locus with ``_at_`` suffix."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="temperature", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.AT,
            token="magnetic_axis",
            type=LocusType.POSITION,
        ),
    )
    assert compose(ir) == "temperature_at_magnetic_axis"


def test_render_locus_of_position() -> None:
    """§A12 row 3: position locus with ``_of_`` relation."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="major_radius", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.OF,
            token="x_point",
            type=LocusType.POSITION,
        ),
    )
    assert compose(ir) == "major_radius_of_x_point"


def test_render_locus_entity_of() -> None:
    """Entity locus uses ``_of_`` relation (§A5)."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.OF,
            token="bolometer",
            type=LocusType.ENTITY,
        ),
    )
    assert compose(ir) == "pressure_of_bolometer"


# ---------------------------------------------------------------------------
# §A2 rule 7: mechanism suffix
# ---------------------------------------------------------------------------


def test_render_mechanism_due_to() -> None:
    """``_due_to_<process>`` appended after all other suffixes."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
        mechanism=Process(token="conduction"),
    )
    assert compose(ir) == "pressure_due_to_conduction"


def test_render_mechanism_with_locus() -> None:
    """Locus before mechanism: ``X_at_L_due_to_P``."""
    ir = StandardNameIR(
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.AT,
            token="plasma_boundary",
            type=LocusType.POSITION,
        ),
        mechanism=Process(token="conduction"),
    )
    assert compose(ir) == "pressure_at_plasma_boundary_due_to_conduction"


# ---------------------------------------------------------------------------
# §A2 combined: operator + projection + locus + mechanism ordering
# ---------------------------------------------------------------------------


def test_render_full_a2_example() -> None:
    """§A2 canonical template: ``<op>_of_<axis>_component_of_<qual>_<base>_<locus>``."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op="root_mean_square")
        ],
        projection=AxisProjection(axis="radial", shape=ProjectionShape.COMPONENT),
        qualifiers=[Qualifier(token="electron")],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.AT,
            token="plasma_boundary",
            type=LocusType.POSITION,
        ),
    )
    assert compose(ir) == (
        "root_mean_square_of_radial_component_of_electron_pressure_at_plasma_boundary"
    )


def test_render_nested_operators_outer_first() -> None:
    """§A2: outer operator applied first → outermost op prefix appears leftmost."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op="maximum"),
            OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op="derivative"),
        ],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.AT,
            token="pedestal",
            type=LocusType.POSITION,
        ),
    )
    # maximum is outer → leftmost; derivative is inner → immediately around base
    assert compose(ir) == "maximum_of_derivative_of_pressure_at_pedestal"


def test_render_a12_row_14_nested_operators() -> None:
    """§A12 row 14 exact example: maximum_of_derivative_of_... at pedestal."""
    ir = StandardNameIR(
        operators=[
            OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op="maximum"),
            OperatorApplication(
                kind=OperatorKind.UNARY_PREFIX,
                op="derivative_with_respect_to_normalized_poloidal_flux",
            ),
        ],
        qualifiers=[Qualifier(token="electron")],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.AT,
            token="pedestal",
            type=LocusType.POSITION,
        ),
    )
    assert compose(ir) == (
        "maximum_of_derivative_with_respect_to_normalized_poloidal_flux_of_"
        "electron_pressure_at_pedestal"
    )


def test_render_a12_row_22_maximum_power_flux_density() -> None:
    """§A12 row 22: ``maximum_of_power_flux_density_at_inner_divertor_target``."""
    ir = StandardNameIR(
        operators=[OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op="maximum")],
        base=QuantityOrCarrier(token="power_flux_density", kind=BaseKind.QUANTITY),
        locus=LocusRef(
            relation=LocusRelation.AT,
            token="inner_divertor_target",
            type=LocusType.POSITION,
        ),
    )
    assert compose(ir) == "maximum_of_power_flux_density_at_inner_divertor_target"


# ---------------------------------------------------------------------------
# §A2 qualifier rendering
# ---------------------------------------------------------------------------


def test_render_single_qualifier() -> None:
    """Qualifier token is prefixed directly before the base."""
    ir = StandardNameIR(
        qualifiers=[Qualifier(token="electron")],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "electron_pressure"


def test_render_multiple_qualifiers() -> None:
    """Multiple qualifiers are concatenated in list order before base."""
    ir = StandardNameIR(
        qualifiers=[Qualifier(token="fast"), Qualifier(token="ion")],
        base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY),
    )
    assert compose(ir) == "fast_ion_pressure"


# ---------------------------------------------------------------------------
# Render errors (invalid IR)
# ---------------------------------------------------------------------------


def test_render_error_on_missing_separator_for_binary() -> None:
    """Binary operator without separator raises ValidationError at construction."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        # separator required for binary operators — pydantic should catch this
        OperatorApplication(
            kind=OperatorKind.BINARY,
            op="ratio",
            # separator intentionally missing
            args=[
                StandardNameIR(
                    base=QuantityOrCarrier(token="pressure", kind=BaseKind.QUANTITY)
                ),
                StandardNameIR(
                    base=QuantityOrCarrier(token="temperature", kind=BaseKind.QUANTITY)
                ),
            ],
        )
