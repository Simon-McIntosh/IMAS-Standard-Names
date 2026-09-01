"""Compositional locus geometric-qualifiers.

A qualifiable locus FEATURE (strike_point, x_point, divertor_target, midplane,
separatrix) composes with ordered geometric qualifiers (primary/secondary,
upper/lower, inner/outer) instead of enumerating each variant as a flat token.
Scales to advanced divertor topologies (snowflake / X / super-X) without new
tokens per combination.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import (
    compose_standard_name,
    parse_standard_name,
)


@pytest.mark.parametrize(
    ("name", "feature", "qualifiers"),
    [
        ("radial_coordinate_of_strike_point", "strike_point", ()),
        ("radial_coordinate_of_inner_strike_point", "strike_point", ("inner",)),
        ("radial_coordinate_of_outer_strike_point", "strike_point", ("outer",)),
        # snowflake: two composed qualifiers, canonical order upper→outer
        (
            "radial_coordinate_of_upper_outer_strike_point",
            "strike_point",
            ("upper", "outer"),
        ),
        ("radial_coordinate_of_primary_x_point", "x_point", ("primary",)),
        ("radial_coordinate_of_secondary_x_point", "x_point", ("secondary",)),
        ("vertical_coordinate_of_inner_divertor_target", "divertor_target", ("inner",)),
        ("electron_temperature_at_outer_midplane", "midplane", ("outer",)),
        ("temperature_at_secondary_separatrix", "separatrix", ("secondary",)),
    ],
)
def test_qualified_locus_round_trips(name, feature, qualifiers):
    parsed = parse_standard_name(name)
    assert parsed.locus_qualifiers == qualifiers
    # feature lands in the geometry/position field, not the qualifier tuple
    assert feature in (parsed.geometry, parsed.position, parsed.object)
    assert compose_standard_name(parsed) == name


def test_non_canonical_qualifier_order_rejected():
    # canonical order is primary/secondary → upper/lower → inner/outer;
    # outer_upper is non-canonical and must be rejected.
    with pytest.raises(ValueError):
        parse_standard_name("radial_coordinate_of_outer_upper_strike_point")


def test_qualifier_on_non_qualifiable_feature_rejected():
    # magnetic_axis is not a qualifiable feature — inner_magnetic_axis is not a
    # locus and must not be fabricated.
    with pytest.raises(ValueError):
        parse_standard_name("radial_coordinate_of_inner_magnetic_axis")


def test_flat_tokens_removed_but_names_preserved():
    # The old flat enumerated tokens are gone from the registry, but names that
    # used them re-parse compositionally and render identically (migration-safe).
    from imas_standard_names.grammar import vocab_loaders

    loci = set(vocab_loaders.load_locus_registry().loci)
    for removed in (
        "inner_strike_point",
        "outer_strike_point",
        "primary_strike_point",
        "secondary_strike_point",
        "primary_x_point",
        "secondary_x_point",
        "inner_divertor_target",
        "outer_divertor_target",
        "inner_midplane",
        "outer_midplane",
        "secondary_separatrix",
    ):
        assert removed not in loci, f"{removed} should be composed, not a flat token"
