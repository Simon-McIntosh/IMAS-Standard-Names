"""Round-trip smoke coverage for the grammar-stabilisation vocabulary additions.

Each token below closes a real full-DD compose gap. Assert that a
representative canonical name using it round-trips through the public
model-layer composer (``compose_standard_name(parse_standard_name(name)) == name``).

* physical_bases: ``magnetic_vector_potential`` (a_field), ``larmor_radius``
  (enables ``normalized_larmor_radius`` = rho*), ``vibrational_level``,
  ``probability``, ``parity``, ``efficiency``, ``peaking_factor``,
  ``field_current_coupling_coefficient`` (em_coupling), ``roughness``,
  ``fluence``, ``tritium_breeding_ratio``, ``fusion_gain``, ``charge_number``
  (enables ``square_of_ion_charge_number`` = z_ion_square).
* subjects (injected gas species): ``ethane``, ``propane``, ``ethylene``,
  ``methane``, ``ammonia_deuterated``, ``methane_carbon_13``,
  ``deuterated_methane``.
* qualifiers: ``incident`` (wall power/flux), ``forward`` (antenna power),
  ``wetted`` (divertor wetted_area), ``spun`` / ``twist`` (FOCS fibre period).
* locus: ``sawtooth_mixing_radius`` (companion to sawtooth_inversion_radius).
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)

_NEW_BASES = [
    "magnetic_vector_potential",
    "larmor_radius",
    "electron_larmor_radius",
    "normalized_larmor_radius",
    "vibrational_level",
    "probability",
    "parity",
    "efficiency",
    "efficiency_of_bolometer",
    "peaking_factor",
    "field_current_coupling_coefficient",
    "roughness",
    "fluence",
    "tritium_breeding_ratio",
    "fusion_gain",
    "charge_number",
    "ion_charge_number",
    "square_of_ion_charge_number",
]

_NEW_SUBJECTS = [
    "ethane_density",
    "propane_density",
    "ethylene_density",
    "methane_density",
    "ammonia_deuterated_density",
    "methane_carbon_13_density",
    "deuterated_methane_density",
]

_NEW_QUALIFIERS = [
    "incident_power",
    "forward_power",
    "wetted_area",
    "spun_period",
    "twist_period",
]

_NEW_LOCI = [
    "pressure_at_sawtooth_mixing_radius",
    "radius_of_sawtooth_mixing_radius",
]

_ALL_NEW = _NEW_BASES + _NEW_SUBJECTS + _NEW_QUALIFIERS + _NEW_LOCI


@pytest.mark.parametrize("name", _ALL_NEW)
def test_grammar_stabilisation_vocab_round_trips(name: str) -> None:
    assert compose_standard_name(parse_standard_name(name)) == name


def test_only_one_methane_deuterated_canonical_spelling() -> None:
    """Canonicalisation guard: deuterated_methane is the single registered
    isotopologue spelling; methane_deuterated must NOT be a subject token."""
    from imas_standard_names.grammar.model_types import Subject

    values = {s.value for s in Subject}
    assert "deuterated_methane" in values
    assert "methane_deuterated" not in values
