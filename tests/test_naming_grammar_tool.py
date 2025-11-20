import asyncio

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.naming_grammar import NamingGrammarTool
from imas_standard_names.tools.schema import SchemaTool


def test_overview_structure(sample_catalog):
    """Test that default overview returns compact structure with available sections."""
    tool = NamingGrammarTool()

    # Without section parameter, should return overview (not full structure)
    result = asyncio.run(tool.get_naming_grammar())

    # Should have canonical pattern in overview
    assert "canonical_pattern" in result
    expected_pattern = (
        "[<component>_component_of | <coordinate>]? [<subject>]? [<device> | of_<object>]? "
        "[<geometric_base> | <physical_base>]? "
        "[of_<geometry> | at_<position>]? [due_to_<process>]?"
    )
    assert result["canonical_pattern"] == expected_pattern

    # Should have common patterns as quick reference
    assert "common_patterns" in result
    patterns = result["common_patterns"]
    assert "vector_component" in patterns
    assert "device_signal" in patterns
    assert "object_property" in patterns

    # Should have critical distinctions
    assert "critical_distinctions" in result
    distinctions = result["critical_distinctions"]
    assert "component_vs_coordinate" in distinctions
    assert "device_vs_object" in distinctions
    assert "geometry_vs_position" in distinctions

    # Quick start workflow
    assert "quick_start" in result
    quick_start = result["quick_start"]
    assert isinstance(quick_start, dict)
    assert "1_choose_base" in quick_start

    # New enhanced fields
    assert "templates" in result
    templates = result["templates"]
    assert isinstance(templates, dict)
    assert templates["component"] == "{token}_component_of"
    assert templates["object"] == "of_{token}"
    assert templates["position"] == "at_{token}"
    assert templates["coordinate"] == "{token}"  # No template - token used as-is
    assert templates["subject"] == "{token}"  # No template - token used as-is

    assert "segment_usage" in result
    segment_usage = result["segment_usage"]
    assert isinstance(segment_usage, dict)
    assert "component" in segment_usage
    assert "guidance" in segment_usage["component"]
    assert "template" in segment_usage["component"]
    assert "vocabulary_size" in segment_usage["component"]

    assert "base_requirements" in result
    base_reqs = result["base_requirements"]
    assert "geometric_base" in base_reqs
    assert "physical_base" in base_reqs
    assert "choice" in base_reqs

    assert "vocabulary_token_counts" in result
    token_counts = result["vocabulary_token_counts"]
    assert isinstance(token_counts, dict)
    assert token_counts["component"] > 0


def test_overview_full_section(sample_catalog):
    """Test that section='all' returns complete grammar structure."""
    tool = NamingGrammarTool()

    # With section='all', should return full structure
    result = asyncio.run(tool.get_naming_grammar(section="all"))

    # Check grammar_structure section (should be in full output)
    assert "grammar_structure" in result
    grammar = result["grammar_structure"]
    assert "canonical_pattern" in grammar
    assert "segment_order" in grammar
    assert "segments" in grammar
    assert isinstance(grammar["segments"], list)
    assert len(grammar["segments"]) > 0

    # Check vocabulary section
    assert "vocabulary" in result
    vocab = result["vocabulary"]
    assert "component" in vocab
    assert "subject" in vocab
    assert "position" in vocab
    assert "geometry" in vocab  # Separate segments
    assert "process" in vocab

    # Check that vocabulary items have expected structure
    assert "template" in vocab["component"]
    assert vocab["component"]["template"] == "{token}_component_of"
    assert "tokens" in vocab["component"]
    assert isinstance(vocab["component"]["tokens"], list)

    # Check position and geometry are separate with different templates
    assert "template" in vocab["position"]
    assert "template" in vocab["geometry"]
    assert vocab["position"]["template"] == "at_{token}"
    assert vocab["geometry"]["template"] == "of_{token}"

    # Check mutually_exclusive flag if present
    if "mutually_exclusive" in vocab["position"]:
        assert vocab["position"]["mutually_exclusive"] is True

    # Check validation_rules section
    assert "validation_rules" in result
    val_rules = result["validation_rules"]
    assert "base_pattern" in val_rules
    assert "base_required" in val_rules
    assert "exclusivity_constraints" in val_rules
    assert isinstance(val_rules["exclusivity_constraints"], list)

    # Verify catalog stats are NOT included (grammar tool no longer has catalog dependency)
    assert "catalog_stats" not in result
    assert "total_standard_names" not in result
    assert "standard_names_by_kind" not in result

    # Version present
    assert "version" in result and isinstance(result["version"], str)


def test_overview_specific_sections(sample_catalog):
    """Test that specific section parameters return focused content."""
    tool = NamingGrammarTool()

    # Test segments section
    result = asyncio.run(tool.get_naming_grammar(section="segments"))
    assert "section" in result
    assert result["section"] == "segments"
    assert "vocabulary" in result
    vocab = result["vocabulary"]
    assert "component" in vocab
    assert "physical_base" in vocab

    # Test rules section
    result = asyncio.run(tool.get_naming_grammar(section="rules"))
    assert "section" in result
    assert result["section"] == "rules"
    assert "validation_rules" in result
    assert result["validation_rules"]["base_required"] is True

    # Test examples section
    result = asyncio.run(tool.get_naming_grammar(section="examples"))
    assert "section" in result
    assert result["section"] == "examples"
    assert "composition_examples" in result
    assert isinstance(result["composition_examples"], dict)
