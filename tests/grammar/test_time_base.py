"""The ``time`` base is reserved for the time coordinate / elapsed time.

A named characteristic timescale is its own atomic ``physical_base``
(``confinement_time``, ``resistive_diffusion_time``, ``exposure_time``,
``rise_time``, ``fall_time`` …) — the same token-by-token treatment as the
other lexicalised quantities (``surface_area``, ``vector_potential``).

The bare ``time`` base MUST NOT carry a ``due_to_<process>``:
``time_due_to_resistive_diffusion`` is ambiguous ("time" — delay? constant?
diffusion time?). The canonical form is the lexicalised timescale base
``resistive_diffusion_time``.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name


def test_bare_time_plus_process_rejected() -> None:
    # base=time + due_to_<process> is ungrammatical — use the timescale base.
    with pytest.raises(ValueError):
        parse_standard_name("time_due_to_resistive_diffusion")


@pytest.mark.parametrize(
    "name",
    [
        "resistive_diffusion_time",
        "exposure_time",
        "rise_time",
        "fall_time",
    ],
)
def test_timescale_bases_round_trip(name: str) -> None:
    model = parse_standard_name(name)
    assert model.physical_base == name
    assert compose_standard_name(model) == name


def test_bare_time_without_process_still_valid() -> None:
    # the time coordinate / elapsed time (no due_to process) stays valid.
    model = parse_standard_name("normalized_time")
    assert model.physical_base == "time"
    assert compose_standard_name(model) == "normalized_time"
