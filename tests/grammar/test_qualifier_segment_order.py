"""Canonical intra-order of a multi-token refined qualifier segment.

Stacked scoping qualifiers render in qualifier-category order (stable within a
category), mirroring the zone-order mechanism: compose() canonicalizes any
authored order, and parse_standard_name rejects a non-canonical spelling via
the round-trip.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    NonCanonicalNameError,
    StandardName,
    compose_standard_name,
    parse_standard_name,
)


def test_cross_category_qualifiers_canonicalize():
    # incident (energy) ranks before implicit (engineering); either authored
    # order composes to the same canonical string.
    a = StandardName(
        qualifier=("implicit", "incident"),
        channel="energy",
        physical_base="source_rate",
    )
    b = StandardName(
        qualifier=("incident", "implicit"),
        channel="energy",
        physical_base="source_rate",
    )
    assert a.compose() == b.compose() == "incident_implicit_energy_source_rate"


def test_same_category_qualifiers_keep_authored_order():
    # breakdown and stray are both in the `state` category; the stable sort
    # preserves their authored order.
    name = "breakdown_stray_magnetic_field_magnitude"
    parsed = parse_standard_name(name)
    assert compose_standard_name(parsed) == name


def test_non_canonical_spelling_rejected():
    with pytest.raises(NonCanonicalNameError):
        parse_standard_name("implicit_incident_energy_source_rate")


def test_canonical_spelling_round_trips():
    name = "incident_implicit_energy_source_rate"
    assert compose_standard_name(parse_standard_name(name)) == name
