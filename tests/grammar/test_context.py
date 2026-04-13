"""Tests for imas_standard_names.grammar.context module."""

import pytest

from imas_standard_names.grammar.context import get_grammar_context


@pytest.fixture(scope="module")
def context() -> dict:
    """Load grammar context once for the entire test module."""
    return get_grammar_context()


# ---------- Top-level key presence ----------


EXPECTED_KEYS = [
    "canonical_pattern",
    "segment_order",
    "template_rules",
    "exclusive_pairs",
    "vocabulary_sections",
    "segment_descriptions",
    "naming_guidance",
    "documentation_guidance",
    "kind_definitions",
    "anti_patterns",
    "tag_descriptions",
    "applicability",
    "field_guidance",
    "type_specific_requirements",
    "quick_start",
    "common_patterns",
    "critical_distinctions",
    "base_requirements",
    "vocabulary_usage_stats",
]


def test_all_keys_present(context: dict):
    missing = set(EXPECTED_KEYS) - set(context.keys())
    assert not missing, f"Missing keys: {missing}"


# ---------- Type checks ----------


def test_canonical_pattern_is_nonempty_str(context: dict):
    assert isinstance(context["canonical_pattern"], str)
    assert len(context["canonical_pattern"]) > 0


def test_segment_order_is_nonempty_str(context: dict):
    assert isinstance(context["segment_order"], str)
    assert "→" in context["segment_order"]


def test_template_rules_is_nonempty_str(context: dict):
    assert isinstance(context["template_rules"], str)
    assert len(context["template_rules"]) > 0


def test_exclusive_pairs_is_list_of_pairs(context: dict):
    pairs = context["exclusive_pairs"]
    assert isinstance(pairs, list)
    assert len(pairs) > 0
    for pair in pairs:
        assert isinstance(pair, list)
        assert len(pair) == 2


def test_vocabulary_sections_is_nonempty_list(context: dict):
    sections = context["vocabulary_sections"]
    assert isinstance(sections, list)
    assert len(sections) > 0
    for section in sections:
        assert isinstance(section, dict)
        assert "segment" in section
        assert "tokens" in section


def test_segment_descriptions_is_nonempty_dict(context: dict):
    descs = context["segment_descriptions"]
    assert isinstance(descs, dict)
    assert len(descs) > 0


# ---------- Naming conventions ----------


def test_naming_guidance_is_well_formed(context: dict):
    ng = context["naming_guidance"]
    assert isinstance(ng, dict)
    assert len(ng) > 0


def test_documentation_guidance_is_well_formed(context: dict):
    dg = context["documentation_guidance"]
    assert isinstance(dg, dict)
    assert len(dg) > 0


def test_kind_definitions_contains_required_kinds(context: dict):
    kd = context["kind_definitions"]
    assert isinstance(kd, dict)
    for kind in ("scalar", "vector", "metadata"):
        assert kind in kd, f"Missing kind: {kind}"


def test_anti_patterns_is_nonempty_list_of_dicts(context: dict):
    ap = context["anti_patterns"]
    assert isinstance(ap, list)
    assert len(ap) > 0
    for item in ap:
        assert isinstance(item, dict)
        assert "mistake" in item
        assert "correction" in item


def test_tag_descriptions_has_primary_and_secondary(context: dict):
    td = context["tag_descriptions"]
    assert isinstance(td, dict)
    assert "primary" in td
    assert "secondary" in td
    assert isinstance(td["primary"], dict)
    assert isinstance(td["secondary"], dict)
    assert len(td["primary"]) > 0
    assert len(td["secondary"]) > 0


def test_applicability_has_required_keys(context: dict):
    app = context["applicability"]
    assert isinstance(app, dict)
    assert "include" in app
    assert "exclude" in app
    assert "rationale" in app
    assert isinstance(app["include"], list)
    assert isinstance(app["exclude"], list)
    assert isinstance(app["rationale"], str)


def test_field_guidance_is_nonempty_dict(context: dict):
    fg = context["field_guidance"]
    assert isinstance(fg, dict)
    assert len(fg) > 0


def test_type_specific_requirements_is_nonempty_dict(context: dict):
    tsr = context["type_specific_requirements"]
    assert isinstance(tsr, dict)
    assert len(tsr) > 0
    for kind in ("scalar", "vector", "metadata"):
        assert kind in tsr, f"Missing type-specific requirements for: {kind}"


# ---------- LLM orientation ----------


def test_quick_start_is_nonempty_str(context: dict):
    qs = context["quick_start"]
    assert isinstance(qs, str)
    assert len(qs) > 0


def test_common_patterns_is_nonempty_list(context: dict):
    cp = context["common_patterns"]
    assert isinstance(cp, list)
    assert len(cp) > 0
    for item in cp:
        assert isinstance(item, dict)
        assert "pattern" in item
        assert "formula" in item
        assert "example" in item


def test_critical_distinctions_is_nonempty_list(context: dict):
    cd = context["critical_distinctions"]
    assert isinstance(cd, list)
    assert len(cd) > 0
    for item in cd:
        assert isinstance(item, dict)
        assert "pair" in item
        assert "rule" in item


def test_base_requirements_is_dict_with_segment_keys(context: dict):
    br = context["base_requirements"]
    assert isinstance(br, dict)
    assert "geometric_base" in br
    assert "physical_base" in br
    assert "choice" in br


# ---------- Vocabulary usage stats ----------


def test_vocabulary_usage_stats_is_dict(context: dict):
    """Stats should be a dict (possibly empty if no catalog is available)."""
    stats = context["vocabulary_usage_stats"]
    assert isinstance(stats, dict)
    # If stats are populated, verify structure
    if stats:
        assert "per_segment" in stats
        assert "most_common" in stats
        assert "unused" in stats
        assert isinstance(stats["per_segment"], dict)
        assert isinstance(stats["most_common"], list)
        assert isinstance(stats["unused"], list)
