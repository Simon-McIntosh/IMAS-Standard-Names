"""Qualifier category coverage invariant.

``qualifier_categories.yml`` groups every ``qualifiers.yml`` token under exactly
one normalized presentation category (consumed by the catalog dataset emitter
and the IR's ``Qualifier.category``). These tests enforce that the two files
stay in lock-step so a token can never be added to one without the other.
"""

from __future__ import annotations

from imas_standard_names.grammar import vocab_loaders

# The closed set of normalized categories (see qualifier_categories.yml).
EXPECTED_CATEGORIES = {
    "transport",
    "source",
    "geometry",
    "region",
    "state",
    "energy",
    "diagnostic",
    "polarization",
    "temporal",
    "normalized",
    "species",
    "engineering",
}


def test_every_qualifier_has_exactly_one_category() -> None:
    qualifiers = set(vocab_loaders.load_qualifiers())
    categories = vocab_loaders.load_qualifier_categories()

    uncategorized = qualifiers - set(categories)
    assert not uncategorized, (
        f"qualifiers.yml tokens missing from qualifier_categories.yml: "
        f"{sorted(uncategorized)}"
    )


def test_no_category_token_is_absent_from_qualifiers() -> None:
    qualifiers = set(vocab_loaders.load_qualifiers())
    categories = vocab_loaders.load_qualifier_categories()

    extra = set(categories) - qualifiers
    assert not extra, (
        f"qualifier_categories.yml lists tokens not in qualifiers.yml: {sorted(extra)}"
    )


def test_categories_are_from_the_normalized_set() -> None:
    used = set(vocab_loaders.load_qualifier_categories().values())
    assert used <= EXPECTED_CATEGORIES, (
        f"unexpected categories: {used - EXPECTED_CATEGORIES}"
    )


def test_ir_qualifier_carries_its_category() -> None:
    """The parser populates IR Qualifier.category from the map."""
    from imas_standard_names.grammar.parser import parse

    ir = parse("major_radius_of_flux_loop").ir
    by_token = {q.token: q.category for q in ir.qualifiers}
    assert by_token.get("major") == "geometry"
