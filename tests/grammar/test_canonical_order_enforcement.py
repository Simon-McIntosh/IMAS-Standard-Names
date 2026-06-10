"""Canonical token-order enforcement: non-canonical spellings are ungrammatical.

The grammar locks modifier ordering the way English locks adjective order
("big red rusty old tractor"): each name has exactly ONE grammatical spelling.

Rule 1 — strict canonical-form parsing: ``parse_standard_name`` raises
:class:`NonCanonicalNameError` (carrying ``canonical_form``) when the tokens
parse but sit in non-canonical order, instead of silently reordering on
compose. The IR-level ``parse()`` stays lenient for diagnostics.

Rule 2 — population form is canonical with a species subject: when a species
subject is present and the lexical base's leading token is also a
population/orbit/aggregation token (``thermal_pressure``, ``thermal_energy``),
the subject + lexical-base spelling is rejected with an error directing to the
population form. The lexical-base spelling remains canonical only in
species-aggregated names.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import (
    NonCanonicalNameError,
    compose_standard_name,
    parse_standard_name,
)
from imas_standard_names.grammar.model import StandardName

# ---------------------------------------------------------------------------
# Rule 1: non-canonical prefix order raises with the canonical form attached
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "canonical"),
    [
        # orbit and population swapped (canonical: <orbit>_<population>)
        ("fast_trapped_ion_density", "trapped_fast_ion_density"),
        # subject before population (canonical: <population>_<subject>)
        ("ion_fast_pressure", "fast_ion_pressure"),
    ],
)
def test_non_canonical_order_rejected_with_canonical_form(name, canonical):
    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name(name)
    exc = excinfo.value
    assert exc.canonical_form == canonical
    assert exc.name == name
    assert canonical in str(exc)
    assert isinstance(exc, ValueError)  # downstream except-clauses keep working
    # The canonical form itself is grammatical and stable.
    assert compose_standard_name(parse_standard_name(canonical)) == canonical


# ---------------------------------------------------------------------------
# Rule 2: population form canonical when a species subject is present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "population_form"),
    [
        ("electron_thermal_pressure", "thermal_electron_pressure"),
        ("ion_thermal_pressure", "thermal_ion_pressure"),
        ("electron_thermal_energy", "thermal_electron_energy"),
    ],
)
def test_subject_plus_lexical_modifier_base_rejected(name, population_form):
    with pytest.raises(ValueError, match=population_form):
        parse_standard_name(name)
    # Direct construction of the dispreferred spelling is equally
    # ungrammatical (the rule lives on the model, not just the parser).
    parsed = population_form.split("_")
    with pytest.raises(ValueError, match=population_form):
        StandardName(
            subject=parsed[1],
            physical_base=f"{parsed[0]}_{'_'.join(parsed[2:])}",
        )


def test_population_form_is_grammatical():
    for name in (
        "thermal_electron_pressure",
        "thermal_ion_pressure",
        "thermal_electron_energy",
    ):
        assert compose_standard_name(parse_standard_name(name)) == name


# ---------------------------------------------------------------------------
# Canonical round-trips unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "trapped_fast_ion_density",
        "thermal_electron_pressure",
        "thermal_pressure",
        "plasma_thermal_pressure",
        "total_plasma_thermal_pressure",
        "total_trapped_fast_ion_energy",
        "safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95",
    ],
)
def test_canonical_names_round_trip(name):
    assert compose_standard_name(parse_standard_name(name)) == name


def test_lexical_base_collision_guard_still_active():
    with pytest.raises(ValueError, match="thermal_pressure"):
        StandardName(population="thermal", physical_base="pressure")
