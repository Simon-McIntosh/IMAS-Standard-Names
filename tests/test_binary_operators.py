"""Tests for Phase 2: Binary operator grammar extensions.

Covers parsing, composition, round-trip, mutual exclusivity, connector
detection, and edge cases for binary operator expressions.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import (
    BinaryOperator,
    StandardName,
    compose_name,
    parse_name,
)
from imas_standard_names.grammar.support import (
    compose_standard_name as compose_parts,
    parse_standard_name as parse_parts,
)


class TestBinaryOperatorCompose:
    """Test composition of names with binary operators."""

    def test_product_of_density_and_temperature(self):
        parts = {
            "binary_operator": "product_of",
            "physical_base": "density",
            "secondary_base": "temperature",
        }
        name = compose_parts(parts)
        assert name == "product_of_density_and_temperature"

    def test_ratio_of_electron_temperature_to_ion_temperature(self):
        parts = {
            "binary_operator": "ratio_of",
            "physical_base": "electron_temperature",
            "secondary_base": "ion_temperature",
        }
        name = compose_parts(parts)
        assert name == "ratio_of_electron_temperature_to_ion_temperature"

    def test_difference_of_pressures(self):
        parts = {
            "binary_operator": "difference_of",
            "physical_base": "total_pressure",
            "secondary_base": "electron_pressure",
        }
        name = compose_parts(parts)
        assert name == "difference_of_total_pressure_and_electron_pressure"

    def test_binary_operator_with_position_suffix(self):
        name = compose_name(
            {
                "binary_operator": "ratio_of",
                "physical_base": "electron_temperature",
                "secondary_base": "ion_temperature",
                "position": "magnetic_axis",
            }
        )
        assert (
            name == "ratio_of_electron_temperature_to_ion_temperature_at_magnetic_axis"
        )

    def test_binary_operator_with_process_suffix(self):
        name = compose_name(
            {
                "binary_operator": "product_of",
                "physical_base": "density",
                "secondary_base": "velocity",
                "process": "turbulent",
            }
        )
        assert name == "product_of_density_and_velocity_due_to_turbulent"

    def test_binary_operator_via_model(self):
        model = StandardName(
            binary_operator="product_of",
            physical_base="density",
            secondary_base="temperature",
        )
        assert model.compose() == "product_of_density_and_temperature"

    def test_binary_operator_enum_value(self):
        model = StandardName(
            binary_operator=BinaryOperator.RATIO_OF,
            physical_base="electron_temperature",
            secondary_base="ion_temperature",
        )
        assert model.compose() == "ratio_of_electron_temperature_to_ion_temperature"


class TestBinaryOperatorParse:
    """Test parsing of names with binary operators."""

    def test_parse_product_of(self):
        result = parse_parts("product_of_density_and_temperature")
        assert result["binary_operator"] == "product_of"
        assert result["physical_base"] == "density"
        assert result["secondary_base"] == "temperature"

    def test_parse_ratio_of(self):
        result = parse_parts("ratio_of_electron_temperature_to_ion_temperature")
        assert result["binary_operator"] == "ratio_of"
        assert result["physical_base"] == "electron_temperature"
        assert result["secondary_base"] == "ion_temperature"

    def test_parse_difference_of(self):
        result = parse_parts("difference_of_total_pressure_and_electron_pressure")
        assert result["binary_operator"] == "difference_of"
        assert result["physical_base"] == "total_pressure"
        assert result["secondary_base"] == "electron_pressure"

    def test_parse_with_suffix(self):
        result = parse_parts(
            "ratio_of_electron_temperature_to_ion_temperature_at_magnetic_axis"
        )
        assert result["binary_operator"] == "ratio_of"
        assert result["physical_base"] == "electron_temperature"
        assert result["secondary_base"] == "ion_temperature"
        assert result["position"] == "magnetic_axis"

    def test_parse_via_model(self):
        model = parse_name("product_of_density_and_temperature")
        assert model.binary_operator == BinaryOperator.PRODUCT_OF
        assert model.physical_base == "density"
        assert model.secondary_base == "temperature"


class TestBinaryOperatorRoundTrip:
    """Test that compose → parse → compose gives identical results."""

    @pytest.mark.parametrize(
        "parts",
        [
            {
                "binary_operator": "product_of",
                "physical_base": "density",
                "secondary_base": "temperature",
            },
            {
                "binary_operator": "ratio_of",
                "physical_base": "electron_temperature",
                "secondary_base": "ion_temperature",
            },
            {
                "binary_operator": "difference_of",
                "physical_base": "total_pressure",
                "secondary_base": "electron_pressure",
            },
            {
                "binary_operator": "ratio_of",
                "physical_base": "electron_temperature",
                "secondary_base": "ion_temperature",
                "position": "magnetic_axis",
            },
            {
                "binary_operator": "product_of",
                "physical_base": "density",
                "secondary_base": "velocity",
                "process": "turbulent",
            },
        ],
    )
    def test_round_trip(self, parts):
        model = StandardName.model_validate(parts)
        name = model.compose()
        parsed = parse_name(name)
        assert parsed.model_dump_compact() == model.model_dump_compact()


class TestBinaryOperatorExclusivity:
    """Test mutual exclusivity constraints for binary operators."""

    def test_binary_excludes_component(self):
        with pytest.raises(ValueError, match="binary_operator.*component"):
            StandardName(
                binary_operator="product_of",
                component="radial",
                physical_base="magnetic_field",
                secondary_base="density",
            )

    def test_binary_excludes_transformation(self):
        with pytest.raises(ValueError, match="binary_operator.*transformation"):
            StandardName(
                binary_operator="product_of",
                transformation="square_of",
                physical_base="temperature",
                secondary_base="density",
            )

    def test_binary_excludes_coordinate(self):
        with pytest.raises(ValueError, match="binary_operator.*coordinate"):
            StandardName(
                binary_operator="product_of",
                coordinate="radial",
                physical_base="position",
                secondary_base="density",
            )

    def test_binary_excludes_subject(self):
        with pytest.raises(ValueError, match="binary_operator.*subject"):
            StandardName(
                binary_operator="product_of",
                subject="electron",
                physical_base="temperature",
                secondary_base="density",
            )

    def test_binary_excludes_device(self):
        with pytest.raises(ValueError, match="binary_operator.*device"):
            StandardName(
                binary_operator="product_of",
                device="flux_loop",
                physical_base="voltage",
                secondary_base="current",
            )

    def test_binary_excludes_geometric_base(self):
        with pytest.raises(ValueError, match="binary_operator.*geometric_base"):
            StandardName(
                binary_operator="product_of",
                geometric_base="position",
                secondary_base="density",
            )

    def test_binary_allows_object_suffix(self):
        model = StandardName(
            binary_operator="ratio_of",
            physical_base="area",
            secondary_base="volume",
            object="flux_loop",
        )
        assert model.object is not None

    def test_binary_allows_position_suffix(self):
        model = StandardName(
            binary_operator="ratio_of",
            physical_base="electron_temperature",
            secondary_base="ion_temperature",
            position="magnetic_axis",
        )
        assert model.position is not None

    def test_binary_requires_secondary_base(self):
        with pytest.raises(ValueError, match="secondary_base"):
            StandardName(
                binary_operator="product_of",
                physical_base="density",
            )

    def test_secondary_base_without_binary_operator(self):
        with pytest.raises(ValueError, match="secondary_base.*binary_operator"):
            StandardName(
                physical_base="density",
                secondary_base="temperature",
            )


class TestBinaryOperatorConnectors:
    """Test connector word handling."""

    def test_product_uses_and(self):
        name = compose_name(
            {
                "binary_operator": "product_of",
                "physical_base": "a",
                "secondary_base": "b",
            }
        )
        assert "_and_" in name

    def test_ratio_uses_to(self):
        name = compose_name(
            {
                "binary_operator": "ratio_of",
                "physical_base": "a",
                "secondary_base": "b",
            }
        )
        assert "_to_" in name

    def test_difference_uses_and(self):
        name = compose_name(
            {
                "binary_operator": "difference_of",
                "physical_base": "a",
                "secondary_base": "b",
            }
        )
        assert "_and_" in name


class TestBinaryOperatorEdgeCases:
    """Test edge cases for binary operator handling."""

    def test_invalid_binary_operator_token(self):
        with pytest.raises(ValueError):
            StandardName(
                binary_operator="sum_of",
                physical_base="a",
                secondary_base="b",
            )

    def test_name_starting_with_product_but_not_binary(self):
        """A name like 'product_cross_section' should not be parsed as binary."""
        result = parse_parts("product_cross_section")
        assert "binary_operator" not in result
        assert result["physical_base"] == "product_cross_section"

    def test_binary_qualifies_generic_base(self):
        """Binary operator should qualify generic physical bases."""
        model = StandardName(
            binary_operator="product_of",
            physical_base="temperature",
            secondary_base="density",
        )
        assert model.physical_base == "temperature"

    def test_compound_base_with_and_in_name(self):
        """Test that rightmost split handles compound bases correctly."""
        # If a base name could contain the connector, rightmost split helps
        result = parse_parts("product_of_supply_and_demand_and_output")
        assert result["binary_operator"] == "product_of"
        assert result["physical_base"] == "supply_and_demand"
        assert result["secondary_base"] == "output"
