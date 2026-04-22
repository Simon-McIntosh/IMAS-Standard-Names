"""Rejection test battery for grammar vNext (plan 38 §A10, item 3).

Forms that MUST raise :class:`~imas_standard_names.grammar.parser.ParseError`
with helpful suggestions. Covers:

- Unknown base tokens (misspellings) with edit-distance ≤ 2 suggestion
- Completely fabricated base tokens
- Invalid token format (uppercase, spaces, hyphens)
- Orphan ``_of_`` without a preceding operator and unknown locus token
- Empty string input
- Names composed only of known operators with no base residue
- Tokens that look like a known qualifier alone (no base)
- Known operator applied to an empty inner expression
- Fabricated locus tokens that look close to known ones (vocab_gap diagnostic)
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
# Helpers
# ---------------------------------------------------------------------------


def _assert_parse_error(name: str, vocabs: Vocabularies) -> ParseError:
    """Assert *name* raises ParseError and return it for further assertions."""
    with pytest.raises(ParseError) as exc_info:
        parse(name, vocabs)
    return exc_info.value


def _assert_parse_error_with_suggestion(
    name: str, vocabs: Vocabularies, suggestion_fragment: str
) -> None:
    """Assert ParseError is raised and at least one suggestion contains the fragment."""
    err = _assert_parse_error(name, vocabs)
    matches = [s for s in err.suggestions if suggestion_fragment in s]
    assert matches, (
        f"Expected a suggestion containing {suggestion_fragment!r} for input {name!r}; "
        f"got suggestions: {err.suggestions}"
    )


# ---------------------------------------------------------------------------
# Group 1: Unknown base tokens — misspellings (edit distance ≤ 2)
# ---------------------------------------------------------------------------


def test_reject_misspelled_temperature(vocabs: Vocabularies) -> None:
    """``temperture`` is one edit from ``temperature``; suggestion must surface it."""
    _assert_parse_error_with_suggestion("temperture", vocabs, "temperature")


def test_reject_misspelled_pressure(vocabs: Vocabularies) -> None:
    """``preessure`` is two edits from ``pressure``."""
    _assert_parse_error("preessure", vocabs)


def test_reject_misspelled_magnetic_field(vocabs: Vocabularies) -> None:
    """``magntic_field`` is one edit from ``magnetic_field``."""
    _assert_parse_error_with_suggestion("magntic_field", vocabs, "magnetic_field")


def test_reject_misspelled_current_density(vocabs: Vocabularies) -> None:
    """``curent_density`` is one edit from ``current_density``."""
    err = _assert_parse_error("curent_density", vocabs)
    # Suggestions should be non-empty (edit-distance match).
    assert err.suggestions, f"Expected at least one suggestion; got {err.suggestions}"


def test_reject_misspelled_safety_factor(vocabs: Vocabularies) -> None:
    """``safty_factor`` is one edit from ``safety_factor``."""
    _assert_parse_error_with_suggestion("safty_factor", vocabs, "safety_factor")


# ---------------------------------------------------------------------------
# Group 2: Completely fabricated base tokens
# ---------------------------------------------------------------------------


def test_reject_fabricated_unknown_token(vocabs: Vocabularies) -> None:
    """``quantum_flux_density_xyz`` has no match in closed vocab."""
    err = _assert_parse_error("quantum_flux_density_xyz", vocabs)
    # May or may not have suggestions, but must raise.
    assert isinstance(err, ParseError)


def test_reject_single_letter_token(vocabs: Vocabularies) -> None:
    """Single-letter tokens are valid snake_case but not in any closed vocab."""
    _assert_parse_error("x", vocabs)


def test_reject_fabricated_with_plausible_prefix(vocabs: Vocabularies) -> None:
    """``electron_fictional_quantity`` — ``fictional_quantity`` not a base."""
    # qualifiers is currently empty, so the parser tries whole residue as base
    err = _assert_parse_error("electron_fictional_quantity", vocabs)
    assert isinstance(err, ParseError)


def test_reject_random_words_as_base(vocabs: Vocabularies) -> None:
    """``banana_smoothie`` has no physical meaning; must be rejected."""
    _assert_parse_error("banana_smoothie", vocabs)


# ---------------------------------------------------------------------------
# Group 3: Invalid token format
# ---------------------------------------------------------------------------


def test_reject_uppercase_token(vocabs: Vocabularies) -> None:
    """Uppercase tokens violate the snake_case requirement."""
    _assert_parse_error("Temperature", vocabs)


def test_reject_mixed_case_token(vocabs: Vocabularies) -> None:
    """Mixed-case tokens violate the format."""
    _assert_parse_error("electron_Temperature", vocabs)


def test_reject_token_with_spaces(vocabs: Vocabularies) -> None:
    """Tokens with spaces are not valid."""
    _assert_parse_error("electron temperature", vocabs)


def test_reject_empty_string(vocabs: Vocabularies) -> None:
    """Empty string must raise ParseError."""
    _assert_parse_error("", vocabs)


def test_reject_token_with_leading_underscore(vocabs: Vocabularies) -> None:
    """Leading underscore violates snake_case."""
    _assert_parse_error("_pressure", vocabs)


def test_reject_token_with_trailing_underscore(vocabs: Vocabularies) -> None:
    """Trailing underscore violates snake_case format."""
    _assert_parse_error("pressure_", vocabs)


def test_reject_token_with_double_underscore(vocabs: Vocabularies) -> None:
    """Double underscore inside token is not valid snake_case."""
    _assert_parse_error("pressure__temperature", vocabs)


# ---------------------------------------------------------------------------
# Group 4: Orphan prepositions / structural anomalies
# ---------------------------------------------------------------------------


def test_reject_orphan_of_at_start(vocabs: Vocabularies) -> None:
    """``_of_pressure`` — leading underscore sequence is invalid."""
    _assert_parse_error("_of_pressure", vocabs)


def test_reject_only_operator_no_base(vocabs: Vocabularies) -> None:
    """``maximum_of_`` has no residue after the operator prefix."""
    _assert_parse_error("maximum_of_", vocabs)


def test_reject_only_preposition_of(vocabs: Vocabularies) -> None:
    """``of`` alone is not a valid base."""
    _assert_parse_error("of", vocabs)


def test_reject_only_preposition_at(vocabs: Vocabularies) -> None:
    """``at`` alone is not a valid base."""
    _assert_parse_error("at", vocabs)


def test_reject_only_due_to(vocabs: Vocabularies) -> None:
    """``due_to`` alone is not a valid base."""
    _assert_parse_error("due_to", vocabs)


# ---------------------------------------------------------------------------
# Group 5: Fabricated locus tokens near known ones (vocab_gap diagnostic)
# ---------------------------------------------------------------------------


def test_reject_unknown_of_locus_no_registry_hit(vocabs: Vocabularies) -> None:
    """``pressure_of_foobar_locus`` — unknown ``_of_`` target not in loci registry.

    Because ``foobar_locus`` is not a registered locus, the ``_of_`` is NOT
    stripped as a locus suffix. The parser leaves it in the residue; the base
    match on ``pressure_of_foobar_locus`` then fails.
    """
    err = _assert_parse_error("pressure_of_foobar_locus", vocabs)
    assert isinstance(err, ParseError)


def test_parse_unknown_at_locus_emits_vocab_gap_diagnostic(
    vocabs: Vocabularies,
) -> None:
    """``pressure_at_invented_position`` — unknown ``_at_`` token falls back
    with a ``vocab_gap`` diagnostic; the name still parses (liberal policy).

    This is the inverse of the base-unknown case: locus gaps are warnings,
    not errors (per parser §A8 spec).
    """
    from imas_standard_names.grammar.render import compose

    result = parse("pressure_at_invented_position", vocabs)
    # Should parse successfully with a vocab_gap diagnostic
    assert any(d.category == "vocab_gap" for d in result.diagnostics), (
        f"Expected vocab_gap diagnostic; got {result.diagnostics}"
    )
    # And the composed form should round-trip
    name_out = compose(result.ir)
    result2 = parse(name_out, vocabs)
    assert result2.ir == result.ir


def test_parse_unknown_over_locus_emits_vocab_gap_diagnostic(
    vocabs: Vocabularies,
) -> None:
    """``temperature_over_some_region`` — unknown ``_over_`` token falls back
    with a ``vocab_gap`` diagnostic."""
    result = parse("temperature_over_some_region", vocabs)
    assert any(d.category == "vocab_gap" for d in result.diagnostics), (
        f"Expected vocab_gap diagnostic; got {result.diagnostics}"
    )


# ---------------------------------------------------------------------------
# Group 6: Residue is a valid base fragment but not complete
# ---------------------------------------------------------------------------


def test_reject_partial_base_compound(vocabs: Vocabularies) -> None:
    """``magnetic`` alone (partial of ``magnetic_field``) is not in vocab."""
    err = _assert_parse_error("magnetic", vocabs)
    assert isinstance(err, ParseError)


def test_reject_partial_base_density(vocabs: Vocabularies) -> None:
    """``excitation`` alone is not a physical_base token in the closed vocab."""
    err = _assert_parse_error("excitation", vocabs)
    assert isinstance(err, ParseError)


# ---------------------------------------------------------------------------
# Group 7: Operator with bad/fabricated inner base
# ---------------------------------------------------------------------------


def test_reject_operator_with_unknown_inner_base(vocabs: Vocabularies) -> None:
    """``maximum_of_foobar_quantity`` — operator correctly peeled, inner base unknown."""
    err = _assert_parse_error("maximum_of_foobar_quantity", vocabs)
    assert isinstance(err, ParseError)
    # The residue should be reported
    assert err.residue is not None, "Expected residue to be set in ParseError"


def test_reject_nested_operators_with_unknown_inner_base(vocabs: Vocabularies) -> None:
    """``maximum_of_amplitude_of_invented_base`` — two operators, bad inner residue."""
    err = _assert_parse_error("maximum_of_amplitude_of_invented_base", vocabs)
    assert isinstance(err, ParseError)
