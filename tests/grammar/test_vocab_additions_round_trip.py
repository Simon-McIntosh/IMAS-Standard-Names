"""Round-trip coverage for newly-registered vocabulary tokens.

Each token below was added to close a real DD/compose vocab gap; assert the
canonical name that uses it round-trips through the public parser/composer.

* ``photon_energy`` (physical_base) + ``lower_bound`` (qualifier, the sibling of
  the pre-existing ``upper_bound``) — spectrometer photon-energy bin edges.
  Bounds render as a LEADING qualifier (``lower_bound_<base>``), mirroring
  ``upper_bound_<base>``.
* ``polarimeter_beam`` (entity locus, ``_of_``) — the probing beam of a
  polarimeter diagnostic, e.g. ``vacuum_wavelength_of_polarimeter_beam``.
* Radiation / fast-particle-loss mechanisms (process, ``_due_to_``):
  ``avalanche``, ``first_orbit_loss``, ``line_radiation``,
  ``synchrotron_radiation``.
* Wave-diagnostic / MSE / numerical-split / PFC-face qualifiers (prefix):
  ``faraday``, ``ordinary_mode``, ``extraordinary_mode``, ``motional_stark``,
  ``straight_field_line``, ``reynolds``, ``implicit``, ``explicit``,
  ``back_surface``, ``front_surface``.
* Radiometric / atomic / MHD / diagnostic bases (physical_base):
  ``radiance``, ``brightness``, ``instrument_function``,
  ``rotational_transform``, ``psi_star``, ``ionisation_potential``.
* Coil-conductor and diagnostic-optic entity loci (``_of_``):
  ``conductor``, ``coil_conductor``, ``coil_conductor_element``,
  ``conductor_cross_section``, ``aperture``, ``filter_window``,
  ``fibre_bundle``.
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
    # Radiation / fast-particle-loss mechanisms (process, _due_to_)
    "current_density_due_to_avalanche",
    "particle_flux_due_to_first_orbit_loss",
    "power_due_to_line_radiation",
    "power_due_to_synchrotron_radiation",
    # Wave-diagnostic / MSE / numerical-split / PFC-face qualifiers (prefix)
    "faraday_angle",
    "ordinary_mode_temperature",
    "extraordinary_mode_temperature",
    "motional_stark_angle",
    "straight_field_line_angle",
    "reynolds_pressure",
    "implicit_source",
    "explicit_source",
    "back_surface_temperature",
    "front_surface_temperature",
    # Radiometric / atomic / MHD / diagnostic bases (physical_base)
    "radiance",
    "brightness",
    "instrument_function",
    "rotational_transform",
    "psi_star",
    "ionisation_potential",
    # Coil-conductor and diagnostic-optic entity loci (_of_)
    "current_of_conductor",
    "current_of_coil_conductor",
    "position_of_coil_conductor_element",
    "area_of_conductor_cross_section",
    "radius_of_aperture",
    "curvature_of_filter_window",
    "width_of_fibre_bundle",
]


@pytest.mark.parametrize("name", ROUND_TRIP)
def test_new_vocab_round_trips(name: str) -> None:
    assert compose_standard_name(parse_standard_name(name)) == name


def test_lower_bound_renders_as_leading_qualifier() -> None:
    """``lower_bound`` is a prefix qualifier like ``upper_bound`` — the trailing
    ``<base>_lower_bound`` form is NOT canonical and must not round-trip."""
    with pytest.raises(ValueError):
        parse_standard_name("photon_energy_lower_bound")
