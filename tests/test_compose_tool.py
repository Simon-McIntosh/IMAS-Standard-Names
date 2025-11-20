"""Test renamed names tool methods."""

import asyncio

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.compose import ComposeTool
from imas_standard_names.tools.naming_grammar import NamingGrammarTool


def test_compose_standard_name():
    """Test compose_standard_name (formerly name_compose)."""
    tool = ComposeTool()

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
    tool = ComposeTool()

    result = asyncio.run(tool.parse_standard_name("radial_position_of_flux_loop"))

    assert "name" in result
    assert "parts" in result
    assert result["name"] == "radial_position_of_flux_loop"
    assert result["parts"]["geometric_base"] == "position"
    assert result["parts"]["coordinate"] == "radial"
    assert result["parts"]["object"] == "flux_loop"


def test_vocabulary_in_grammar_tool():
    """Test that vocabulary is now in get_naming_grammar (with section='all')."""
    examples_catalog = StandardNameCatalog(
        root="./imas_standard_names/resources/standard_name_examples",
        permissive=False,
    )
    tool = NamingGrammarTool(examples_catalog)

    # Get full grammar with section='all'
    result = asyncio.run(tool.get_naming_grammar(section="all"))

    assert "vocabulary" in result
    vocab = result["vocabulary"]

    # Check for actual vocabulary segments
    assert "component" in vocab
    assert "subject" in vocab
    assert "position" in vocab
    assert "geometry" in vocab  # Separate from position
    assert "process" in vocab
    assert "object" in vocab

    # Check that vocabulary structure includes templates
    assert "template" in vocab["component"]
    assert vocab["component"]["template"] == "{token}_component_of"
