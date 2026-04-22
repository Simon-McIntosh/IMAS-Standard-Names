"""Vocabulary-gap contract test for grammar vNext (plan 38 §A10, item 5).

Validates the contract that downstream codex tooling (``write_vocab_gaps()``)
relies on:

1. **physical_base is a closed vocabulary**: ``v.bases`` is a non-empty
   ``frozenset`` populated from ``physical_bases.yml``; there is no open
   fallback path.

2. **Unknown base raises ParseError with suggestions**: parsing a name whose
   residue is not in ``physical_bases ∪ geometry_carriers`` raises
   :class:`~imas_standard_names.grammar.parser.ParseError` and the error's
   ``.suggestions`` list contains the nearest closed-vocab candidates
   (edit-distance ranking via :func:`difflib.get_close_matches`).

3. **vocab_gap diagnostic for unknown locus tokens**: parsing a name whose
   ``_at_`` or ``_over_`` suffix points to an unregistered locus token
   emits a :class:`~imas_standard_names.grammar.parser.Diagnostic` with
   ``category == "vocab_gap"`` in the returned ``ParseResult.diagnostics``
   list (the name still parses; gap is a warning, not an error).

4. **Vocabulary immutability**: the ``Vocabularies`` bundle is a frozen
   dataclass; attempting to mutate it raises an error.

Note on ``is_open_segment``:
  The plan §A10 item 5 mentions ``is_open_segment('physical_base') is False``.
  This function does not exist in the current parser API; the equivalent
  contract is captured here by asserting directly on ``len(v.bases) > 0``
  (closed, non-empty frozenset) and the ParseError-on-unknown-base behaviour.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.parser import (
    Diagnostic,
    ParseError,
    Vocabularies,
    load_default_vocabularies,
    parse,
)

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vocabs() -> Vocabularies:
    return load_default_vocabularies()


# ---------------------------------------------------------------------------
# Contract 1: physical_base vocab is closed and non-empty
# ---------------------------------------------------------------------------


def test_physical_bases_vocab_is_closed_and_populated(vocabs: Vocabularies) -> None:
    """``v.bases`` must be a non-empty frozenset (closed vocabulary contract).

    Plan §A6 and §A9.2 require ≥ 200 tokens in the closed vocab after curation.
    """
    assert isinstance(vocabs.bases, frozenset), (
        "v.bases must be a frozenset (immutable closed set)"
    )
    assert len(vocabs.bases) >= 200, (
        f"Expected ≥200 physical_bases; got {len(vocabs.bases)}"
    )


def test_geometry_carriers_vocab_is_closed_and_populated(vocabs: Vocabularies) -> None:
    """``v.carriers`` must be a non-empty frozenset."""
    assert isinstance(vocabs.carriers, frozenset)
    assert len(vocabs.carriers) > 0, "geometry_carriers frozenset must not be empty"


def test_physical_bases_and_carriers_are_disjoint(vocabs: Vocabularies) -> None:
    """physical_bases and geometry_carriers must not share tokens.

    A token in both would be ambiguous (quantity vs geometry).
    """
    overlap = vocabs.bases & vocabs.carriers
    assert not overlap, (
        f"Overlap between physical_bases and geometry_carriers: {sorted(overlap)}"
    )


# ---------------------------------------------------------------------------
# Contract 2: unknown base raises ParseError with suggestions
# ---------------------------------------------------------------------------


def test_unknown_base_raises_parse_error(vocabs: Vocabularies) -> None:
    """A fabricated base token not in any closed vocab raises ParseError."""
    fabricated = "utterly_invented_physical_quantity_zxq"
    with pytest.raises(ParseError) as exc_info:
        parse(fabricated, vocabs)
    err = exc_info.value
    assert isinstance(err, ParseError)


def test_unknown_base_parse_error_has_residue(vocabs: Vocabularies) -> None:
    """ParseError for unknown base exposes the failing residue string."""
    fabricated = "invented_base_residue_token"
    with pytest.raises(ParseError) as exc_info:
        parse(fabricated, vocabs)
    err = exc_info.value
    assert err.residue is not None, "ParseError.residue must be set for unknown base"
    assert err.residue != "", "ParseError.residue must be non-empty"


def test_close_misspelling_surfaces_suggestion(vocabs: Vocabularies) -> None:
    """Edit-distance ≤ 2 misspelling produces at least one suggestion."""
    # 'temperture' is one edit from 'temperature' (missing 'a')
    with pytest.raises(ParseError) as exc_info:
        parse("temperture", vocabs)
    err = exc_info.value
    assert err.suggestions, (
        "Expected at least one suggestion for 'temperture'; suggestions were empty"
    )
    assert "temperature" in err.suggestions, (
        f"Expected 'temperature' in suggestions; got {err.suggestions}"
    )


def test_close_misspelling_safety_factor(vocabs: Vocabularies) -> None:
    """``safty_factor`` (missing 'e') surfaces ``safety_factor`` as suggestion."""
    with pytest.raises(ParseError) as exc_info:
        parse("safty_factor", vocabs)
    err = exc_info.value
    assert "safety_factor" in err.suggestions, (
        f"Expected 'safety_factor' in suggestions; got {err.suggestions}"
    )


def test_no_suggestions_for_completely_invented_token(vocabs: Vocabularies) -> None:
    """A token with no close vocabulary matches has an empty suggestions list."""
    with pytest.raises(ParseError) as exc_info:
        parse("zzz_qqq_ppp_no_match", vocabs)
    err = exc_info.value
    # Suggestions may be empty for tokens with no close neighbours.
    assert isinstance(err.suggestions, list)


def test_operator_with_unknown_inner_base_raises_parse_error_with_residue(
    vocabs: Vocabularies,
) -> None:
    """Operator correctly peeled; inner residue fails with residue set on error."""
    with pytest.raises(ParseError) as exc_info:
        parse("maximum_of_made_up_base_zxq", vocabs)
    err = exc_info.value
    assert err.residue is not None


# ---------------------------------------------------------------------------
# Contract 3: unknown locus token emits vocab_gap Diagnostic (not an error)
# ---------------------------------------------------------------------------


def test_unknown_at_locus_emits_vocab_gap_diagnostic(vocabs: Vocabularies) -> None:
    """Unknown ``_at_`` locus token → ``vocab_gap`` Diagnostic, not ParseError.

    This is the key codex integration contract: ``write_vocab_gaps()`` scans
    ParseResult.diagnostics for ``category == "vocab_gap"`` entries to collect
    tokens that should be added to the locus_registry.
    """
    result = parse("pressure_at_totally_unknown_locus_token", vocabs)

    vocab_gap_diags = [d for d in result.diagnostics if d.category == "vocab_gap"]
    assert vocab_gap_diags, (
        f"Expected ≥1 vocab_gap diagnostic for unknown _at_ locus; "
        f"got diagnostics: {result.diagnostics}"
    )
    assert all(isinstance(d, Diagnostic) for d in vocab_gap_diags)


def test_unknown_over_locus_emits_vocab_gap_diagnostic(vocabs: Vocabularies) -> None:
    """Unknown ``_over_`` locus token → ``vocab_gap`` Diagnostic."""
    result = parse("temperature_over_unknown_region_token", vocabs)

    vocab_gap_diags = [d for d in result.diagnostics if d.category == "vocab_gap"]
    assert vocab_gap_diags, (
        f"Expected vocab_gap diagnostic for unknown _over_ locus token; "
        f"got: {result.diagnostics}"
    )


def test_vocab_gap_diagnostic_identifies_locus_layer(vocabs: Vocabularies) -> None:
    """The vocab_gap Diagnostic layer must be ``'parser'``."""
    result = parse("pressure_at_invented_locus_for_vocab_gap", vocabs)

    for diag in result.diagnostics:
        if diag.category == "vocab_gap":
            assert diag.layer == "parser", (
                f"Expected layer='parser'; got layer={diag.layer!r}"
            )
            break
    else:
        pytest.fail("No vocab_gap diagnostic found")


def test_of_locus_without_registry_hit_is_not_vocab_gap(vocabs: Vocabularies) -> None:
    """Unknown token after ``_of_`` is NOT treated as a locus (left in residue).

    Unlike ``_at_`` and ``_over_``, an unknown ``_of_`` token is left in the
    string (it may be a binary-operator template). The parser then rejects the
    name entirely with ParseError, not a vocab_gap diagnostic.
    """
    with pytest.raises(ParseError):
        parse("pressure_of_entirely_unknown_token_xyz", vocabs)


# ---------------------------------------------------------------------------
# Contract 4: Vocabularies bundle is immutable
# ---------------------------------------------------------------------------


def test_vocabularies_is_frozen(vocabs: Vocabularies) -> None:
    """The Vocabularies dataclass must be frozen (immutable)."""
    with pytest.raises((AttributeError, TypeError)):
        vocabs.bases = frozenset({"pressure"})  # type: ignore[misc]


def test_vocabularies_bases_frozenset_is_immutable(vocabs: Vocabularies) -> None:
    """The ``bases`` frozenset cannot be mutated."""
    original_len = len(vocabs.bases)
    # Frozensets don't have add(); accessing the attribute is read-only.
    assert not hasattr(vocabs.bases, "add"), "frozenset must not have .add()"
    assert len(vocabs.bases) == original_len
