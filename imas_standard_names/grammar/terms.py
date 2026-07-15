"""Governed grammar terms, distinct from complete standard names."""

from pydantic import BaseModel, Field

from imas_standard_names.grammar.vocab_loaders import (
    load_geometry_carriers,
    load_locus_registry,
)


class StandardTerm(BaseModel, frozen=True):
    """A normative compositional term used by the standard-name grammar."""

    token: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    segment: str
    definition: str = Field(min_length=20)
    abbreviations: tuple[str, ...] = ()
    allowed_relations: tuple[str, ...] = ()
    references: tuple[str, ...] = ()


def standard_terms() -> tuple[StandardTerm, ...]:
    """Return the governed term collection in deterministic token order."""
    registry = load_locus_registry()
    terms = [
        StandardTerm(
            token=token,
            segment="locus",
            definition=entry.definition,
            abbreviations=tuple(entry.abbreviations),
            allowed_relations=tuple(entry.allowed_relations),
            references=tuple(entry.references),
        )
        for token, entry in sorted(registry.loci.items())
    ]
    carriers = load_geometry_carriers()
    terms.extend(
        StandardTerm(
            token=token,
            segment="geometric_base",
            definition=entry.definition,
        )
        for token, entry in sorted(carriers.carriers.items())
        if entry.definition
    )
    return tuple(sorted(terms, key=lambda term: (term.token, term.segment)))


def fetch_standard_terms(
    tokens: list[str] | tuple[str, ...] | str,
) -> tuple[StandardTerm, ...]:
    """Fetch exact governed terms by canonical token or abbreviation."""
    requested = [tokens] if isinstance(tokens, str) else list(tokens)
    wanted = {item.casefold() for item in requested}
    return tuple(
        term
        for term in standard_terms()
        if term.token.casefold() in wanted
        or any(abbreviation.casefold() in wanted for abbreviation in term.abbreviations)
    )


def search_standard_terms(
    query: str, *, segment: str | None = None
) -> tuple[StandardTerm, ...]:
    """Search governed terms across token, definition, and abbreviations."""
    words = tuple(word for word in query.casefold().replace("_", " ").split() if word)
    matches: list[StandardTerm] = []
    for term in standard_terms():
        if segment is not None and term.segment != segment:
            continue
        haystack = " ".join(
            (term.token.replace("_", " "), term.definition, *term.abbreviations)
        ).casefold()
        if all(word in haystack for word in words):
            matches.append(term)
    return tuple(matches)
