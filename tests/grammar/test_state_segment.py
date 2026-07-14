"""The `state` grammar segment: charge_state (ions) / internal_state (neutrals).

State resolution — a quantity resolved for a specific state of a species
rather than the species aggregate — is a single-token subject-refinement
segment rendered immediately after the subject:
``<population>_<subject>_<state>_<channel>_<base>``. It replaces the fused
``ion_state`` / ``ion_charge_state`` / ``neutral_state`` compound subjects.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)

ROUND_TRIP = [
    "ion_charge_state_density",
    "neutral_internal_state_density",
    "fast_ion_charge_state_pressure",
    "total_ion_charge_state_density",
    "parallel_neutral_internal_state_momentum_flux",
]


@pytest.mark.parametrize("name", ROUND_TRIP)
def test_state_names_round_trip(name: str) -> None:
    parsed = parse_standard_name(name)
    assert compose_standard_name(parsed) == name


def test_state_segment_populated() -> None:
    # Neutral internal_state has no fused-subject competitor, so it decomposes
    # via the state segment even before the fused ion_state/ion_charge_state/
    # neutral_state subject tokens are deleted (that deletion — which makes the
    # segment the canonical parse for ION names too — is the fused-token-surgery
    # task; see test_fused_subject_tokens_removed there).
    p = parse_standard_name("neutral_internal_state_density")
    assert p.subject.value == "neutral"
    assert p.state.value == "internal_state"
    assert p.physical_base == "density"


def test_state_renders_after_subject() -> None:
    p = parse_standard_name("parallel_neutral_internal_state_momentum_flux")
    assert p.component.value == "parallel"
    assert p.subject.value == "neutral"
    assert p.state.value == "internal_state"


def test_state_field_composes_from_model() -> None:
    # Build directly from the model to prove compose emits state after subject
    # (independent of any fused-subject greedy-match).
    from imas_standard_names.grammar.model import StandardName

    name = compose_standard_name(
        StandardName(subject="neutral", state="internal_state", physical_base="density")
    )
    assert name == "neutral_internal_state_density"
