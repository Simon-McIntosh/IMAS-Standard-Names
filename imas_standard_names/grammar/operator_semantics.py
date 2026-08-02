"""Stable semantic categories attached to authoritative operator tokens."""

import functools
from collections.abc import Mapping
from types import MappingProxyType

from imas_standard_names.grammar.vocab_loaders import load_operators

__all__ = ["get_operator_semantics"]

_EMPTY_SEMANTICS: frozenset[str] = frozenset()


@functools.lru_cache(maxsize=1)
def _semantics_by_operator() -> Mapping[str, frozenset[str]]:
    """Load one immutable view over the authoritative operator registry."""
    registry = load_operators()
    return MappingProxyType(
        {
            token: frozenset(definition.semantic_effects)
            for token, definition in registry.operators.items()
        }
    )


def get_operator_semantics(token: str) -> frozenset[str]:
    """Return stable semantic effects for an operator token.

    Lookup is based only on the token, so it applies equally when parsing
    represents a bare-prefix operator as a qualifier. Unknown tokens and
    registered operators without semantic effects return an empty frozenset.
    """
    return _semantics_by_operator().get(token, _EMPTY_SEMANTICS)
