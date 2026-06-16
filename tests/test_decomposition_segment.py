"""Tests for the decomposition segment (plan 29 / ADR-4 F3).

Decomposition is a pseudo-segment (like transformation) that prefixes the
physical_base with Fourier / spectral / mode-number tokens, e.g.::

    fourier_coefficient_of_magnetic_field
    n_equals_1_magnetic_field
    m_over_n_equals_2_over_1_magnetic_field
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    StandardName,
    compose_standard_name,
    parse_standard_name,
)
from imas_standard_names.grammar.model_types import Decomposition, Transformation

# Decomposition tokens use rc20 forms (fourier_coefficient_of, n_equals_1, …)
# that are not yet present in the operators registry (plan 38 §A7).
_XFAIL_RC20 = pytest.mark.xfail(
    strict=True,
    reason="rc20 decomposition token forms not yet in operators registry (plan 38 §A7)",
)


@_XFAIL_RC20
@pytest.mark.parametrize(
    "name",
    [
        "fourier_coefficient_of_magnetic_field",
        "fourier_amplitude_of_electron_density",
        "fourier_phase_of_magnetic_field",
        "cosine_coefficient_of_magnetic_field",
        "sine_coefficient_of_magnetic_field",
        "n_equals_1_magnetic_field",
        "n_equals_2_electron_density",
        "m_equals_1_magnetic_field",
        "m_equals_2_magnetic_field",
        "m_over_n_equals_2_over_1_magnetic_field",
    ],
)
def test_decomposition_round_trip(name: str) -> None:
    """Parse then compose should recover the original name for every token."""
    parsed = parse_standard_name(name)
    assert parsed.decomposition is not None
    assert parsed.physical_base in {"magnetic_field", "electron_density"}
    assert compose_standard_name(parsed) == name


@_XFAIL_RC20
def test_decomposition_is_set_correctly() -> None:
    """Decomposition field should be populated with the matched enum value."""
    parsed = parse_standard_name("fourier_coefficient_of_magnetic_field")
    assert parsed.decomposition == Decomposition.FOURIER_COEFFICIENT_OF
    assert parsed.physical_base == "magnetic_field"
    assert parsed.transformation is None


@_XFAIL_RC20
def test_decomposition_mode_number_prefix() -> None:
    parsed = parse_standard_name("n_equals_1_magnetic_field")
    assert parsed.decomposition == Decomposition.N_EQUALS_1
    assert parsed.physical_base == "magnetic_field"


@_XFAIL_RC20
def test_decomposition_mode_number_ratio() -> None:
    parsed = parse_standard_name("m_over_n_equals_2_over_1_magnetic_field")
    assert parsed.decomposition == Decomposition.M_OVER_N_EQUALS_2_OVER_1
    assert parsed.physical_base == "magnetic_field"


@_XFAIL_RC20
def test_decomposition_with_prefix_segments() -> None:
    """Decomposition should combine with non-conflicting prefix segments."""
    name = "electron_fourier_coefficient_of_magnetic_field"
    parsed = parse_standard_name(name)
    assert parsed.decomposition == Decomposition.FOURIER_COEFFICIENT_OF
    assert parsed.subject == "electron"
    assert parsed.physical_base == "magnetic_field"
    assert compose_standard_name(parsed) == name


def test_decomposition_coexists_with_transformation() -> None:
    """A prefix transformation and a postfix decomposition now coexist.

    The two operators occupy structurally distinct, unambiguous positions in
    the canonical string — the prefix renders at the front
    (``<transform>_of_<...>``) and the postfix at the tail
    (``<...>_<decomposition>``). The parser peels the trailing postfix before
    the leading prefix, so the round-trip is deterministic. The previously
    cited ``square_of_..._fourier_coefficient`` ambiguity does not exist.
    """
    model = StandardName(
        transformation="square",
        decomposition="fourier_coefficient",
        physical_base="magnetic_field",
    )
    name = "square_of_magnetic_field_fourier_coefficient"
    assert compose_standard_name(model) == name
    # Full string round-trip recovers the same two operator slots.
    reparsed = parse_standard_name(name)
    assert reparsed.transformation == Transformation.SQUARE
    assert reparsed.decomposition == Decomposition.FOURIER_COEFFICIENT
    assert compose_standard_name(reparsed) == name


def test_decomposition_exclusive_with_geometric_base() -> None:
    with pytest.raises(ValueError, match="geometric_base"):
        StandardName(
            decomposition="fourier_coefficient_of",
            geometric_base="area",
        )
