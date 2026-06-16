"""Postfix canonicalization of the scalar-extraction operators.

The scalar-extraction operators ``real_part``, ``imaginary_part`` and
``amplitude`` are canonical **postfix** operators (rendered ``<base>_<op>``,
like ``magnitude``/``moment``/``waveform``), not prefix ``<op>_of_<base>``.

Postfix is required for two reasons:

1. Consistency — the other scalar-extraction / spectral operators
   (``magnitude``, ``fourier_coefficient``, ``moment``, ``waveform``) are
   already postfix; these three were the only prefix outliers.
2. Composability with a projection — the prefix ``<op>_of_<base>`` form
   cannot combine with a component/coordinate projection because the flat
   model treats ``transformation`` and ``component`` as mutually exclusive
   (``amplitude_of_radial_electric_field`` raises ValidationError), whereas
   the postfix form ``radial_electric_field_amplitude`` round-trips.

There is exactly ONE token per operation: the previously-duplicated
``real_part_postfix`` / ``imaginary_part_postfix`` tokens are removed.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)


def _round_trip(name: str) -> str:
    return compose_standard_name(parse_standard_name(name))


# Canonical postfix scalar-extraction names that must round-trip.
POSTFIX_ROUND_TRIP = [
    "electric_field_real_part",
    "electric_field_imaginary_part",
    "electric_field_amplitude",
    "magnetic_field_real_part",
]

# Projection-combined postfix names — these FAILED in rc40 (the prefix
# ``_of_`` form cannot carry a projection) and MUST now round-trip.
PROJECTION_COMBINED_ROUND_TRIP = [
    "radial_electric_field_real_part",
    "parallel_magnetic_field_amplitude",
    "radial_electric_field_amplitude",
]

# Pre-existing postfix operator that must keep round-tripping (regression).
REGRESSION_ROUND_TRIP = [
    "magnetic_field_magnitude",
]

# Old prefix / duplicate forms that must NO LONGER be canonical: either they
# fail to parse outright (removed / no longer postfix tokens) or they
# normalize to a different (postfix) canonical string.
OLD_FORMS_NOT_CANONICAL = [
    # old prefix canonical — token is no longer a prefix operator
    "real_part_of_electric_field",
    "imaginary_part_of_electric_field",
    "amplitude_of_electric_field",
    # removed duplicate postfix tokens
    "electric_field_real_part_postfix",
    "electric_field_imaginary_part_postfix",
]


@pytest.mark.parametrize("name", POSTFIX_ROUND_TRIP)
def test_postfix_scalar_extraction_round_trips(name: str) -> None:
    assert _round_trip(name) == name


@pytest.mark.parametrize("name", PROJECTION_COMBINED_ROUND_TRIP)
def test_projection_combined_postfix_round_trips(name: str) -> None:
    """rc40 raised on these; the postfix convention makes them valid."""
    assert _round_trip(name) == name


@pytest.mark.parametrize("name", REGRESSION_ROUND_TRIP)
def test_existing_postfix_operator_still_round_trips(name: str) -> None:
    assert _round_trip(name) == name


@pytest.mark.parametrize("name", OLD_FORMS_NOT_CANONICAL)
def test_old_forms_are_not_canonical(name: str) -> None:
    """Old prefix / duplicate-token forms must not survive as-is.

    They either fail to parse (token removed / no longer a prefix op) or
    normalize to a different canonical string.
    """
    try:
        result = _round_trip(name)
    except Exception:
        return  # acceptable: the old form no longer parses
    assert result != name, (
        f"{name!r} should no longer be canonical but round-tripped unchanged"
    )
