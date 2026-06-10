"""Lexical thermal_pressure / thermal_energy bases + collision guard.

``thermal pressure`` is a thermodynamic compound (contrasting with magnetic /
fast-particle pressure): ``thermal`` attaches to the BASE, not to a species
population. Likewise ``thermal_energy`` (total thermal stored energy W_th).
Both are lexical physical-base tokens; longest-suffix base matching wins over
population peeling, so ``plasma_thermal_pressure`` keeps its meaning and
round-trips identically instead of re-ordering to ``thermal_plasma_pressure``.

Population readings are preserved when a subject intervenes
(``thermal_ion_pressure`` = population thermal + subject ion + base pressure),
and a model-level collision guard rejects modifier+base combinations whose
rendered adjacent form IS a lexical base (population=thermal + base=pressure
renders the string ``thermal_pressure`` and would not round-trip).
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name
from imas_standard_names.grammar.model import StandardName


def _v(seg):
    return seg.value if seg is not None else None


# ---------------------------------------------------------------------------
# Exact round-trips: thermal attaches to the base
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "aggregation", "subject", "base"),
    [
        ("thermal_pressure", None, None, "thermal_pressure"),
        ("plasma_thermal_pressure", None, None, "plasma_thermal_pressure"),
        ("total_plasma_thermal_pressure", "total", None, "plasma_thermal_pressure"),
        ("electron_thermal_pressure", None, "electron", "thermal_pressure"),
        ("ion_thermal_pressure", None, "ion", "thermal_pressure"),
        ("thermal_energy", None, None, "thermal_energy"),
        ("electron_thermal_energy", None, "electron", "thermal_energy"),
    ],
)
def test_lexical_thermal_base_round_trips(name, aggregation, subject, base):
    model = parse_standard_name(name)
    assert _v(model.aggregation) == aggregation, f"{name!r}: aggregation"
    assert model.population is None, f"{name!r}: population must be empty"
    assert _v(model.subject) == subject, f"{name!r}: subject"
    assert model.physical_base == base, f"{name!r}: base"
    assert compose_standard_name(model) == name


# ---------------------------------------------------------------------------
# Population readings preserved (no suffix collision)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "population", "subject"),
    [
        ("thermal_ion_pressure", "thermal", "ion"),
        ("thermal_electron_pressure", "thermal", "electron"),
        ("fast_ion_pressure", "fast", "ion"),
    ],
)
def test_population_subject_reading_preserved(name, population, subject):
    model = parse_standard_name(name)
    assert _v(model.population) == population
    assert _v(model.subject) == subject
    assert model.physical_base == "pressure"
    assert compose_standard_name(model) == name


# ---------------------------------------------------------------------------
# Collision guard: modifier+base rendering a lexical base is rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("population", "base", "lexical"),
    [
        ("thermal", "pressure", "thermal_pressure"),
        ("thermal", "energy", "thermal_energy"),
    ],
)
def test_collision_guard_rejects_lexical_base_render(population, base, lexical):
    with pytest.raises(ValueError, match=lexical):
        StandardName(population=population, physical_base=base)


def test_collision_guard_skipped_when_subject_intervenes():
    # thermal_ion_pressure: subject sits between population and base, so no
    # lexical-base collision is possible.
    model = StandardName(population="thermal", subject="ion", physical_base="pressure")
    assert model.compose() == "thermal_ion_pressure"


def test_non_colliding_population_base_still_allowed():
    # fast_pressure is not a lexical base; population=fast + pressure is fine.
    model = StandardName(population="fast", physical_base="pressure")
    assert model.compose() == "fast_pressure"
