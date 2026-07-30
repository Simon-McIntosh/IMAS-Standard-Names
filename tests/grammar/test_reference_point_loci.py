"""Reference-point loci stay limited to reusable geometric positions."""

import pytest

from imas_standard_names import ParseError, compose, get_grammar_context, parse
from imas_standard_names.grammar.vocab_loaders import load_locus_registry


def test_oblique_storage_reference_point_is_not_registered() -> None:
    registry = load_locus_registry()
    assert "oblique_reference_point" not in registry.loci

    grammar = get_grammar_context()["grammar"]
    assert "oblique_reference_point" not in grammar["vocabularies"]["locus_registry"]

    aliases = grammar["advisory_aliases"].get("position", {})
    assert "oblique_reference_point" not in aliases
    assert all(
        alias["canonical"] != "oblique_reference_point" for alias in aliases.values()
    )


def test_oblique_storage_reference_point_is_not_a_valid_locus() -> None:
    with pytest.raises(ParseError):
        parse("radial_coordinate_at_oblique_reference_point", strict=True)


@pytest.mark.parametrize(
    "name",
    [
        "radial_coordinate_at_rectangle_center",
        "radial_coordinate_at_annulus_center",
        "radial_coordinate_of_ferritic_element",
    ],
)
def test_reusable_reference_and_entity_loci_remain_valid(name: str) -> None:
    assert compose(parse(name, strict=True).ir) == name
