"""Tests for generic physical base validation.

Generic physical bases (area, current, power, temperature, voltage, etc.) are
too ambiguous to stand alone and must be qualified with subject, device, object,
position, or geometry context.
"""

import pytest
from pydantic import ValidationError

from imas_standard_names.grammar.constants import GENERIC_PHYSICAL_BASES
from imas_standard_names.grammar.model import StandardName, parse_standard_name
from imas_standard_names.grammar.types import Component, Object, Position, Subject


class TestGenericPhysicalBaseValidation:
    """Test that generic physical bases require qualification."""

    def test_generic_bases_constant_exists(self):
        """Verify GENERIC_PHYSICAL_BASES constant is populated."""
        assert GENERIC_PHYSICAL_BASES
        assert len(GENERIC_PHYSICAL_BASES) > 0
        assert "current" in GENERIC_PHYSICAL_BASES
        assert "temperature" in GENERIC_PHYSICAL_BASES
        assert "voltage" in GENERIC_PHYSICAL_BASES
        assert "power" in GENERIC_PHYSICAL_BASES
        assert "area" in GENERIC_PHYSICAL_BASES

    def test_unqualified_current_fails(self):
        """Test that 'current' alone is rejected."""
        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'current' requires qualification",
        ):
            StandardName(physical_base="current")

    def test_unqualified_temperature_fails(self):
        """Test that 'temperature' alone is rejected."""
        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'temperature' requires qualification",
        ):
            StandardName(physical_base="temperature")

    def test_unqualified_voltage_fails(self):
        """Test that 'voltage' alone is rejected."""
        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'voltage' requires qualification",
        ):
            StandardName(physical_base="voltage")

    def test_unqualified_power_fails(self):
        """Test that 'power' alone is rejected."""
        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'power' requires qualification",
        ):
            StandardName(physical_base="power")

    def test_unqualified_area_fails(self):
        """Test that 'area' alone is rejected."""
        with pytest.raises(
            ValidationError, match="Generic physical_base 'area' requires qualification"
        ):
            StandardName(physical_base="area")

    def test_current_with_subject_valid(self):
        """Test that subject qualification makes generic base valid."""
        model = StandardName(subject=Subject.ELECTRON, physical_base="current")
        assert model.compose() == "electron_current"

    def test_current_with_device_valid(self):
        """Test that device qualification makes generic base valid."""
        model = StandardName(device=Object.POLOIDAL_FIELD_COIL, physical_base="current")
        assert model.compose() == "poloidal_field_coil_current"

    def test_temperature_with_subject_valid(self):
        """Test that subject makes temperature valid."""
        model = StandardName(subject=Subject.ELECTRON, physical_base="temperature")
        assert model.compose() == "electron_temperature"

    def test_voltage_with_device_valid(self):
        """Test that device makes voltage valid."""
        model = StandardName(
            device=Object.POLOIDAL_MAGNETIC_FIELD_PROBE, physical_base="voltage"
        )
        assert model.compose() == "poloidal_magnetic_field_probe_voltage"

    def test_power_with_device_valid(self):
        """Test that device makes power valid."""
        model = StandardName(
            device=Object.ION_CYCLOTRON_HEATING_ANTENNA, physical_base="forward_power"
        )
        assert model.compose() == "ion_cyclotron_heating_antenna_forward_power"

    def test_area_with_object_valid(self):
        """Test that object qualification makes area valid."""
        model = StandardName(physical_base="area", object=Object.FLUX_LOOP)
        assert model.compose() == "area_of_flux_loop"

    def test_pressure_with_position_valid(self):
        """Test that position qualification makes pressure valid."""
        model = StandardName(physical_base="pressure", position=Position.MAGNETIC_AXIS)
        assert model.compose() == "pressure_at_magnetic_axis"

    def test_volume_with_geometry_valid(self):
        """Test that geometry qualification makes volume valid."""
        model = StandardName(
            physical_base="volume_enclosed", geometry=Position.LAST_CLOSED_FLUX_SURFACE
        )
        assert model.compose() == "volume_enclosed_of_last_closed_flux_surface"

    def test_component_does_not_qualify_generic_base(self):
        """Test that component alone doesn't qualify generic physical base."""
        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'current' requires qualification",
        ):
            StandardName(component=Component.RADIAL, physical_base="current")

    def test_coordinate_does_not_qualify_generic_base(self):
        """Test that coordinate alone doesn't qualify generic physical base."""
        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'temperature' requires qualification",
        ):
            StandardName(coordinate=Component.RADIAL, physical_base="temperature")

    def test_non_generic_base_no_qualification_required(self):
        """Test that non-generic physical bases don't need qualification."""
        # magnetic_field is specific, not generic
        model = StandardName(physical_base="magnetic_field")
        assert model.compose() == "magnetic_field"

        # safety_factor is specific
        model = StandardName(physical_base="safety_factor")
        assert model.compose() == "safety_factor"

    def test_parse_unqualified_generic_fails(self):
        """Test that parsing unqualified generic names fails."""
        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'current' requires qualification",
        ):
            parse_standard_name("current")

        with pytest.raises(
            ValidationError,
            match="Generic physical_base 'voltage' requires qualification",
        ):
            parse_standard_name("voltage")

    def test_parse_qualified_generic_succeeds(self):
        """Test that parsing properly qualified generic names succeeds."""
        model = parse_standard_name("electron_temperature")
        assert model.subject == "electron"
        assert model.physical_base == "temperature"

        model = parse_standard_name("poloidal_field_coil_current")
        assert model.device == "poloidal_field_coil"
        assert model.physical_base == "current"

    def test_all_generic_bases_validated(self):
        """Test that all defined generic bases are validated."""
        for generic_base in GENERIC_PHYSICAL_BASES:
            with pytest.raises(
                ValidationError,
                match=f"Generic physical_base '{generic_base}' requires qualification",
            ):
                StandardName(physical_base=generic_base)
