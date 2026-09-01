"""Population + orbit segments: modifier qualifiers (energy-state and orbit
class) are retained on the StandardName model as orthogonal single-token
``population`` / ``orbit`` segments rather than dropped or folded into
``physical_base``.

Decomposition contract (rc32): ``fast``/``thermal``/… are population
qualifiers; ``trapped``/``co_passing``/… are orbit qualifiers; both compose
orthogonally with a species ``subject`` and render before it —
``trapped_fast_ion_density`` → orbit=trapped, population=fast, subject=ion,
base=density — and must round-trip.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name


def _v(seg):
    return seg.value if seg is not None else None


@pytest.mark.parametrize(
    ("name", "aggregation", "orbit", "population", "subject", "base"),
    [
        # population only
        ("fast_ion_pressure", None, None, "fast", "ion", "pressure"),
        ("thermal_electron_density", None, None, "thermal", "electron", "density"),
        # 'plasma' is a channel-qualifier (channel_qualifiers.yml): it peels
        # into the channel_qualifier segment, leaving current as the base.
        # 'total' is an aggregation token (not population) as of the
        # aggregation-segment split.
        ("total_plasma_current", "total", None, None, None, "current"),
        # orbit only
        ("trapped_electron_density", None, "trapped", None, "electron", "density"),
        ("co_passing_ion_density", None, "co_passing", None, "ion", "density"),
        # orbit + population stacked (one token each, distinct segments)
        ("trapped_fast_ion_density", None, "trapped", "fast", "ion", "density"),
        # aggregation + population stacked (orthogonal dimensions)
        ("total_fast_ion_energy", "total", None, "fast", "ion", "energy"),
    ],
)
def test_population_orbit_retained_and_round_trip(
    name, aggregation, orbit, population, subject, base
):
    model = parse_standard_name(name)
    assert _v(model.aggregation) == aggregation, f"{name!r}: aggregation"
    assert _v(model.orbit) == orbit, f"{name!r}: orbit"
    assert _v(model.population) == population, f"{name!r}: population"
    assert _v(model.subject) == subject, f"{name!r}: subject"
    assert model.physical_base == base
    assert compose_standard_name(model) == name


def test_bare_species_has_no_modifiers():
    model = parse_standard_name("electron_density")
    assert model.population is None
    assert model.orbit is None
    assert compose_standard_name(model) == "electron_density"
