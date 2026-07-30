"""Lossless validation of ordered operator-expression trees."""

import pytest

from imas_standard_names import compose, parse
from imas_standard_names.grammar.ir import OperatorKind
from imas_standard_names.grammar.parser import ParseError

INVERSE_SQUARED_RADIUS = "flux_surface_averaged_inverse_of_square_of_major_radius"
SQUARED_FIELD_MAGNITUDE = "flux_surface_averaged_square_of_magnetic_field_magnitude"
GRADIENT_TO_FIELD_RATIO = (
    "flux_surface_averaged_ratio_of"
    "_square_of_toroidal_flux_coordinate_gradient_magnitude"
    "_to_square_of_magnetic_field_magnitude"
)


@pytest.mark.parametrize(
    "name",
    [
        INVERSE_SQUARED_RADIUS,
        SQUARED_FIELD_MAGNITUDE,
        GRADIENT_TO_FIELD_RATIO,
    ],
)
def test_metric_operator_trees_strictly_validate_and_round_trip(name: str) -> None:
    result = parse(name, strict=True)

    assert compose(result.ir) == name


def test_unary_chain_is_outermost_first() -> None:
    ir = parse(INVERSE_SQUARED_RADIUS, strict=True).ir

    assert [operator.op for operator in ir.operators] == [
        "flux_surface_averaged",
        "inverse",
        "square",
    ]


def test_postfix_operator_stays_inside_prefix_operators() -> None:
    ir = parse(SQUARED_FIELD_MAGNITUDE, strict=True).ir

    assert [(operator.op, operator.kind) for operator in ir.operators] == [
        ("flux_surface_averaged", OperatorKind.UNARY_PREFIX),
        ("square", OperatorKind.UNARY_PREFIX),
        ("magnitude", OperatorKind.UNARY_POSTFIX),
    ]


def test_registered_base_wins_before_bare_prefix_peeling() -> None:
    name = "flux_surface_averaged_metric_magnitude"
    ir = parse(name).ir

    assert ir.base.token == "flux_surface_averaged_metric"
    assert [operator.op for operator in ir.operators] == ["magnitude"]
    assert compose(ir) == name


def test_binary_operands_keep_their_ordered_operator_trees() -> None:
    ir = parse(GRADIENT_TO_FIELD_RATIO, strict=True).ir
    binary = next(
        operator for operator in ir.operators if operator.kind is OperatorKind.BINARY
    )

    assert [operator.op for operator in binary.args[0].operators] == [
        "square",
        "magnitude",
    ]
    assert [operator.op for operator in binary.args[1].operators] == [
        "square",
        "magnitude",
    ]


def test_equal_precedence_operators_are_not_reordered() -> None:
    inverse_then_square = parse("inverse_of_square_of_pressure", strict=True).ir
    square_then_inverse = parse("square_of_inverse_of_pressure", strict=True).ir

    assert [operator.op for operator in inverse_then_square.operators] == [
        "inverse",
        "square",
    ]
    assert [operator.op for operator in square_then_inverse.operators] == [
        "square",
        "inverse",
    ]
    assert inverse_then_square != square_then_inverse


def test_outer_operator_respects_registered_precedence() -> None:
    assert (
        compose(parse("maximum_of_gradient_of_pressure", strict=True).ir)
        == "maximum_of_gradient_of_pressure"
    )

    with pytest.raises(ParseError, match="precedence"):
        parse("gradient_of_maximum_of_pressure", strict=True)


def test_explicit_prefix_respects_inner_bare_prefix_precedence() -> None:
    with pytest.raises(ParseError, match="precedence"):
        parse("inverse_of_volume_averaged_electron_temperature", strict=True)

    name = "volume_averaged_inverse_of_electron_temperature"
    assert compose(parse(name, strict=True).ir) == name


@pytest.mark.parametrize(
    "name",
    [
        "magnetic_moment",
        "square_of_magnetic_moment",
    ],
)
def test_registered_atomic_base_wins_before_postfix_operator(name: str) -> None:
    ir = parse(name, strict=True).ir

    assert ir.base.token == "magnetic_moment"
    assert all(operator.op != "moment" for operator in ir.operators)
    assert compose(ir) == name


@pytest.mark.parametrize(
    "name",
    [
        "magnetic_field_real_part",
        "magnetic_field_imaginary_part",
        "square_of_magnetic_field_fourier_coefficient",
    ],
)
def test_registered_decomposition_forms_remain_strictly_valid(name: str) -> None:
    assert compose(parse(name, strict=True).ir) == name


@pytest.mark.parametrize(
    "name",
    [
        "flux_surface_averaged_inverse_square_major_radius",
        "flux_surface_averaged_square_magnetic_field_magnitude",
        (
            "flux_surface_averaged_ratio_of"
            "_square_toroidal_flux_coordinate_gradient_magnitude"
            "_to_square_magnetic_field_magnitude"
        ),
    ],
)
def test_glued_operator_spellings_are_not_strictly_valid(name: str) -> None:
    with pytest.raises(ParseError, match="operator spelling"):
        parse(name, strict=True)


@pytest.mark.parametrize(
    "name,reason",
    [
        ("gradient_of_magnetic_field", "requires one of"),
        ("pressure_magnitude", "requires one of"),
        ("temperature", "requires qualification"),
        ("ratio_of_unregistered_quantity_to_electron_density", "not registered"),
        (
            "flux_surface_averaged_square_of_safety_factor",
            "constant on a flux surface",
        ),
    ],
)
def test_strict_validation_enforces_recursive_operator_semantics(
    name: str, reason: str
) -> None:
    with pytest.raises(ParseError, match=reason):
        parse(name, strict=True)


def test_invalid_deep_binary_chain_parses_each_substring_once(monkeypatch) -> None:
    """Memoization bounds adversarial split exploration by distinct substrings."""
    from imas_standard_names.grammar import parser

    calls: list[tuple[str, bool]] = []
    original = parser._parse_uncached

    def counted(name, vocabs, *, strict):
        calls.append((name, strict))
        return original(name, vocabs, strict=strict)

    monkeypatch.setattr(parser, "_parse_uncached", counted)
    invalid = "ratio_of_" + "_to_".join(["electron_density"] * 10 + ["unknown"])

    with pytest.raises(ParseError):
        parse(invalid, strict=True)

    assert len(calls) == len(set(calls))
    assert len(calls) <= len(invalid) ** 2
