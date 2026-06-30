"""Tests for vocabulary extensions (Phases 2A-2D).

Validates parse + compose round-trip for new component, subject, and process tokens.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import (
    StandardName,
    compose_name,
    parse_name,
)


class TestPerpendicular:
    """Phase 2A: perpendicular component token."""

    def test_compose_perpendicular_component(self):
        parts = {"component": "perpendicular", "physical_base": "magnetic_field"}
        name = compose_name(parts)
        assert name == "perpendicular_magnetic_field"

    def test_parse_perpendicular_component(self):
        parsed = parse_name("perpendicular_magnetic_field")
        assert parsed.component.value == "perpendicular"
        assert parsed.physical_base == "magnetic_field"

    def test_perpendicular_round_trip(self):
        # heat_flux decomposes as channel=heat + base=flux (see channels.yml).
        model = StandardName(
            component="perpendicular", channel="heat", physical_base="flux"
        )
        name = model.compose()
        assert name == "perpendicular_heat_flux"
        parsed = parse_name(name)
        assert parsed.component.value == "perpendicular"
        assert parsed.channel.value == "heat"
        assert parsed.physical_base == "flux"


class TestSubjectTokens:
    """Phase 2C: New subject tokens (Tiers 1-3)."""

    @pytest.mark.parametrize(
        "subject",
        [
            # Tier 1: Core fusion species
            "hydrogen",
            "alpha_particle",
            "helium_3",
            "helium_4",
            # Tier 2: Impurity elements
            "carbon",
            "nitrogen",
            "neon",
            "argon",
            "boron",
            "beryllium",
            "tungsten",
            "iron",
            "lithium",
            "oxygen",
            # Tier 3: Extended species
            "krypton",
            "xenon",
            "deuterium_tritium",
            "deuterium_deuterium",
            "tritium_tritium",
            "hydrogenic",
            "neutral_beam",
            "impurity_ion",
        ],
    )
    def test_subject_round_trip(self, subject):
        # NOTE: fast_neutral/fast_electron decomposed into population+species
        # (rc32) — see test_population_segment.py.
        """Each subject token should compose and parse correctly."""
        parts = {"subject": subject, "physical_base": "temperature"}
        name = compose_name(parts)
        assert name == f"{subject}_temperature"
        parsed = parse_name(name)
        assert parsed.subject.value == subject
        assert parsed.physical_base == "temperature"

    def test_alpha_particle_density(self):
        parsed = parse_name("alpha_particle_density")
        assert parsed.subject.value == "alpha_particle"
        assert parsed.physical_base == "density"

    def test_tungsten_density_with_position(self):
        name = "tungsten_density_at_magnetic_axis"
        parsed = parse_name(name)
        assert parsed.subject.value == "tungsten"
        assert parsed.physical_base == "density"
        assert parsed.position.value == "magnetic_axis"

    def test_deuterium_tritium_pressure(self):
        parsed = parse_name("deuterium_tritium_pressure")
        assert parsed.subject.value == "deuterium_tritium"
        assert parsed.physical_base == "pressure"


class TestProcessTokens:
    """Phase 2D: New process tokens."""

    @pytest.mark.parametrize(
        "process",
        [
            "non_inductive",
            "gas_injection",
            "pellet_injection",
            "beam_beam_fusion",
            "beam_thermal_fusion",
            "ion_cyclotron_current_drive",
        ],
    )
    def test_process_round_trip(self, process):
        """Each process token should compose and parse correctly."""
        parts = {"physical_base": "power", "process": process}
        name = compose_name(parts)
        assert name == f"power_due_to_{process}"
        parsed = parse_name(name)
        assert parsed.process.value == process
        assert parsed.physical_base == "power"

    def test_non_inductive_current(self):
        parsed = parse_name("plasma_current_due_to_non_inductive")
        assert parsed.process.value == "non_inductive"
        assert parsed.physical_base == "plasma_current"

    def test_gas_injection_with_subject(self):
        # particle_flux decomposes as channel=particle + base=flux.
        name = "deuterium_particle_flux_due_to_gas_injection"
        parsed = parse_name(name)
        assert parsed.subject.value == "deuterium"
        assert parsed.channel.value == "particle"
        assert parsed.physical_base == "flux"
        assert parsed.process.value == "gas_injection"


class TestRecyclingProcess:
    """recycling process token (codex R4 VocabGap: divertor recycling)."""

    def test_particle_flux_due_to_recycling_round_trips(self):
        # particle_flux decomposes as channel=particle + base=flux.
        name = "particle_flux_due_to_recycling"
        parsed = parse_name(name)
        assert parsed.process.value == "recycling"
        assert parsed.channel.value == "particle"
        assert parsed.physical_base == "flux"
        assert compose_name(parsed) == name
