"""The `state` segment tokens must not collide with any other segment.

The general cross-segment uniqueness lint (``test_vocab_uniqueness.py``)
already scans every ``vocabularies/*.yml``; this module pins the guarantee
for the state segment specifically, so a future edit that reintroduces a
``charge_state`` / ``internal_state`` token into another vocabulary (the
exact collision that a stale locus caused when the segment was added) fails
loudly with a state-focused message rather than as one line in the global
lint.

A token that resolves to two segments would give one spelling two parses and
break the greedy longest-prefix / canonical-one-spelling contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from imas_standard_names.grammar.vocab_loaders import load_states

_VOCAB_DIR = (
    Path(__file__).parents[2] / "imas_standard_names" / "grammar" / "vocabularies"
)

# Vocabularies that are intentionally NOT token-defining segment sets
# (mirrors the skip set in test_vocab_uniqueness.py) plus states.yml itself.
_SKIP = {
    "qualifier_categories.yml",
    "scoping_qualifiers.yml",
    "states.yml",
}

# Documented, permitted edge cases: (state_token, other_vocab_file). Empty by
# design — no state token is allowed to double-register. Add an entry ONLY
# with a written rationale, never to silence a real collision.
_ALLOWED_EDGE_CASES: set[tuple[str, str]] = set()


def _tokens_of(path: Path) -> set[str]:
    data = yaml.safe_load(path.read_text())
    tokens: set[str] = set()
    if isinstance(data, list):
        tokens.update(str(item) for item in data if item)
    elif isinstance(data, dict):
        for value in data.values():
            if isinstance(value, dict):
                tokens.update(value.keys())
    return tokens


def test_state_tokens_are_the_expected_two() -> None:
    assert load_states() == {"charge_state", "internal_state"}


@pytest.mark.parametrize(
    "vocab_file",
    [p.name for p in sorted(_VOCAB_DIR.glob("*.yml")) if p.name not in _SKIP],
)
def test_state_tokens_disjoint_from_other_segment(vocab_file: str) -> None:
    state_tokens = set(load_states())
    other = _tokens_of(_VOCAB_DIR / vocab_file)
    overlap = {
        tok
        for tok in state_tokens & other
        if (tok, vocab_file) not in _ALLOWED_EDGE_CASES
    }
    assert not overlap, (
        f"state token(s) {sorted(overlap)} also defined in {vocab_file}; "
        "a token must resolve to exactly one segment. Remove it from the other "
        "vocabulary (as the vestigial charge_state locus was), or — only with a "
        "written rationale — add (token, file) to _ALLOWED_EDGE_CASES."
    )
