"""Bind the three binary-operator source-of-truth files so they cannot drift.

Binary operators are described in three places, each consumed for a different
purpose:

* ``operators.yml`` (``kind: binary`` entries) — the operator *semantics*:
  precedence and the ``separator`` word joining the two operands.
* ``binary_operators.yml`` — the ``_of``-suffixed surface tokens that seed the
  ``BinaryOperator`` enum and ``BINARY_OPERATOR_TOKENS``.
* ``specification.yml`` (``binary_operator_connectors``) — the connector word
  the renderer places between the operands.

Each ``kind: binary`` operator ``<op>`` in ``operators.yml`` corresponds to the
surface token ``<op>_of``, and its ``separator`` (``_and_`` / ``_to_``) is the
connector word with the surrounding underscores stripped (``and`` / ``to``).
These tests assert that correspondence so an edit to one file that is not
mirrored in the others fails loudly instead of desynchronising the grammar.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from imas_standard_names.grammar_codegen.spec import GrammarSpec

_VOCAB = (
    Path(__file__).resolve().parents[1]
    / "imas_standard_names"
    / "grammar"
    / "vocabularies"
)


def _binary_operator_semantics() -> dict[str, str]:
    """Bare binary operator token -> separator, read from operators.yml."""
    data = yaml.safe_load((_VOCAB / "operators.yml").read_text(encoding="utf-8"))
    return {
        token: entry["separator"]
        for token, entry in data["operators"].items()
        if isinstance(entry, dict) and entry.get("kind") == "binary"
    }


def _surface_tokens() -> set[str]:
    """The ``_of``-suffixed tokens from binary_operators.yml."""
    data = yaml.safe_load((_VOCAB / "binary_operators.yml").read_text(encoding="utf-8"))
    return {token for token in data if isinstance(token, str)}


def _connectors() -> dict[str, str]:
    """binary_operator_connectors from specification.yml.

    Loaded through GrammarSpec so the ``!include`` tags resolve exactly as the
    codegen sees them.
    """
    return dict(GrammarSpec.load().binary_operator_connectors or {})


def test_surface_tokens_match_binary_semantics():
    """Each kind:binary operator <op> must surface as exactly <op>_of."""
    expected = {f"{op}_of" for op in _binary_operator_semantics()}
    assert _surface_tokens() == expected


def test_connectors_cover_exactly_the_surface_tokens():
    """The connector map keys must equal the surface tokens."""
    assert set(_connectors()) == _surface_tokens()


def test_connector_word_equals_separator_stripped():
    """Each connector word is the operator separator without underscores."""
    semantics = _binary_operator_semantics()
    connectors = _connectors()
    for op, separator in semantics.items():
        token = f"{op}_of"
        assert connectors[token] == separator.strip("_"), (
            f"connector for '{token}' ({connectors[token]!r}) disagrees with the "
            f"operators.yml separator {separator!r} for '{op}'"
        )
