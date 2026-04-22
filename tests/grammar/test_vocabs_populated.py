"""Tests for populated vNext vocabularies (plan 38 W2a).

Asserts that the vocabulary files populated from rc20 corpus mining
have sufficient coverage, contain key entries, and have no cross-registry
duplicates.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.vocab_loaders import (
    load_coordinate_axes,
    load_geometry_carriers,
    load_locus_registry,
    load_operators,
    load_physical_bases,
    validate_no_cross_registry_duplicates,
)

# ---------------------------------------------------------------------------
# Cardinality checks
# ---------------------------------------------------------------------------


class TestRegistryCardinality:
    """Minimum entry counts for each populated registry."""

    def test_physical_bases_minimum_150(self):
        reg = load_physical_bases()
        assert len(reg.bases) >= 150, (
            f"Expected >= 150 physical bases, got {len(reg.bases)}"
        )

    def test_locus_registry_minimum_60(self):
        reg = load_locus_registry()
        assert len(reg.loci) >= 60, f"Expected >= 60 locus entries, got {len(reg.loci)}"

    def test_operators_minimum_30(self):
        reg = load_operators()
        assert len(reg.operators) >= 30, (
            f"Expected >= 30 operators, got {len(reg.operators)}"
        )

    def test_geometry_carriers_minimum_10(self):
        reg = load_geometry_carriers()
        assert len(reg.carriers) >= 10, (
            f"Expected >= 10 geometry carriers, got {len(reg.carriers)}"
        )

    def test_coordinate_axes_minimum_8(self):
        reg = load_coordinate_axes()
        assert len(reg.axes) >= 8, f"Expected >= 8 coordinate axes, got {len(reg.axes)}"


# ---------------------------------------------------------------------------
# Key entries from corpus top-50 physical bases
# ---------------------------------------------------------------------------


class TestPhysicalBasesCorpusCoverage:
    """Every top-50 physical_base from mining_report.md must be present."""

    @pytest.fixture()
    def bases(self):
        return load_physical_bases()

    @pytest.mark.parametrize(
        "token",
        [
            "current_density",
            "major_radius",
            "number_density",
            "magnetic_field",
            "momentum_flux",
            "temperature",
            "pressure",
            "particle_flux",
            "velocity",
            "energy_source",
            "effective_charge",
            "magnetic_flux",
            "flux_coordinate",
            "radiated_power_density",
            "radiated_power_inside_flux_surface",
            "angle",
            "momentum_convective_velocity",
            "momentum_flux_limiter",
            "center_of_mass_velocity",
            "current",
            "accumulated_gas_injection",
            "gas_injection_rate",
            "energy_flux",
            "momentum_diffusivity",
            "momentum_source",
            "prefill_gas_injection",
            "heating_power",
            "plasma_current",
            "density",
            "particle_radial_diffusivity",
            "convective_velocity",
            "larmor_radius",
            "scrape_off_layer_density_decay_length",
            "scrape_off_layer_heat_flux_decay_length",
            "scrape_off_layer_temperature_decay_length",
            "thermal_energy_pedestal",
            "stored_energy",
            "fusion_power_density",
            "neutron_emissivity",
            "particle_flux_from_wall",
            "power_flux_density",
            "lower_hybrid_electric_field",
            "temperature_peaking_factor",
            "energy_radial_diffusivity_on_ggd",
        ],
    )
    def test_top50_base_present(self, bases, token):
        assert token in bases.bases, (
            f"Corpus top-50 base '{token}' missing from physical_bases.yml"
        )


# ---------------------------------------------------------------------------
# Key entries in operators
# ---------------------------------------------------------------------------


class TestOperatorKeyEntries:
    """Operators surfaced by corpus and plan must be present."""

    @pytest.fixture()
    def ops(self):
        return load_operators()

    @pytest.mark.parametrize(
        "token",
        [
            "tendency",
            "derivative_with_respect_to",
            "reference_waveform",
            "gyroaveraged",
            "moment",
            "flux_surface_averaged",
            "line_integrated",
            "maximum",
            "minimum",
            "time_derivative",
            "time_average",
            "root_mean_square",
            "magnitude",
            "real_part",
            "imaginary_part",
            "accumulated",
            "normalized",
            "volume_averaged",
            "fourier_coefficient",
            "ratio",
            "product",
            "on_ggd",
            "waveform",
            "bessel_0",
            "bessel_1",
        ],
    )
    def test_key_operator_present(self, ops, token):
        assert token in ops.operators, (
            f"Key operator '{token}' missing from operators.yml"
        )


# ---------------------------------------------------------------------------
# Key entries in locus registry
# ---------------------------------------------------------------------------


class TestLocusRegistryKeyEntries:
    """Essential loci with correct types."""

    @pytest.fixture()
    def loci(self):
        return load_locus_registry()

    def test_plasma_boundary_entity(self, loci):
        # plasma_boundary reclassified to position in vNext (plan 38 §A5)
        assert "plasma_boundary" in loci.loci
        assert loci.loci["plasma_boundary"].type == "position"

    def test_magnetic_axis_position(self, loci):
        assert "magnetic_axis" in loci.loci
        assert loci.loci["magnetic_axis"].type == "position"

    def test_x_point_position(self, loci):
        assert "x_point" in loci.loci
        assert loci.loci["x_point"].type == "position"

    def test_separatrix_entity(self, loci):
        assert "separatrix" in loci.loci
        assert loci.loci["separatrix"].type == "entity"

    def test_flux_loop_entity(self, loci):
        assert "flux_loop" in loci.loci
        assert loci.loci["flux_loop"].type == "entity"

    def test_wall_present(self, loci):
        assert "wall" in loci.loci

    def test_ion_cyclotron_heating_antenna_entity(self, loci):
        assert "ion_cyclotron_heating_antenna" in loci.loci
        assert loci.loci["ion_cyclotron_heating_antenna"].type == "entity"

    def test_ferritic_element_centroid_position(self, loci):
        assert "ferritic_element_centroid" in loci.loci
        assert loci.loci["ferritic_element_centroid"].type == "position"

    def test_sawtooth_inversion_radius_position(self, loci):
        assert "sawtooth_inversion_radius" in loci.loci
        assert loci.loci["sawtooth_inversion_radius"].type == "position"


# ---------------------------------------------------------------------------
# Cross-registry: no duplicate token names
# ---------------------------------------------------------------------------


class TestCrossRegistryDuplicates:
    """No token may appear in more than one vNext registry."""

    def test_no_cross_registry_duplicates(self):
        validate_no_cross_registry_duplicates()


# ---------------------------------------------------------------------------
# Physical base kind validation
# ---------------------------------------------------------------------------


class TestPhysicalBaseKinds:
    """Physical bases must have valid kind values."""

    def test_all_bases_have_kind(self):
        reg = load_physical_bases()
        for name, base in reg.bases.items():
            assert base.kind in {"scalar", "vector", "tensor", "complex"}, (
                f"Base '{name}' has invalid kind: {base.kind}"
            )

    def test_magnetic_field_is_vector(self):
        reg = load_physical_bases()
        assert reg.bases["magnetic_field"].kind == "vector"

    def test_temperature_is_scalar(self):
        reg = load_physical_bases()
        assert reg.bases["temperature"].kind == "scalar"

    def test_contravariant_metric_tensor_is_tensor(self):
        reg = load_physical_bases()
        assert reg.bases["contravariant_metric_tensor"].kind == "tensor"
