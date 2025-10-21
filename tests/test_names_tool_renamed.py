"""Test renamed names tool methods."""

import asyncio

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.names import NamesTool
from imas_standard_names.tools.overview import OverviewTool


def test_compose_standard_name():
    """Test compose_standard_name (formerly name_compose)."""
    repo = StandardNameCatalog()
    tool = NamesTool(repo)

    result = asyncio.run(
        tool.compose_standard_name(
            physical_base="heat_flux",
            component="radial",
            subject="electron",
        )
    )

    assert "name" in result
    assert "parts" in result
    assert result["name"] == "radial_component_of_electron_heat_flux"
    assert result["parts"]["physical_base"] == "heat_flux"
    assert result["parts"]["component"] == "radial"
    assert result["parts"]["subject"] == "electron"


def test_parse_standard_name():
    """Test parse_standard_name (formerly name_parse)."""
    repo = StandardNameCatalog()
    tool = NamesTool(repo)

    result = asyncio.run(tool.parse_standard_name("radial_position_of_flux_loop"))

    assert "name" in result
    assert "parts" in result
    assert result["name"] == "radial_position_of_flux_loop"
    assert result["parts"]["geometric_base"] == "position"
    assert result["parts"]["coordinate"] == "radial"
    assert result["parts"]["object"] == "flux_loop"


def test_vocabulary_in_grammar_tool():
    """Test that vocabulary is now in get_grammar_and_vocabulary (merged from name_list_tokens)."""
    repo = StandardNameCatalog()
    tool = OverviewTool(repo)

    result = asyncio.run(tool.get_grammar_and_vocabulary())

    assert "vocabulary" in result
    vocab = result["vocabulary"]

    # Check for actual vocabulary segments
    assert "component" in vocab
    assert "subject" in vocab
    assert "position" in vocab
    assert "geometry" in vocab  # Separate from position
    assert "process" in vocab
    assert "object" in vocab
    assert "source" in vocab

    # Check that vocabulary structure includes templates
    assert "template" in vocab["component"]
    assert vocab["component"]["template"] == "{token}_component_of"

    # Check composition examples (moved to separate key)
    assert "composition_examples" in result
    examples = result["composition_examples"]
    assert isinstance(examples, list)
    assert len(examples) > 0

    # Check first example has required fields
    assert "name" in examples[0]
    assert "parts" in examples[0]
    assert examples[0]["name"] == "toroidal_component_of_magnetic_field"
