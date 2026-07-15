from imas_standard_names.grammar import (
    fetch_standard_terms,
    search_standard_terms,
    standard_terms,
)
from imas_standard_names.grammar.constants import SEGMENT_TOKEN_MAP
from imas_standard_names.grammar.vocab_loaders import load_locus_registry


def test_every_locus_has_one_governed_definition() -> None:
    registry = load_locus_registry()
    terms = standard_terms()
    assert {term.token for term in terms} == set(registry.loci)
    assert all(term.definition.strip() for term in terms)


def test_display_abbreviations_do_not_enter_parser_vocabulary() -> None:
    parser_tokens = {
        token.casefold() for tokens in SEGMENT_TOKEN_MAP.values() for token in tokens
    }
    abbreviations = {
        abbreviation.casefold()
        for term in standard_terms()
        for abbreviation in term.abbreviations
    }
    assert abbreviations.isdisjoint(parser_tokens)


def test_lcfs_and_itb_resolve_as_display_abbreviations() -> None:
    assert fetch_standard_terms("LCFS")[0].token == "last_closed_flux_surface"
    assert fetch_standard_terms("ITB")[0].token == "internal_transport_barrier"


def test_search_matches_definition_words() -> None:
    matches = search_standard_terms("outermost closed toroidally")
    assert [term.token for term in matches] == ["last_closed_flux_surface"]
