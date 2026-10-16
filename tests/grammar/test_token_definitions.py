"""Population, zone and aggregation tokens carry definitions that render."""

from __future__ import annotations

from imas_standard_names.grammar import vocab_loaders
from imas_standard_names.grammar.model_types import Aggregation, Population, Zone
from imas_standard_names.grammar.terms import select_conventions
from imas_standard_names.grammar.vocab_loaders import (
    load_aggregations,
    load_populations,
    load_zones,
)


def test_loaders_return_the_recorded_token_sets():
    """The entries shape changes no token and no zone order.

    The three ``StrEnum``s are the token record the plain lists held, so they
    are the frozen arm this test compares the loaders against.
    """
    assert load_populations() == frozenset(member.value for member in Population)
    assert load_aggregations() == frozenset(member.value for member in Aggregation)
    assert load_zones() == tuple(member.value for member in Zone)


def test_definitions_carry_a_population_a_zone_and_an_aggregation():
    definitions = vocab_loaders._vocabulary_definitions()
    assert definitions["fast"]
    assert definitions["lower"]
    assert definitions["total"]


def test_a_definition_renders_for_a_name_carrying_the_token():
    definitions = vocab_loaders._vocabulary_definitions()
    for name, token in (
        ("fast_ion_pressure", "fast"),
        ("lower_outer_squareness_of_flux_surface", "lower"),
        ("total_plasma_current", "total"),
    ):
        applied = select_conventions(name)
        rendered = [
            entry.definition for entry in applied.definitions if entry.token == token
        ]
        assert rendered == [definitions[token]], name


def test_a_zone_definition_names_the_segment_the_token_was_used_in():
    applied = select_conventions("lower_outer_squareness_of_flux_surface")
    assert [(entry.token, entry.segment) for entry in applied.definitions] == [
        ("lower", "zone"),
        ("outer", "zone"),
    ]


def test_a_token_without_a_definition_loads_and_contributes_nothing():
    assert "core" in load_zones()
    assert "core" not in vocab_loaders._vocabulary_definitions()
    assert select_conventions("core_electron_temperature").definitions == ()
