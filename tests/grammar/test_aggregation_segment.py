"""Aggregation segment + same-segment token-stacking rejection.

The ``aggregation`` segment (total, net) marks a population/species/contribution
reduction. It is an orthogonal dimension from ``population`` (energy-state) and
legitimately STACKS with it, rendering outermost:
``<aggregation>_<orbit>_<population>_<subject>_<base>``, e.g.
``total_trapped_fast_ion_energy``.

These tests also pin the no-silent-drop contract: a second token of the SAME
single-token segment (two aggregations, two populations, or two orbits) is a
hard error rather than a last-wins silent token drop.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name
from imas_standard_names.grammar.model import StandardName


def _v(seg):
    return seg.value if seg is not None else None


# ---------------------------------------------------------------------------
# Same-segment stacking is a hard error (no silent last-wins drop)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "segment"),
    [
        ("fast_thermal_ion_density", "population"),
        ("trapped_co_passing_ion_density", "orbit"),
    ],
)
def test_same_segment_stacking_rejected(name, segment):
    with pytest.raises(ValueError, match=segment):
        parse_standard_name(name)


def test_two_aggregations_rejected():
    # Constructed at the IR adapter layer: a name that peels two aggregation
    # tokens must raise rather than silently drop one.
    from imas_standard_names.grammar.ir import (
        BaseKind,
        Qualifier,
        QuantityOrCarrier,
        StandardNameIR,
    )
    from imas_standard_names.grammar.model import _ir_to_model_dict

    ir = StandardNameIR(
        base=QuantityOrCarrier(token="energy", kind=BaseKind.QUANTITY),
        qualifiers=[Qualifier(token="total"), Qualifier(token="net")],
    )
    with pytest.raises(ValueError, match="aggregation"):
        _ir_to_model_dict(ir)


# ---------------------------------------------------------------------------
# Catalog representability — the two names rc32 silently corrupted are now
# representable without losing a token (token order may canonicalise).
# ---------------------------------------------------------------------------


def test_total_thermal_plasma_pressure_canonical():
    # Energy-state modifiers live only in population: canonical order is
    # total(thermal(plasma_pressure)). The legacy catalog spelling
    # total_plasma_thermal_pressure is non-canonical and rejected with the
    # canonical form attached.
    from imas_standard_names.grammar import NonCanonicalNameError

    name = "total_thermal_plasma_pressure"
    model = parse_standard_name(name)
    assert _v(model.aggregation) == "total"
    assert _v(model.population) == "thermal"
    # plasma is a channel-qualifier (channel_qualifiers.yml): it peels into the
    # channel_qualifier segment, leaving pressure as the base. Round-trips.
    assert _v(model.channel_qualifier) == "plasma"
    assert model.physical_base == "pressure"
    assert compose_standard_name(model) == name

    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name("total_plasma_thermal_pressure")
    assert excinfo.value.canonical_form == name


def test_total_thermal_ion_species_density_round_trips():
    name = "total_thermal_ion_species_density"
    model = parse_standard_name(name)
    assert _v(model.aggregation) == "total"
    assert _v(model.population) == "thermal"
    assert _v(model.subject) == "ion_species"
    assert model.physical_base == "density"
    assert compose_standard_name(model) == name


# ---------------------------------------------------------------------------
# Round-trips: aggregation + population stack, and the net token
# ---------------------------------------------------------------------------


def test_total_fast_ion_energy_round_trips():
    name = "total_fast_ion_energy"
    model = parse_standard_name(name)
    assert _v(model.aggregation) == "total"
    assert _v(model.population) == "fast"
    assert _v(model.subject) == "ion"
    assert model.physical_base == "energy"
    assert compose_standard_name(model) == name


def test_net_token_round_trips():
    name = "net_ion_current"
    model = parse_standard_name(name)
    assert _v(model.aggregation) == "net"
    assert _v(model.subject) == "ion"
    assert model.physical_base == "current"
    assert compose_standard_name(model) == name


# ---------------------------------------------------------------------------
# Generic physical base qualification (M1): aggregation/population qualify a
# generic base; a bare generic base still fails.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["total_pressure", "fast_pressure", "total_current"])
def test_generic_base_qualified_by_modifier_segment(name):
    model = parse_standard_name(name)
    assert compose_standard_name(model) == name


@pytest.mark.parametrize("base", ["pressure", "current"])
def test_bare_generic_base_still_rejected(base):
    with pytest.raises(ValueError):
        StandardName(physical_base=base)


# ---------------------------------------------------------------------------
# Canonical render order: aggregation outermost
# ---------------------------------------------------------------------------


def test_canonical_render_order_aggregation_outermost():
    model = StandardName(
        aggregation="total",
        orbit="trapped",
        population="fast",
        subject="ion",
        physical_base="energy",
    )
    assert model.compose() == "total_trapped_fast_ion_energy"
