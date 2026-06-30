"""Channel segment: transport-channel prefix (what is transported).

The ``channel`` segment (heat, particle, energy, momentum) names WHAT is
transported. It is a STRUCTURAL role, not a generic qualifier: it is the
INNERMOST prefix segment, rendering immediately before the base and AFTER any
residual qualifier(s):
``<aggregation>_<orbit>_<population>_<subject>_<device>_<zone...>_<qualifier...>_<channel>_<base>``.

It is SINGLE-token (a name carries at most one transport channel). Two channel
tokens in one name is a hard error.

Dual role: ``energy`` and ``momentum`` are ALSO physical_bases
(``kinetic_energy``, ``internal_energy``, ``angular_momentum``, standalone
``electron_energy``). The parser matches the longest base first, so a standalone
``energy``/``momentum`` parses as the base while ``energy_flux`` /
``momentum_diffusivity`` strip the channel + base.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name
from imas_standard_names.grammar.model import StandardName

# ---------------------------------------------------------------------------
# Channel names parse → compose round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "channel", "subject", "base"),
    [
        ("heat_flux", "heat", None, "flux"),
        ("energy_flux", "energy", None, "flux"),
        ("momentum_flux", "momentum", None, "flux"),
        ("particle_flux", "particle", None, "flux"),
        ("electron_energy_flux", "energy", "electron", "flux"),
        ("electron_heat_flux", "heat", "electron", "flux"),
        ("momentum_diffusivity", "momentum", None, "diffusivity"),
        ("heat_diffusivity", "heat", None, "diffusivity"),
        ("momentum_source", "momentum", None, "source"),
        ("ion_particle_flux", "particle", "ion", "flux"),
    ],
)
def test_channel_round_trip(
    name: str, channel: str, subject: str | None, base: str
) -> None:
    model = parse_standard_name(name)
    assert model.channel is not None
    assert model.channel.value == channel
    assert (model.subject.value if model.subject else None) == subject
    assert model.physical_base == base
    assert compose_standard_name(model) == name


def test_channel_renders_innermost_before_base() -> None:
    """The channel renders immediately before the base, after the subject."""
    model = parse_standard_name("electron_energy_flux")
    assert model.subject is not None and model.subject.value == "electron"
    assert model.channel is not None and model.channel.value == "energy"
    assert model.physical_base == "flux"


# ---------------------------------------------------------------------------
# energy / momentum dual role: standalone parses as a BASE, not a channel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "electron_energy",
        "kinetic_energy",
        "internal_energy",
        "angular_momentum",
    ],
)
def test_energy_momentum_standalone_parses_as_base(name: str) -> None:
    model = parse_standard_name(name)
    # The channel slot is empty: energy/momentum here are the (compound) base.
    assert model.channel is None
    assert compose_standard_name(model) == name


def test_electron_energy_is_subject_plus_base_not_channel() -> None:
    model = parse_standard_name("electron_energy")
    assert model.subject is not None and model.subject.value == "electron"
    assert model.channel is None
    assert model.physical_base == "energy"


# ---------------------------------------------------------------------------
# Single-token: two channel tokens in one name is a hard error
# ---------------------------------------------------------------------------


def test_two_channel_tokens_rejected() -> None:
    # heat_energy_flux would imply channel=heat AND channel=energy — a name
    # carries at most one transport channel.
    with pytest.raises(ValueError, match="channel"):
        parse_standard_name("heat_energy_flux")


def test_single_channel_model_round_trips() -> None:
    model = StandardName(physical_base="flux", channel="heat")
    assert compose_standard_name(model) == "heat_flux"
