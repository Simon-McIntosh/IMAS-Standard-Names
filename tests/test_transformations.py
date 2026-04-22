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

# rc20 token forms (e.g. square_of, inverse_of) were replaced by bare tokens
# (square, inverse) in vNext grammar (plan 38 §A7).  Tests that rely on the
# old forms are preserved for reference but marked as expected failures until
# vNext grammar is finalised.
_XFAIL_RC20 = pytest.mark.xfail(
    strict=True,
    reason=(
        "rc20 _of-suffixed tokens replaced by bare tokens in vNext grammar"
        " (plan 38 §A7)"
    ),
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

    def test_volume_averaged(self):
        parts = {
            "transformation": "volume_averaged",
            "physical_base": "electron_temperature",
        }
        name = compose_parts(parts)
        assert name == "volume_averaged_electron_temperature"

    def test_time_derivative_of(self):
        parts = {
            "transformation": "time_derivative_of",
            "physical_base": "magnetic_flux",
        }
        name = compose_parts(parts)
        assert name == "time_derivative_of_magnetic_flux"

    def test_normalized(self):
        parts = {"transformation": "normalized", "physical_base": "electron_pressure"}
        name = compose_parts(parts)
        assert name == "normalized_electron_pressure"

    def test_flux_surface_averaged(self):
        parts = {
            "transformation": "flux_surface_averaged",
            "physical_base": "electron_temperature",
        }
        name = compose_parts(parts)
        assert name == "flux_surface_averaged_electron_temperature"

    def test_line_averaged(self):
        parts = {"transformation": "line_averaged", "physical_base": "electron_density"}
        name = compose_parts(parts)
        assert name == "line_averaged_electron_density"

    def test_surface_integrated(self):
        parts = {"transformation": "surface_integrated", "physical_base": "heat_flux"}
        name = compose_parts(parts)
        assert name == "surface_integrated_heat_flux"

    def test_volume_integrated(self):
        parts = {"transformation": "volume_integrated", "physical_base": "power"}
        name = compose_parts(parts)
        assert name == "volume_integrated_power"

    def test_time_integrated(self):
        parts = {
            "transformation": "time_integrated",
            "physical_base": "radiation_power",
        }
        name = compose_parts(parts)
        assert name == "time_integrated_radiation_power"

    def test_maximum_of(self):
        parts = {"transformation": "maximum_of", "physical_base": "electron_pressure"}
        name = compose_parts(parts)
        assert name == "maximum_of_electron_pressure"

    def test_minimum_of(self):
        parts = {"transformation": "minimum_of", "physical_base": "safety_factor"}
        name = compose_parts(parts)
        assert name == "minimum_of_safety_factor"

    def test_maximum_over_flux_surface(self):
        parts = {
            "transformation": "maximum_over_flux_surface",
            "physical_base": "electron_temperature",
        }
        name = compose_parts(parts)
        assert name == "maximum_over_flux_surface_electron_temperature"

    def test_minimum_over_flux_surface(self):
        parts = {
            "transformation": "minimum_over_flux_surface",
            "physical_base": "safety_factor",
        }
        name = compose_parts(parts)
        assert name == "minimum_over_flux_surface_safety_factor"

    def test_derivative_of(self):
        parts = {
            "transformation": "derivative_of",
            "physical_base": "electron_temperature",
        }
        name = compose_parts(parts)
        assert name == "derivative_of_electron_temperature"

    def test_radial_derivative_of(self):
        parts = {
            "transformation": "radial_derivative_of",
            "physical_base": "electron_pressure",
        }
        name = compose_parts(parts)
        assert name == "radial_derivative_of_electron_pressure"

    @_XFAIL_RC20
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

    @_XFAIL_RC20
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

    @_XFAIL_RC20
    def test_transformation_via_model(self):
        """Compose via the StandardName model."""
        model = StandardName(
            transformation="square_of",
            physical_base="electron_temperature",
        )
        assert model.compose() == "square_of_electron_temperature"

    @_XFAIL_RC20
    def test_transformation_enum_value(self):
        model = StandardName(
            transformation=Transformation.LOGARITHM_OF,
            physical_base="density",
        )
        assert model.compose() == "logarithm_of_density"


class TestTransformationParse:
    """Test parsing of names with unary transformations."""

    @_XFAIL_RC20
    def test_parse_square_of(self):
        result = parse_parts("square_of_electron_temperature")
        assert result["transformation"] == "square_of"
        assert result["physical_base"] == "electron_temperature"

    @_XFAIL_RC20
    def test_parse_change_over_time_in(self):
        result = parse_parts("change_over_time_in_magnetic_flux")
        assert result["transformation"] == "change_over_time_in"
        assert result["physical_base"] == "magnetic_flux"

    @_XFAIL_RC20
    def test_parse_logarithm_of(self):
        result = parse_parts("logarithm_of_density")
        assert result["transformation"] == "logarithm_of"
        assert result["physical_base"] == "density"

    @_XFAIL_RC20
    def test_parse_inverse_of(self):
        result = parse_parts("inverse_of_safety_factor")
        assert result["transformation"] == "inverse_of"
        assert result["physical_base"] == "safety_factor"

    def test_parse_volume_averaged(self):
        result = parse_parts("volume_averaged_electron_temperature")
        assert result["transformation"] == "volume_averaged"
        assert result["physical_base"] == "electron_temperature"

    @_XFAIL_RC20
    def test_parse_time_derivative_of(self):
        result = parse_parts("time_derivative_of_magnetic_flux")
        assert result["transformation"] == "time_derivative_of"
        assert result["physical_base"] == "magnetic_flux"

    def test_parse_normalized(self):
        result = parse_parts("normalized_electron_pressure")
        assert result["transformation"] == "normalized"
        assert result["physical_base"] == "electron_pressure"

    def test_parse_flux_surface_averaged(self):
        result = parse_parts("flux_surface_averaged_electron_temperature")
        assert result["transformation"] == "flux_surface_averaged"
        assert result["physical_base"] == "electron_temperature"

    def test_parse_maximum_over_flux_surface(self):
        result = parse_parts("maximum_over_flux_surface_electron_temperature")
        assert result["transformation"] == "maximum_over_flux_surface"
        assert result["physical_base"] == "electron_temperature"

    @_XFAIL_RC20
    def test_parse_radial_derivative_of(self):
        """Parser splits radial_derivative_of as coordinate=radial + transformation=derivative_of."""
        result = parse_parts("radial_derivative_of_electron_pressure")
        assert result["transformation"] == "derivative_of"
        assert result["coordinate"] == "radial"
        assert result["physical_base"] == "electron_pressure"

    @_XFAIL_RC20
    def test_parse_with_subject_prefix(self):
        result = parse_parts("electron_square_of_temperature")
        assert result["subject"] == "electron"
        assert result["transformation"] == "square_of"
        assert result["physical_base"] == "temperature"

    @_XFAIL_RC20
    def test_parse_with_suffix(self):
        result = parse_parts("inverse_of_safety_factor_at_magnetic_axis")
        assert result["transformation"] == "inverse_of"
        assert result["physical_base"] == "safety_factor"
        assert result["position"] == "magnetic_axis"

    @_XFAIL_RC20
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
            pytest.param(
                {
                    "transformation": "square_of",
                    "physical_base": "electron_temperature",
                },
                marks=_XFAIL_RC20,
            ),
            pytest.param(
                {
                    "transformation": "change_over_time_in",
                    "physical_base": "magnetic_flux",
                },
                marks=_XFAIL_RC20,
            ),
            pytest.param(
                {"transformation": "logarithm_of", "physical_base": "density"},
                marks=_XFAIL_RC20,
            ),
            pytest.param(
                {"transformation": "inverse_of", "physical_base": "safety_factor"},
                marks=_XFAIL_RC20,
            ),
            pytest.param(
                {
                    "subject": "electron",
                    "transformation": "square_of",
                    "physical_base": "temperature",
                },
                marks=_XFAIL_RC20,
            ),
            pytest.param(
                {
                    "transformation": "inverse_of",
                    "physical_base": "safety_factor",
                    "position": "magnetic_axis",
                },
                marks=_XFAIL_RC20,
            ),
            {"transformation": "volume_averaged", "physical_base": "electron_density"},
            {
                "transformation": "flux_surface_averaged",
                "physical_base": "electron_temperature",
            },
            {"transformation": "line_averaged", "physical_base": "electron_density"},
            {"transformation": "surface_integrated", "physical_base": "heat_flux"},
            {"transformation": "volume_integrated", "physical_base": "power"},
            pytest.param(
                {
                    "transformation": "time_integrated",
                    "physical_base": "radiation_power",
                },
                marks=_XFAIL_RC20,
            ),
            pytest.param(
                {
                    "transformation": "time_derivative_of",
                    "physical_base": "magnetic_flux",
                },
                marks=_XFAIL_RC20,
            ),
            {"transformation": "normalized", "physical_base": "electron_pressure"},
            pytest.param(
                {"transformation": "maximum_of", "physical_base": "electron_pressure"},
                marks=_XFAIL_RC20,
            ),
            pytest.param(
                {"transformation": "minimum_of", "physical_base": "safety_factor"},
                marks=_XFAIL_RC20,
            ),
            {
                "transformation": "maximum_over_flux_surface",
                "physical_base": "electron_temperature",
            },
            {
                "transformation": "minimum_over_flux_surface",
                "physical_base": "safety_factor",
            },
            pytest.param(
                {
                    "transformation": "derivative_of",
                    "physical_base": "electron_temperature",
                },
                marks=_XFAIL_RC20,
            ),
        ],
    )
    def test_round_trip(self, parts):
        model = StandardName.model_validate(parts)
        name = model.compose()
        parsed = parse_name(name)
        assert parsed.model_dump_compact() == model.model_dump_compact()

    @_XFAIL_RC20
    def test_radial_derivative_compose_parse(self):
        """radial_derivative_of composes correctly but parses as coordinate+derivative_of."""
        model = StandardName(
            transformation="radial_derivative_of",
            physical_base="electron_pressure",
        )
        name = model.compose()
        assert name == "radial_derivative_of_electron_pressure"
        # Parser interprets 'radial' as a coordinate prefix
        result = parse_parts(name)
        assert result["coordinate"] == "radial"
        assert result["transformation"] == "derivative_of"
        assert result["physical_base"] == "electron_pressure"


