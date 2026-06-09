"""Population segment: modifier qualifiers (energy-state, orbit class, …) are
retained on the StandardName model as a scalar ``population`` segment rather
than being dropped or folded into ``physical_base``.

Decomposition contract (codex 2026-06-09): ``fast``/``thermal``/``trapped``/…
are population qualifiers composed orthogonally with a species ``subject`` and
the ``physical_base`` — e.g. ``trapped_fast_ion_density`` →
population=``trapped_fast``, subject=``ion``, base=``density`` — and must
round-trip.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name


@pytest.mark.parametrize(
    ("name", "population", "subject", "base"),
    [
        # Single population qualifier + species + base.
        ("trapped_electron_density", "trapped", "electron", "density"),
        ("co_passing_ion_density", "co_passing", "ion", "density"),
    ],
)
def test_population_retained_and_round_trips(name, population, subject, base):
    model = parse_standard_name(name)
    assert model.population == population, (
        f"{name!r}: population dropped/folded (got {model.population!r})"
    )
    assert (model.subject and model.subject.value) == subject
    assert model.physical_base == base
    # Round-trip: the population prefix must be reproduced verbatim.
    assert compose_standard_name(model) == name


def test_bare_species_has_no_population():
    model = parse_standard_name("electron_density")
    assert model.population is None
    assert compose_standard_name(model) == "electron_density"
