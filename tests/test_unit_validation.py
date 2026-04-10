"""Tests for Phase 3: Dimensionless unit validation in semantic checks."""

from __future__ import annotations

from imas_standard_names.models import (
    StandardNameMetadataEntry,
    StandardNameScalarEntry,
    StandardNameVectorEntry,
)
from imas_standard_names.validation.semantic import (
    _check_dimensionless_physical_quantity,
)


def _scalar(name: str, unit: str = "eV") -> StandardNameScalarEntry:
    return StandardNameScalarEntry(
        name=name,
        kind="scalar",
        unit=unit,
        description="Test entry",
        documentation="Test documentation for validation.",
        physics_domain="general",
        status="draft",
    )


def _vector(name: str, unit: str = "m.s^-1") -> StandardNameVectorEntry:
    return StandardNameVectorEntry(
        name=name,
        kind="vector",
        unit=unit,
        description="Test entry",
        documentation="Test documentation for validation.",
        physics_domain="general",
        status="draft",
    )


def _metadata(name: str) -> StandardNameMetadataEntry:
    return StandardNameMetadataEntry(
        name=name,
        kind="metadata",
        description="Test entry",
        documentation="Test documentation for validation.",
        physics_domain="general",
        status="draft",
    )


class TestDimensionlessPhysicalQuantity:
    """Test _check_dimensionless_physical_quantity semantic check."""

    def test_warns_temperature_with_unit_one(self):
        entry = _scalar("electron_temperature", unit="1")
        issues = _check_dimensionless_physical_quantity("electron_temperature", entry)
        assert len(issues) == 1
        assert "WARNING" in issues[0]
        assert "temperature" in issues[0]
        assert "dimensionless" in issues[0]

    def test_warns_density_with_unit_one(self):
        entry = _scalar("electron_density", unit="1")
        issues = _check_dimensionless_physical_quantity("electron_density", entry)
        assert len(issues) == 1
        assert "density" in issues[0]

    def test_warns_pressure_with_unit_one(self):
        entry = _scalar("electron_pressure", unit="1")
        issues = _check_dimensionless_physical_quantity("electron_pressure", entry)
        assert len(issues) == 1
        assert "pressure" in issues[0]

    def test_warns_velocity_with_unit_one(self):
        entry = _scalar("ion_velocity", unit="1")
        issues = _check_dimensionless_physical_quantity("ion_velocity", entry)
        assert len(issues) == 1
        assert "velocity" in issues[0]

    def test_no_warning_for_proper_unit(self):
        entry = _scalar("electron_temperature", unit="eV")
        issues = _check_dimensionless_physical_quantity("electron_temperature", entry)
        assert issues == []

    def test_no_warning_for_non_dimensional_base(self):
        """Names with bases not in the inherently-dimensional set should pass."""
        entry = _scalar("safety_factor", unit="1")
        issues = _check_dimensionless_physical_quantity("safety_factor", entry)
        assert issues == []

    def test_no_warning_for_ratio_binary_operator(self):
        """Binary operator names (ratios) can legitimately be dimensionless."""
        entry = _scalar("ratio_of_electron_temperature_to_ion_temperature", unit="1")
        issues = _check_dimensionless_physical_quantity(
            "ratio_of_electron_temperature_to_ion_temperature", entry
        )
        assert issues == []

    def test_no_warning_for_product_binary_operator(self):
        entry = _scalar("product_of_density_and_velocity", unit="1")
        issues = _check_dimensionless_physical_quantity(
            "product_of_density_and_velocity", entry
        )
        assert issues == []

    def test_no_warning_for_metadata_entry(self):
        entry = _metadata("plasma_boundary")
        issues = _check_dimensionless_physical_quantity("plasma_boundary", entry)
        assert issues == []

    def test_vector_with_unit_one_warns(self):
        entry = _vector("magnetic_field", unit="1")
        issues = _check_dimensionless_physical_quantity("magnetic_field", entry)
        assert len(issues) == 1
        assert "magnetic_field" in issues[0]

    def test_warns_for_area(self):
        entry = _scalar("area_of_flux_loop", unit="1")
        issues = _check_dimensionless_physical_quantity("area_of_flux_loop", entry)
        assert len(issues) == 1
        assert "area" in issues[0]

    def test_warns_for_energy(self):
        entry = _scalar("electron_energy", unit="1")
        issues = _check_dimensionless_physical_quantity("electron_energy", entry)
        assert len(issues) == 1
        assert "energy" in issues[0]

    def test_no_warning_for_different_unit(self):
        """Non-'1' units should never trigger this check."""
        entry = _scalar("electron_temperature", unit="K")
        issues = _check_dimensionless_physical_quantity("electron_temperature", entry)
        assert issues == []
