from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.overview import OverviewTool


def test_overview_structure(sample_catalog):
    repo = sample_catalog
    tool = OverviewTool(repo)
    # call directly (sync wrapper of async not needed if we just run loop)
    import asyncio

    result = asyncio.run(tool.get_grammar_and_vocabulary())

    # Check grammar_structure section (new, should be first)
    assert "grammar_structure" in result
    grammar = result["grammar_structure"]
    assert "canonical_pattern" in grammar
    assert "segment_order" in grammar
    assert "segments" in grammar
    assert isinstance(grammar["segments"], list)
    assert len(grammar["segments"]) > 0

    # Verify canonical pattern matches grammar.yml
    expected_pattern = (
        "[<component>_component_of | <coordinate>]? [<subject>]? "
        "[<geometric_base> | <physical_base>]? "
        "[of_<object> | from_<source>]? [of_<geometry> | at_<position>]? [due_to_<process>]?"
    )
    assert grammar["canonical_pattern"] == expected_pattern

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

    # Check validation_rules section (new)
    assert "validation_rules" in result
    val_rules = result["validation_rules"]
    assert "base_pattern" in val_rules
    assert "base_required" in val_rules
    assert "exclusivity_constraints" in val_rules
    assert isinstance(val_rules["exclusivity_constraints"], list)

    # Check composition_examples section (new, improved)
    assert "composition_examples" in result
    examples = result["composition_examples"]
    assert isinstance(examples, list)
    assert len(examples) > 0
    # Check that examples have the right structure
    for example in examples:
        assert "name" in example
        assert "parts" in example
        assert "template_expansion" in example

    # Check catalog stats section
    assert "catalog_stats" in result
    stats = result["catalog_stats"]
    assert "total_standard_names" in stats and stats["total_standard_names"] == len(
        repo
    )
    assert stats["total_standard_names"] > 0

    expected_kinds = {"scalar", "vector"}
    assert set(stats["standard_names_by_kind"]) == expected_kinds
    assert (
        sum(stats["standard_names_by_kind"].values()) == stats["total_standard_names"]
    )

    expected_status = {"draft", "active", "deprecated", "superseded"}
    assert set(stats["standard_names_by_status"]) == expected_status
    assert (
        sum(stats["standard_names_by_status"].values()) == stats["total_standard_names"]
    )

    # Unit mapping: at least one unit key and dimensionless may appear
    assert "standard_names_by_unit" in stats and isinstance(
        stats["standard_names_by_unit"], dict
    )

    # Tags aggregation present (may be empty dict)
    assert "standard_names_by_tag" in stats
    assert isinstance(stats["standard_names_by_tag"], dict)

    # Version present
    assert "version" in result and isinstance(result["version"], str)
