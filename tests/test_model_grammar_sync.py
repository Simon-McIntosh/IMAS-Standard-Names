"""Test that StandardName model stays in sync with grammar specification.

This test validates model.py and names.py (MCP tool) against the actual YAML
grammar specification, ensuring that any changes to the grammar are reflected
in both the model and the tool interface.
"""

import asyncio
import inspect

import pytest

from imas_standard_names.grammar.model import StandardName
from imas_standard_names.grammar.types import (
    EXCLUSIVE_SEGMENT_PAIRS,
    SEGMENT_ORDER,
    Component,
    Object,
    Position,
    Process,
    Source,
    Subject,
)
from imas_standard_names.grammar_codegen.spec import GrammarSpec
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.names import NamesTool


def _load_grammar_spec():
    """Load the grammar specification from YAML files."""
    return GrammarSpec.load()


def _build_expected_type_map(spec: GrammarSpec):
    """Build expected type map from grammar specification."""
    from imas_standard_names.grammar_codegen.generate import (
        ENUM_NAME_OVERRIDES,
        _enum_class_name,
    )

    type_map = {}
    for segment in spec.segments:
        if segment.vocabulary_name:
            enum_name = _enum_class_name(segment.vocabulary_name)
            # Map enum name to actual type
            type_class = {
                "Component": Component,
                "Subject": Subject,
                "Object": Object,
                "Source": Source,
                "Position": Position,
                "Process": Process,
            }.get(enum_name)
            type_map[segment.identifier] = type_class
        else:
            # Base segment has no vocabulary
            type_map[segment.identifier] = str
    return type_map


def test_model_has_all_grammar_segments():
    """Verify StandardName has fields for all segments in specification.yml."""
    spec = _load_grammar_spec()
    model_fields = set(StandardName.model_fields.keys())
    grammar_segments = {segment.identifier for segment in spec.segments}

    assert model_fields == grammar_segments, (
        f"StandardName fields don't match grammar specification!\n"
        f"Missing in model: {grammar_segments - model_fields}\n"
        f"Extra in model: {model_fields - grammar_segments}\n"
        f"\nUpdate model.py to match specification.yml"
    )


def test_model_field_types_match_grammar():
    """Verify StandardName field types match expected types from specification.yml."""
    spec = _load_grammar_spec()
    expected_type_map = _build_expected_type_map(spec)

    for segment in spec.segments:
        segment_name = segment.identifier
        expected_type = expected_type_map[segment_name]

        field_info = StandardName.model_fields.get(segment_name)
        assert field_info is not None, f"Missing field: {segment_name}"

        # Get the actual annotation
        annotation = field_info.annotation

        # For base (required field)
        if not segment.optional:
            assert "str" in str(annotation) or annotation is str, (
                f"Field '{segment_name}' should be str, got {annotation}"
            )
        else:
            # All other fields are optional - check type is present
            if expected_type:
                assert expected_type.__name__ in str(annotation), (
                    f"Field '{segment_name}' type mismatch.\n"
                    f"Expected: {expected_type}\n"
                    f"Got: {annotation}"
                )


def test_model_has_exclusivity_validation():
    """Verify StandardName validates exclusive segment pairs."""
    # Test component/coordinate exclusivity
    with pytest.raises(ValueError, match="component.*coordinate"):
        StandardName(
            base="temperature",
            component=Component.RADIAL,
            coordinate=Component.TOROIDAL,
        )

    # Test object/source exclusivity
    with pytest.raises(ValueError, match="object.*source"):
        StandardName(
            base="temperature",
            object=Object.FLUX_LOOP,
            source=Source.FLUX_LOOP,
        )

    # Test geometry/position exclusivity
    with pytest.raises(ValueError, match="geometry.*position"):
        StandardName(
            base="temperature",
            geometry=Position.MAGNETIC_AXIS,
            position=Position.PLASMA_BOUNDARY,
        )


def test_exclusive_pairs_match_specification():
    """Verify EXCLUSIVE_SEGMENT_PAIRS matches exclusive_with in specification.yml."""
    spec = _load_grammar_spec()

    # Build expected pairs from specification
    expected_pairs = set()
    for segment in spec.segments:
        for other in segment.exclusive_with:
            # Normalize pair order (alphabetically sorted)
            pair = tuple(sorted([segment.identifier, other]))
            expected_pairs.add(pair)

    actual_pairs = set(EXCLUSIVE_SEGMENT_PAIRS)

    assert actual_pairs == expected_pairs, (
        f"EXCLUSIVE_SEGMENT_PAIRS doesn't match specification.yml!\n"
        f"Expected from YAML: {expected_pairs}\n"
        f"Got from types.py: {actual_pairs}\n"
        f"\nRun: python -m imas_standard_names.grammar_codegen.generate"
    )


