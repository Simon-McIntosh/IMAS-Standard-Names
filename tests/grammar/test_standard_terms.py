from imas_standard_names.grammar import (
    fetch_standard_terms,
    search_standard_terms,
    standard_terms,
)
from imas_standard_names.grammar.constants import SEGMENT_TOKEN_MAP
from imas_standard_names.grammar.vocab_loaders import (
    load_geometry_carriers,
    load_locus_registry,
)


def test_every_locus_has_one_governed_definition() -> None:
    registry = load_locus_registry()
    terms = [term for term in standard_terms() if term.segment == "locus"]
    assert {term.token for term in terms} == set(registry.loci)
    assert all(term.definition.strip() for term in terms)


def test_defined_geometry_carriers_are_governed_terms() -> None:
    carriers = load_geometry_carriers().carriers
    expected = {token for token, entry in carriers.items() if entry.definition}
    actual = {
        term.token for term in standard_terms() if term.segment == "geometric_base"
    }
    assert actual == expected


def test_local_frame_terms_preserve_dd_orientation_semantics() -> None:
    first = fetch_standard_terms("first_local_tangential_unit_vector")[0]
    second = fetch_standard_terms("second_local_tangential_unit_vector")[0]

    assert "positive toroidal phi" in first.definition
    assert "horizontal" in first.definition
    assert "e2 = e3 x e1" in second.definition
    assert "not necessarily vertical" in second.definition
    assert "not necessarily a principal-curvature direction" in second.definition


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
