"""Tests for uncertainty modifier operators (rc23 — B9 error siblings).

Verifies that the three uncertainty operators (upper_uncertainty,
lower_uncertainty, uncertainty_index) parse correctly, round-trip,
and compose expected canonical forms from parent names.

These operators map IMAS ``_error_upper`` / ``_error_lower`` /
``_error_index`` companion fields to standard-name grammar modifiers.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.ir import (
    BaseKind,
    OperatorKind,
)
from imas_standard_names.grammar.parser import (
    ParseResult,
    Vocabularies,
    load_default_vocabularies,
    parse,
)
from imas_standard_names.grammar.render import compose


@pytest.fixture(scope="module")
def vocabs() -> Vocabularies:
    """Load the full production vocabulary for testing."""
    return load_default_vocabularies()


# -----------------------------------------------------------------------
# Round-trip tests: parse ↔ compose identity
# -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "upper_uncertainty_of_plasma_current",
        "lower_uncertainty_of_plasma_current",
        "uncertainty_index_of_plasma_current",
        "upper_uncertainty_of_pressure",
        "lower_uncertainty_of_temperature",
        "uncertainty_index_of_major_radius",
    ],
)
def test_uncertainty_round_trip(vocabs: Vocabularies, name: str):
    """Uncertainty names should round-trip: compose(parse(name)) == name."""
    result = parse(name, vocabs=vocabs)
    assert isinstance(result, ParseResult)
    assert compose(result.ir) == name


# -----------------------------------------------------------------------
# Structure tests: verify IR decomposition
# -----------------------------------------------------------------------


def test_upper_uncertainty_decomposition(vocabs: Vocabularies):
    """upper_uncertainty_of_temperature → correct IR shape."""
    name = "upper_uncertainty_of_temperature"
    result = parse(name, vocabs=vocabs)
    ir = result.ir

    # Outer operator is upper_uncertainty (unary_prefix)
    assert len(ir.operators) == 1
    assert ir.operators[0].op == "upper_uncertainty"
    assert ir.operators[0].kind is OperatorKind.UNARY_PREFIX

    # Base is temperature
    assert ir.base.token == "temperature"
    assert ir.base.kind is BaseKind.QUANTITY


def test_lower_uncertainty_decomposition(vocabs: Vocabularies):
    """lower_uncertainty_of_pressure → correct IR shape."""
    name = "lower_uncertainty_of_pressure"
    result = parse(name, vocabs=vocabs)
    ir = result.ir

    assert len(ir.operators) == 1
    assert ir.operators[0].op == "lower_uncertainty"
    assert ir.operators[0].kind is OperatorKind.UNARY_PREFIX
    assert ir.base.token == "pressure"


def test_uncertainty_index_decomposition(vocabs: Vocabularies):
    """uncertainty_index_of_temperature → correct IR shape."""
    name = "uncertainty_index_of_temperature"
    result = parse(name, vocabs=vocabs)
    ir = result.ir

    assert len(ir.operators) == 1
    assert ir.operators[0].op == "uncertainty_index"
    assert ir.operators[0].kind is OperatorKind.UNARY_PREFIX
    assert ir.base.token == "temperature"


# -----------------------------------------------------------------------
# Nested operator: uncertainty wrapping another operator
# -----------------------------------------------------------------------


def test_uncertainty_wrapping_nested_operator(vocabs: Vocabularies):
    """upper_uncertainty_of_time_derivative_of_pressure should parse."""
    name = "upper_uncertainty_of_time_derivative_of_pressure"
    result = parse(name, vocabs=vocabs)
    ir = result.ir

    # Two operators: outer = upper_uncertainty, inner = time_derivative
    assert len(ir.operators) == 2
    assert ir.operators[0].op == "upper_uncertainty"
    assert ir.operators[1].op == "time_derivative"
    assert ir.base.token == "pressure"
    assert compose(ir) == name


# -----------------------------------------------------------------------
# All three siblings from the same parent
# -----------------------------------------------------------------------


_ERROR_SUFFIX_MAP = {
    "_error_upper": "upper_uncertainty",
    "_error_lower": "lower_uncertainty",
    "_error_index": "uncertainty_index",
}


@pytest.mark.parametrize(
    ("parent_name", "suffix", "expected_op"),
    [
        ("plasma_current", "_error_upper", "upper_uncertainty"),
        ("plasma_current", "_error_lower", "lower_uncertainty"),
        ("plasma_current", "_error_index", "uncertainty_index"),
    ],
)
def test_sibling_naming_pattern(
    vocabs: Vocabularies,
    parent_name: str,
    suffix: str,
    expected_op: str,
):
    """Given a parent standard name, the error sibling should parse correctly."""
    sibling_name = f"{expected_op}_of_{parent_name}"
    result = parse(sibling_name, vocabs=vocabs)
    assert isinstance(result, ParseResult)
    assert result.ir.operators[0].op == expected_op
    assert compose(result.ir) == sibling_name
