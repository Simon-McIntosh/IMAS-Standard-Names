"""Energy-state modifiers live ONLY in the population segment.

``thermal_pressure`` is population=thermal + base=pressure — there is no
lexical thermal_pressure/thermal_energy base (the rc34 lexicalisation was
reverted: hiding ``thermal`` inside a base token let it render AFTER the
plasma qualifier, violating the locked adjective order). Canonical compounds
order modifier-first: ``thermal_plasma_pressure``,
``total_thermal_plasma_pressure`` (= total(thermal(plasma_pressure))),
``thermal_electron_pressure``. Strict canonical-form parsing
(:class:`NonCanonicalNameError`) does all the enforcement work.

``fast_wave`` / ``slow_wave`` are ICRF wave-branch lexical QUALIFIER tokens:
``fast_wave_power`` folds to base=fast_wave_power with NO population —
"fast wave" is the fast magnetosonic wave, not a fast particle population.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import (
    NonCanonicalNameError,
    compose_standard_name,
    parse_standard_name,
)


def _v(seg):
    return seg.value if seg is not None else None


# ---------------------------------------------------------------------------
# Population decomposition: canonical thermal names round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "aggregation", "population", "subject", "base"),
    [
        ("thermal_pressure", None, "thermal", None, "pressure"),
        ("thermal_energy", None, "thermal", None, "energy"),
        # plasma is a channel-qualifier (channel_qualifiers.yml): it peels into
        # the channel_qualifier segment, leaving pressure as the base.
        ("thermal_plasma_pressure", None, "thermal", None, "pressure"),
        ("total_thermal_plasma_pressure", "total", "thermal", None, "pressure"),
        ("thermal_electron_pressure", None, "thermal", "electron", "pressure"),
        ("thermal_ion_pressure", None, "thermal", "ion", "pressure"),
        ("fast_ion_pressure", None, "fast", "ion", "pressure"),
    ],
)
def test_population_decomposition_round_trips(
    name, aggregation, population, subject, base
):
    model = parse_standard_name(name)
    assert _v(model.aggregation) == aggregation, f"{name!r}: aggregation"
    assert _v(model.population) == population, f"{name!r}: population"
    assert _v(model.subject) == subject, f"{name!r}: subject"
    assert model.physical_base == base, f"{name!r}: base"
    assert compose_standard_name(model) == name


# ---------------------------------------------------------------------------
# Non-canonical spellings reject with the canonical form attached
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "canonical"),
    [
        ("plasma_thermal_pressure", "thermal_plasma_pressure"),
        ("total_plasma_thermal_pressure", "total_thermal_plasma_pressure"),
        ("electron_thermal_pressure", "thermal_electron_pressure"),
        ("ion_thermal_pressure", "thermal_ion_pressure"),
        ("electron_thermal_energy", "thermal_electron_energy"),
    ],
)
def test_modifier_after_qualifier_or_subject_rejected(name, canonical):
    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name(name)
    assert excinfo.value.canonical_form == canonical


def test_no_lexical_thermal_bases():
    from imas_standard_names.grammar.constants import SEGMENT_TOKEN_MAP

    bases = set(SEGMENT_TOKEN_MAP["physical_base"])
    assert "thermal_pressure" not in bases
    assert "thermal_energy" not in bases


# ---------------------------------------------------------------------------
# fast_wave family: lexical wave-branch qualifier, not a fast population
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "base"),
    [
        ("fast_wave_power", "fast_wave_power"),
        ("slow_wave_power", "slow_wave_power"),
    ],
)
def test_wave_branch_names_fold_without_population(name, base):
    model = parse_standard_name(name)
    assert model.population is None, (
        f"{name!r}: '{name.split('_')[0]}' is a wave branch, not a population"
    )
    assert model.physical_base == base
    assert compose_standard_name(model) == name


def test_fast_population_reading_untouched():
    model = parse_standard_name("fast_ion_energy")
    assert _v(model.population) == "fast"
    assert _v(model.subject) == "ion"
    assert model.physical_base == "energy"
