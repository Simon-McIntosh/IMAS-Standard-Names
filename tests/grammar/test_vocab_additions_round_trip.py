"""Round-trip coverage for newly-registered vocabulary tokens.

Each token below was added to close a real DD/compose vocab gap; assert the
canonical name that uses it round-trips through the public parser/composer.

* ``photon_energy`` (physical_base) + ``lower_bound`` (qualifier, the sibling of
  the pre-existing ``upper_bound``) — spectrometer photon-energy bin edges.
  Bounds render as a LEADING qualifier (``lower_bound_<base>``), mirroring
  ``upper_bound_<base>``.
* ``polarimeter_beam`` (entity locus, ``_of_``) — the probing beam of a
  polarimeter diagnostic, e.g. ``vacuum_wavelength_of_polarimeter_beam``.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)

ROUND_TRIP = [
    "photon_energy",
    "lower_bound_photon_energy",
    "upper_bound_photon_energy",
    "vacuum_wavelength_of_polarimeter_beam",
]


@pytest.mark.parametrize("name", ROUND_TRIP)
def test_new_vocab_round_trips(name: str) -> None:
    assert compose_standard_name(parse_standard_name(name)) == name


def test_lower_bound_renders_as_leading_qualifier() -> None:
    """``lower_bound`` is a prefix qualifier like ``upper_bound`` — the trailing
    ``<base>_lower_bound`` form is NOT canonical and must not round-trip."""
    with pytest.raises(ValueError):
        parse_standard_name("photon_energy_lower_bound")
