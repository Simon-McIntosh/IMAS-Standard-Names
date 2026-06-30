"""Canonical token-order enforcement: non-canonical spellings are ungrammatical.

The grammar locks modifier ordering the way English locks adjective order
("big red rusty old tractor"): each name has exactly ONE grammatical spelling.

Strict canonical-form parsing: ``parse_standard_name`` raises
:class:`NonCanonicalNameError` (carrying ``canonical_form``) when the tokens
parse but sit in non-canonical order, instead of silently reordering on
compose. The IR-level ``parse()`` stays lenient for diagnostics.

Energy-state modifiers live ONLY in the population segment (no lexical
thermal_pressure/thermal_energy bases), so the single canonical-order rule
covers them too: electron_thermal_pressure → canonical
thermal_electron_pressure; plasma_thermal_pressure → thermal_plasma_pressure.
Component/coordinate is the first (outermost) prefix segment.
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
# Subject stacking is a hard error; canonical_form is NEVER lossy
# ---------------------------------------------------------------------------


def test_two_subject_tokens_rejected_without_canonical_form():
    # Two species subjects must raise the C1-style stacking error naming both
    # tokens — never a NonCanonicalNameError offering the lossy render
    # ('deuterium_density' silently dropping electron) that downstream
    # pipelines would auto-adopt.
    with pytest.raises(
        ValueError, match=r"Two 'subject' tokens \('electron' and 'deuterium'\)"
    ) as excinfo:
        parse_standard_name("electron_deuterium_density")
    assert not hasattr(excinfo.value, "canonical_form")


@pytest.mark.parametrize(
    "name",
    [
        # Atomic multi-word subject tokens are SINGLE enum tokens: unaffected.
        # (was deuterium_tritium_fusion_power_density — 'fusion' moved to the
        # process segment, so that name now migrates to a due_to_ form.)
        "deuterium_tritium_density",
        "runaway_electron_density",
    ],
)
def test_atomic_multiword_subjects_unaffected(name):
    assert compose_standard_name(parse_standard_name(name)) == name


def test_ratio_to_template_behaviour_pinned():
    # tritium_to_deuterium_density_ratio does not parse today (the to_
    # connector blocks base resolution); pin that it raises the unknown-base
    # error and NOT a subject-stacking error.
    from imas_standard_names.grammar import UnknownBaseTokenError

    with pytest.raises(UnknownBaseTokenError):
        parse_standard_name("tritium_to_deuterium_density_ratio")


def test_lossy_canonical_never_offered():
    # Device tokens still project last-wins (out of C1 scope): the canonical
    # render of flux_loop_mse_voltage drops flux_loop. The lossless guard must
    # surface a distinct error WITHOUT canonical_form instead of offering the
    # lossy rename.
    with pytest.raises(ValueError, match=r"projection lost token\(s\)") as excinfo:
        parse_standard_name("flux_loop_mse_voltage")
    assert not isinstance(excinfo.value, NonCanonicalNameError)
    assert not hasattr(excinfo.value, "canonical_form")


def test_lossless_guard_unit():
    from imas_standard_names.grammar.model import _assert_lossless_canonical

    # Pure reorder: identical token multisets — guard passes silently.
    _assert_lossless_canonical("fast_trapped_ion_density", "trapped_fast_ion_density")
    # Lost tokens: raises without canonical_form.
    with pytest.raises(ValueError, match="lost token"):
        _assert_lossless_canonical("electron_deuterium_density", "deuterium_density")
    # Gained tokens (synthetic): also refused.
    with pytest.raises(ValueError, match="gained token"):
        _assert_lossless_canonical("ion_density", "thermal_ion_density")


# ---------------------------------------------------------------------------
# Energy-state modifiers after a qualifier/subject are non-canonical
# (no lexical thermal bases — rule 1 does all the work)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "canonical"),
    [
        ("electron_thermal_pressure", "thermal_electron_pressure"),
        ("ion_thermal_pressure", "thermal_ion_pressure"),
        ("electron_thermal_energy", "thermal_electron_energy"),
        ("plasma_thermal_pressure", "thermal_plasma_pressure"),
        ("total_plasma_thermal_pressure", "total_thermal_plasma_pressure"),
    ],
)
def test_modifier_after_qualifier_rejected_with_canonical(name, canonical):
    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name(name)
    assert excinfo.value.canonical_form == canonical


def test_population_form_is_grammatical():
    for name in (
        "thermal_electron_pressure",
        "thermal_ion_pressure",
        "thermal_electron_energy",
    ):
        assert compose_standard_name(parse_standard_name(name)) == name


# ---------------------------------------------------------------------------
# Component/coordinate is the FIRST (outermost) prefix segment
# ---------------------------------------------------------------------------


def test_component_first_locked():
    canonical = "radial_total_ion_energy_diffusivity"
    assert compose_standard_name(parse_standard_name(canonical)) == canonical
    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name("total_radial_ion_energy_diffusivity")
    assert excinfo.value.canonical_form == canonical


# ---------------------------------------------------------------------------
# Canonical round-trips unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "trapped_fast_ion_density",
        "thermal_electron_pressure",
        "thermal_pressure",
        "thermal_plasma_pressure",
        "total_thermal_plasma_pressure",
        "total_trapped_fast_ion_energy",
        "safety_factor_at_normalized_poloidal_magnetic_flux_equal_to_0_95",
    ],
)
def test_canonical_names_round_trip(name):
    assert compose_standard_name(parse_standard_name(name)) == name


def test_population_qualifies_generic_base():
    # population=thermal is sufficient qualification for the generic base
    # 'pressure' (M1), and the construction composes to the canonical string.
    model = StandardName(population="thermal", physical_base="pressure")
    assert model.compose() == "thermal_pressure"
