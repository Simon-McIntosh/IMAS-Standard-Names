"""Value-parameterized at-loci and strict locus projection.

Grammar production ``at_<position>_equal_to_<value>`` where ``<position>`` is
a registry position token and ``<value>`` is a numeric literal with
underscores as decimal separators (``0_95`` = 0.95, ``1_0`` = 1.0, ``2`` = 2).
The model carries the value in the ``position_value`` extension field and
compose() renders ``at_<position>_equal_to_<position_value>``.

These tests also pin the strict-projection contract: a locus token the model
cannot represent is a hard error — silently dropping it would lose the entire
locus and collide with the locus-free name (the rc33 deep-review bug:
``safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95`` degraded
to bare ``safety_factor``).
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name
from imas_standard_names.grammar.model import StandardName

Q95_NAME = "safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95"


# ---------------------------------------------------------------------------
# Round-trips
# ---------------------------------------------------------------------------


def test_q95_round_trips_exactly():
    model = parse_standard_name(Q95_NAME)
    assert model.physical_base == "safety_factor"
    assert model.position is not None
    assert model.position.value == "normalized_poloidal_magnetic_flux"
    assert model.position_value == "0_95"
    assert compose_standard_name(model) == Q95_NAME


@pytest.mark.parametrize(
    ("name", "value"),
    [
        (
            "electron_temperature_at_normalized_poloidal_magnetic_flux_equal_to_1_0",
            "1_0",
        ),
        ("electron_temperature_at_normalized_poloidal_magnetic_flux_equal_to_2", "2"),
    ],
)
def test_value_literal_forms_round_trip(name, value):
    model = parse_standard_name(name)
    assert model.position_value == value
    assert compose_standard_name(model) == name


def test_explicit_construction_composes():
    model = StandardName(
        physical_base="safety_factor",
        position="normalized_poloidal_magnetic_flux",
        position_value="0_95",
    )
    assert model.compose() == Q95_NAME


def test_plain_position_locus_unaffected():
    name = "electron_temperature_at_magnetic_axis"
    model = parse_standard_name(name)
    assert model.position_value is None
    assert compose_standard_name(model) == name


def test_bare_safety_factor_remains_distinct():
    model = parse_standard_name("safety_factor")
    assert model.position is None
    assert model.position_value is None
    assert compose_standard_name(model) == "safety_factor"


# ---------------------------------------------------------------------------
# Value validation
# ---------------------------------------------------------------------------


def test_non_numeric_value_rejected_at_parse():
    # 'abc' fails the numeric-literal pattern, so the token never registry-
    # matches and the strict projection raises on the unknown locus token.
    with pytest.raises(ValueError, match="position"):
        parse_standard_name(
            "safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_abc"
        )


@pytest.mark.parametrize("bad_value", ["abc", "0_95_5", "_95", "0__95", "0.95"])
def test_position_value_field_pattern(bad_value):
    with pytest.raises(ValueError, match="position_value"):
        StandardName(
            physical_base="safety_factor",
            position="normalized_poloidal_magnetic_flux",
            position_value=bad_value,
        )


def test_position_value_requires_position():
    with pytest.raises(ValueError, match="position"):
        StandardName(physical_base="safety_factor", position_value="0_95")


# ---------------------------------------------------------------------------
# Strict locus projection (no silent drops)
# ---------------------------------------------------------------------------


def test_unknown_at_locus_raises():
    with pytest.raises(ValueError, match="made_up_place"):
        parse_standard_name("electron_temperature_at_made_up_place")


def test_unknown_over_locus_raises():
    # The ``over`` relation is valid only for region-typed loci (closed
    # vocabulary). An unregistered region does not strip as a locus; it stays
    # in the residue and the unknown-base match fails, rejecting the name.
    with pytest.raises(ValueError, match="made_up_zone"):
        parse_standard_name("electron_density_over_made_up_zone")


# ---------------------------------------------------------------------------
# Registry token rename: normalized_poloidal_magnetic_flux
# ---------------------------------------------------------------------------


def test_legacy_short_registry_token_no_longer_silently_parses():
    # The legacy short token was renamed to align with the
    # poloidal_magnetic_flux physical-base family; with strict projection the
    # unregistered short form now raises instead of silently dropping.
    with pytest.raises(ValueError):
        parse_standard_name("electron_temperature_at_normalized_poloidal_flux")
