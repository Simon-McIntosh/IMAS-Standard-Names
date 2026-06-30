"""Channel-qualifier segment: a qualifier that binds to the transport CHANNEL.

The ``channel_qualifier`` segment (kinetic, plasma, diamagnetic) names a
qualifier that binds to the transport CHANNEL rather than the base. It renders
immediately OUTER of the channel (before it) and INNER of the zone:
``<subject>_<device>_<zone...>_<channel_qualifier>_<channel>_<qualifier...>_<base>``.

It is SINGLE-token (a name carries at most one channel-qualifier). Two
channel-qualifier tokens in one name is a hard error.

This is distinct from the BASE-binding qualifiers (qualifiers.yml), which bind
to the base and render INNER of the channel.

Dual-coexistence: ``kinetic`` is a channel-qualifier AND ``kinetic_energy`` /
``internal_energy`` are atomic bases (Class 4). The parser's longest-base match
disambiguates: ``electron_kinetic_energy`` parses as ``base=kinetic_energy``,
while ``ion_kinetic_energy_flux`` strips ``channel_qualifier=kinetic`` +
``channel=energy`` + ``base=flux``.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name
from imas_standard_names.grammar.model import StandardName

# ---------------------------------------------------------------------------
# Channel-qualifier names parse -> compose round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "channel_qualifier", "channel", "subject", "base"),
    [
        ("kinetic_energy_flux", "kinetic", "energy", None, "flux"),
        ("plasma_momentum_flux", "plasma", "momentum", None, "flux"),
        ("ion_kinetic_energy_flux", "kinetic", "energy", "ion", "flux"),
        (
            "diamagnetic_momentum_diffusivity",
            "diamagnetic",
            "momentum",
            None,
            "diffusivity",
        ),
    ],
)
def test_channel_qualifier_round_trip(
    name: str,
    channel_qualifier: str,
    channel: str,
    subject: str | None,
    base: str,
) -> None:
    model = parse_standard_name(name)
    assert model.channel_qualifier is not None
    assert model.channel_qualifier.value == channel_qualifier
    assert model.channel is not None
    assert model.channel.value == channel
    assert (model.subject.value if model.subject else None) == subject
    assert model.physical_base == base
    assert compose_standard_name(model) == name


def test_channel_qualifier_renders_outer_of_channel() -> None:
    """The channel-qualifier renders immediately before the channel word."""
    model = parse_standard_name("ion_kinetic_energy_flux")
    assert model.subject is not None and model.subject.value == "ion"
    assert model.channel_qualifier is not None
    assert model.channel_qualifier.value == "kinetic"
    assert model.channel is not None and model.channel.value == "energy"
    assert model.physical_base == "flux"


# ---------------------------------------------------------------------------
# Dual-coexistence: kinetic_energy is an atomic BASE; kinetic is a qualifier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "kinetic_energy",
        "internal_energy",
        "electron_kinetic_energy",
        "runaway_electron_kinetic_energy",
    ],
)
def test_kinetic_energy_standalone_parses_as_base(name: str) -> None:
    model = parse_standard_name(name)
    # The channel-qualifier slot is empty: kinetic_energy is the (compound) base.
    assert model.channel_qualifier is None
    assert model.channel is None
    assert compose_standard_name(model) == name


def test_kinetic_energy_density_round_trips() -> None:
    # energy_density decomposes channel=energy + base=density, so the kinetic
    # here is the channel-qualifier (not part of a kinetic_energy base). It
    # still round-trips canonically.
    name = "ion_kinetic_energy_density"
    model = parse_standard_name(name)
    assert model.channel_qualifier is not None
    assert model.channel_qualifier.value == "kinetic"
    assert compose_standard_name(model) == name


def test_kinetic_energy_flux_is_canonical() -> None:
    """kinetic_energy_flux must stay kinetic_energy_flux (NOT energy_kinetic_flux)."""
    model = parse_standard_name("kinetic_energy_flux")
    assert model.compose() == "kinetic_energy_flux"


def test_plasma_momentum_flux_is_canonical() -> None:
    model = parse_standard_name("plasma_momentum_flux")
    assert model.compose() == "plasma_momentum_flux"


# ---------------------------------------------------------------------------
# diamagnetic dual-binding: base-bound legacy forms still round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "diamagnetic_velocity_due_to_diamagnetic_drift",
        "diamagnetic_current_density",
        "diamagnetic_momentum_diffusivity",
        "diamagnetic_momentum_convection_velocity",
    ],
)
def test_diamagnetic_families_round_trip(name: str) -> None:
    model = parse_standard_name(name)
    assert compose_standard_name(model) == name


# ---------------------------------------------------------------------------
# Single-token: two channel-qualifier tokens in one name is a hard error
# ---------------------------------------------------------------------------


def test_two_channel_qualifier_tokens_rejected() -> None:
    # kinetic_plasma_energy_flux would imply channel_qualifier=kinetic AND
    # channel_qualifier=plasma — a name carries at most one channel-qualifier.
    with pytest.raises(ValueError, match="channel_qualifier"):
        parse_standard_name("kinetic_plasma_energy_flux")


def test_single_channel_qualifier_model_round_trips() -> None:
    model = StandardName(
        physical_base="flux", channel="energy", channel_qualifier="kinetic"
    )
    assert compose_standard_name(model) == "kinetic_energy_flux"