def test_model_optional_fields_match_specification():
    """Verify optional/required fields match specification.yml."""
    spec = _load_grammar_spec()

    for segment in spec.segments:
        field_info = StandardName.model_fields.get(segment.identifier)
        assert field_info is not None, f"Missing field: {segment.identifier}"

        # Check if field is required/optional
        is_required = field_info.is_required()

        if segment.optional:
            assert not is_required, (
                f"Field '{segment.identifier}' should be optional according to specification.yml"
            )
        else:
            assert is_required, (
                f"Field '{segment.identifier}' should be required according to specification.yml"
            )


def test_names_tool_has_all_segment_parameters():
    """Verify compose_standard_name MCP tool has parameters for all segments."""
    spec = _load_grammar_spec()
    tool = NamesTool(StandardNameCatalog())

    # Get the compose_standard_name method signature
    sig = inspect.signature(tool.compose_standard_name)
    tool_params = set(sig.parameters.keys())

    # Remove non-segment parameters (self, ctx)
    tool_params.discard("self")
    tool_params.discard("ctx")

    # Get expected segments from grammar
    grammar_segments = {segment.identifier for segment in spec.segments}

    assert tool_params == grammar_segments, (
        f"compose_standard_name parameters don't match grammar specification!\n"
        f"Missing parameters: {grammar_segments - tool_params}\n"
        f"Extra parameters: {tool_params - grammar_segments}\n"
        f"\nUpdate NamesTool.compose_standard_name in names.py"
    )


def test_names_tool_parameter_types_match_grammar():
    """Verify compose_standard_name parameter types match grammar vocabularies."""
    spec = _load_grammar_spec()
    expected_type_map = _build_expected_type_map(spec)
    tool = NamesTool(StandardNameCatalog())

    # Get the compose_standard_name method signature
    sig = inspect.signature(tool.compose_standard_name)

    for segment in spec.segments:
        param_name = segment.identifier

        # Skip ctx parameter
        if param_name == "ctx":
            continue

        param = sig.parameters.get(param_name)
        assert param is not None, f"Missing parameter: {param_name}"

        # Get annotation
        annotation_str = str(param.annotation)
        expected_type = expected_type_map.get(param_name)

        if expected_type:
            # Check that the expected type appears in the annotation
            assert expected_type.__name__ in annotation_str, (
                f"Parameter '{param_name}' type mismatch.\n"
                f"Expected type: {expected_type.__name__}\n"
                f"Got annotation: {annotation_str}"
            )


def test_names_tool_compose_creates_valid_model():
    """Verify compose_standard_name tool creates valid StandardName instances."""
    tool = NamesTool(StandardNameCatalog())

    # Test basic composition
    result = asyncio.run(
        tool.compose_standard_name(
            base="temperature", component="radial", subject="electron"
        )
    )

    assert "name" in result
    assert "parts" in result
    assert result["name"] == "radial_electron_temperature"

    # Test with object parameter
    result = asyncio.run(
        tool.compose_standard_name(base="major_radius", object="flux_loop")
    )

    assert result["name"] == "major_radius_of_flux_loop"

    # Test with source parameter
    result = asyncio.run(tool.compose_standard_name(base="voltage", source="flux_loop"))

    assert result["name"] == "voltage_from_flux_loop"


def test_names_tool_respects_exclusive_pairs():
    """Verify compose_standard_name enforces exclusive segment pairs."""
    tool = NamesTool(StandardNameCatalog())

    # Test component/coordinate exclusivity
    with pytest.raises(ValueError, match="component.*coordinate"):
        asyncio.run(
            tool.compose_standard_name(
                base="temperature", component="radial", coordinate="toroidal"
            )
        )

    # Test object/source exclusivity
    with pytest.raises(ValueError, match="object.*source"):
        asyncio.run(
            tool.compose_standard_name(
                base="temperature", object="flux_loop", source="flux_loop"
            )
        )