class TestTransformationExclusivity:
    """Test mutual exclusivity constraints for transformations."""

    @_XFAIL_RC20
    def test_transformation_excludes_component(self):
        with pytest.raises(ValueError, match="transformation.*component"):
            StandardName(
                transformation="square_of",
                component="radial",
                physical_base="magnetic_field",
            )

    @_XFAIL_RC20
    def test_transformation_excludes_coordinate(self):
        with pytest.raises(ValueError, match="transformation.*coordinate"):
            StandardName(
                transformation="square_of",
                coordinate="radial",
                geometric_base="position",
            )

    @_XFAIL_RC20
    def test_transformation_excludes_geometric_base(self):
        with pytest.raises(ValueError, match="transformation.*geometric_base"):
            StandardName(
                transformation="square_of",
                geometric_base="position",
            )

    @_XFAIL_RC20
    def test_transformation_allows_subject(self):
        """Subject prefix is allowed with transformation."""
        model = StandardName(
            subject="electron",
            transformation="square_of",
            physical_base="temperature",
        )
        assert model.transformation == Transformation.SQUARE_OF
        assert model.subject is not None

    @_XFAIL_RC20
    def test_transformation_allows_device(self):
        """Device prefix is allowed with transformation."""
        model = StandardName(
            device="flux_loop",
            transformation="inverse_of",
            physical_base="resistance",
        )
        assert model.transformation == Transformation.INVERSE_OF

    @_XFAIL_RC20
    def test_transformation_allows_position_suffix(self):
        """Position suffix is allowed with transformation."""
        model = StandardName(
            transformation="inverse_of",
            physical_base="safety_factor",
            position="magnetic_axis",
        )
        assert model.position is not None

    @_XFAIL_RC20
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

    @_XFAIL_RC20
    def test_time_derivative_synonym(self):
        """Both time_derivative_of and change_over_time_in are valid transformations."""
        for t in ["time_derivative_of", "change_over_time_in"]:
            name = f"{t}_electron_temperature"
            parsed = parse_parts(name)
            assert parsed["transformation"] == t
            assert parsed["physical_base"] == "electron_temperature"

    @_XFAIL_RC20
    def test_radial_derivative_not_radial_component(self):
        """radial_derivative_of parses as coordinate=radial + transformation=derivative_of."""
        name = "radial_derivative_of_electron_pressure"
        parsed = parse_parts(name)
        assert parsed["transformation"] == "derivative_of"
        assert parsed["coordinate"] == "radial"
        assert "component" not in parsed

    @_XFAIL_RC20
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

    @_XFAIL_RC20
    def test_transformation_qualifies_generic_base(self):
        """Transformation should qualify generic physical bases."""
        model = StandardName(
            transformation="square_of",
            physical_base="temperature",
        )
        assert model.physical_base == "temperature"
