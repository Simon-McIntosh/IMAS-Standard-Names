"""Tests for Phase 1: Unary transformation grammar extensions.

Covers parsing, composition, round-trip, mutual exclusivity,
and edge cases for transformation prefixes on physical bases.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import (
    StandardName,
    Transformation,
    compose_name,
    parse_name,
)
from imas_standard_names.grammar.support import (
    compose_standard_name as compose_parts,
    parse_standard_name as parse_parts,
)


class TestTransformationCompose:
    """Test composition of names with unary transformations."""

    def test_square_of_temperature(self):
        parts = {"transformation": "square_of", "physical_base": "electron_temperature"}
        name = compose_parts(parts)
        assert name == "square_of_electron_temperature"

    def test_change_over_time_in_magnetic_flux(self):
        parts = {
            "transformation": "change_over_time_in",
            "physical_base": "magnetic_flux",
        }
        name = compose_parts(parts)
        assert name == "change_over_time_in_magnetic_flux"

    def test_logarithm_of_density(self):
        parts = {"transformation": "logarithm_of", "physical_base": "density"}
        name = compose_parts(parts)
        assert name == "logarithm_of_density"

    def test_inverse_of_safety_factor(self):
        parts = {"transformation": "inverse_of", "physical_base": "safety_factor"}
        name = compose_parts(parts)
        assert name == "inverse_of_safety_factor"

    def test_transformation_with_subject_prefix(self):
        """Subject prefix should come before transformation+base."""
        name = compose_name(
            {
                "subject": "electron",
                "transformation": "square_of",
                "physical_base": "temperature",
            }
        )
        assert name == "electron_square_of_temperature"

    def test_transformation_with_suffix(self):
        """Suffixes should follow the transformation+base."""
        name = compose_name(
            {
                "transformation": "inverse_of",
                "physical_base": "safety_factor",
                "position": "magnetic_axis",
            }
        )
        assert name == "inverse_of_safety_factor_at_magnetic_axis"

    def test_transformation_via_model(self):
        """Compose via the StandardName model."""
        model = StandardName(
            transformation="square_of",
            physical_base="electron_temperature",
        )
        assert model.compose() == "square_of_electron_temperature"

    def test_transformation_enum_value(self):
        model = StandardName(
            transformation=Transformation.LOGARITHM_OF,
            physical_base="density",
        )
        assert model.compose() == "logarithm_of_density"


class TestTransformationParse:
    """Test parsing of names with unary transformations."""

    def test_parse_square_of(self):
        result = parse_parts("square_of_electron_temperature")
        assert result["transformation"] == "square_of"
        assert result["physical_base"] == "electron_temperature"

    def test_parse_change_over_time_in(self):
        result = parse_parts("change_over_time_in_magnetic_flux")
        assert result["transformation"] == "change_over_time_in"
        assert result["physical_base"] == "magnetic_flux"

    def test_parse_logarithm_of(self):
        result = parse_parts("logarithm_of_density")
        assert result["transformation"] == "logarithm_of"
        assert result["physical_base"] == "density"

    def test_parse_inverse_of(self):
        result = parse_parts("inverse_of_safety_factor")
        assert result["transformation"] == "inverse_of"
        assert result["physical_base"] == "safety_factor"

    def test_parse_with_subject_prefix(self):
        result = parse_parts("electron_square_of_temperature")
        assert result["subject"] == "electron"
        assert result["transformation"] == "square_of"
        assert result["physical_base"] == "temperature"

    def test_parse_with_suffix(self):
        result = parse_parts("inverse_of_safety_factor_at_magnetic_axis")
        assert result["transformation"] == "inverse_of"
        assert result["physical_base"] == "safety_factor"
        assert result["position"] == "magnetic_axis"

    def test_parse_via_model(self):
        model = parse_name("square_of_electron_temperature")
        assert model.transformation == Transformation.SQUARE_OF
        assert model.physical_base == "electron_temperature"

    def test_parse_name_without_transformation(self):
        """Names without transformation should parse normally."""
        result = parse_parts("magnetic_field")
        assert "transformation" not in result
        assert result["physical_base"] == "magnetic_field"


class TestTransformationRoundTrip:
    """Test that compose → parse → compose gives identical results."""

    @pytest.mark.parametrize(
        "parts",
        [
            {"transformation": "square_of", "physical_base": "electron_temperature"},
            {
                "transformation": "change_over_time_in",
                "physical_base": "magnetic_flux",
            },
            {"transformation": "logarithm_of", "physical_base": "density"},
            {"transformation": "inverse_of", "physical_base": "safety_factor"},
            {
                "subject": "electron",
                "transformation": "square_of",
                "physical_base": "temperature",
            },
            {
                "transformation": "inverse_of",
                "physical_base": "safety_factor",
                "position": "magnetic_axis",
            },
        ],
    )
    def test_round_trip(self, parts):
        model = StandardName.model_validate(parts)
        name = model.compose()
        parsed = parse_name(name)
        assert parsed.model_dump_compact() == model.model_dump_compact()


class TestTransformationExclusivity:
    """Test mutual exclusivity constraints for transformations."""

    def test_transformation_excludes_component(self):
        with pytest.raises(ValueError, match="transformation.*component"):
            StandardName(
                transformation="square_of",
                component="radial",
                physical_base="magnetic_field",
            )

    def test_transformation_excludes_coordinate(self):
        with pytest.raises(ValueError, match="transformation.*coordinate"):
            StandardName(
                transformation="square_of",
                coordinate="radial",
                geometric_base="position",
            )

    def test_transformation_excludes_geometric_base(self):
        with pytest.raises(ValueError, match="transformation.*geometric_base"):
            StandardName(
                transformation="square_of",
                geometric_base="position",
            )

    def test_transformation_allows_subject(self):
        """Subject prefix is allowed with transformation."""
        model = StandardName(
            subject="electron",
            transformation="square_of",
            physical_base="temperature",
        )
        assert model.transformation == Transformation.SQUARE_OF
        assert model.subject is not None

    def test_transformation_allows_device(self):
        """Device prefix is allowed with transformation."""
        model = StandardName(
            device="flux_loop",
            transformation="inverse_of",
            physical_base="resistance",
        )
        assert model.transformation == Transformation.INVERSE_OF

    def test_transformation_allows_position_suffix(self):
        """Position suffix is allowed with transformation."""
        model = StandardName(
            transformation="inverse_of",
            physical_base="safety_factor",
            position="magnetic_axis",
        )
        assert model.position is not None

    def test_transformation_allows_process_suffix(self):
        """Process suffix is allowed with transformation."""
        model = StandardName(
            transformation="square_of",
            physical_base="electron_temperature",
            process="ohmic",
        )
        assert model.process is not None


class TestTransformationEdgeCases:
    """Test edge cases for transformation handling."""

    def test_name_starting_with_square_but_not_transformation(self):
        """A name like 'square_root_function' should not match transformation."""
        result = parse_parts("square_root_function")
        assert "transformation" not in result
        assert result["physical_base"] == "square_root_function"

    def test_invalid_transformation_token(self):
        with pytest.raises(ValueError):
            StandardName(
                transformation="cube_of",
                physical_base="temperature",
            )

    def test_transformation_qualifies_generic_base(self):
        """Transformation should qualify generic physical bases."""
        model = StandardName(
            transformation="square_of",
            physical_base="temperature",
        )
        assert model.physical_base == "temperature"
