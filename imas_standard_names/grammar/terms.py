"""Governed grammar terms, distinct from complete standard names."""

from collections.abc import Iterator
from functools import lru_cache

from pydantic import BaseModel, Field

from imas_standard_names.grammar.ir import (
    BaseKind,
    LocusType,
    OperatorApplication,
    ProjectionShape,
    StandardNameIR,
)
from imas_standard_names.grammar.parser import parse
from imas_standard_names.grammar.vocab_loaders import (
    ConventionsRegistry,
    _vocabulary_definitions as _load_vocabulary_definitions,
    load_aggregations,
    load_conventions,
    load_geometry_carriers,
    load_geometry_representations,
    load_locus_registry,
    load_orbits,
    load_populations,
    load_section_planes,
    load_states,
    load_subjects,
    load_zones,
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


# ---------------------------------------------------------------------------
# Conventions selected from a parsed name
# ---------------------------------------------------------------------------


class ConceptSymbolUse(BaseModel, frozen=True):
    """One symbol used by an applied concept."""

    symbol: str
    meaning: str


class AppliedConcept(BaseModel, frozen=True):
    """A shared concept that applies to a name, with its definition resolved."""

    token: str
    phrase: str
    definition: str = ""
    equation: str
    symbols: tuple[ConceptSymbolUse, ...] = ()
    forbidden_variants: tuple[str, ...] = ()
    restates_equation: bool


class AppliedNotation(BaseModel, frozen=True):
    """The notation entry for a token appearing in a name."""

    token: str
    symbol: str
    parameters: tuple[tuple[str, str], ...] = ()
    forbidden_spellings: tuple[str, ...] = ()


class AppliedTemplate(BaseModel, frozen=True):
    """The description/documentation template matching a name's pattern."""

    base: str
    segments: tuple[str, ...]
    description: str
    documentation: str


class AppliedConventions(BaseModel, frozen=True):
    """The convention entries that apply to one parsed name."""

    concepts: tuple[AppliedConcept, ...] = ()
    notation: tuple[AppliedNotation, ...] = ()
    templates: tuple[AppliedTemplate, ...] = ()


@lru_cache(maxsize=1)
def _segment_vocabularies() -> dict[str, frozenset[str]]:
    """Segment kind → the tokens that fill it, for segment classification."""
    return {
        "subject": load_subjects(),
        "zone": frozenset(load_zones()),
        "population": load_populations(),
        "orbit": load_orbits(),
        "state": load_states(),
        "aggregation": load_aggregations(),
        "section_plane": load_section_planes(),
        "geometry_representation": load_geometry_representations(),
    }


@lru_cache(maxsize=1)
def _vocabulary_definitions() -> dict[str, str]:
    return _load_vocabulary_definitions()


def _iter_operators(
    operators: list[OperatorApplication],
) -> Iterator[OperatorApplication]:
    for operator in operators:
        yield operator
        for argument in operator.args:
            yield from _iter_operators(argument.operators)


def _qualifier_segment_kind(token: str) -> str:
    for kind, tokens in _segment_vocabularies().items():
        if token in tokens:
            return kind
    return "qualifier"


def _locus_segment_kind(locus_type: LocusType) -> str:
    return {
        LocusType.ENTITY: "object",
        LocusType.POSITION: "position",
        LocusType.GEOMETRY: "geometry",
        LocusType.REGION: "region",
    }[locus_type]


def _ir_tokens(ir: StandardNameIR) -> frozenset[str]:
    """Every grammar token named by the parse of a name."""
    tokens: set[str] = {operator.op for operator in _iter_operators(ir.operators)}
    tokens |= {qualifier.token for qualifier in ir.qualifiers}
    tokens.add(ir.base.token)
    if ir.projection is not None:
        tokens.add(ir.projection.axis)
    if ir.locus is not None:
        tokens.add(ir.locus.token)
        tokens |= set(ir.locus.qualifiers)
    if ir.mechanism is not None:
        tokens.add(ir.mechanism.token)
    return frozenset(tokens)


def _ir_segments(ir: StandardNameIR) -> frozenset[str]:
    """The segment kinds the parse of a name fills."""
    kinds: set[str] = set()
    if ir.operators:
        kinds.add("transformation")
    if ir.projection is not None:
        kinds.add(
            "component"
            if ir.projection.shape is ProjectionShape.COMPONENT
            else "coordinate"
        )
    kinds.update(_qualifier_segment_kind(q.token) for q in ir.qualifiers)
    kinds.add(
        "physical_base" if ir.base.kind is BaseKind.QUANTITY else "geometric_base"
    )
    if ir.locus is not None:
        kinds.add(_locus_segment_kind(ir.locus.type))
    if ir.mechanism is not None:
        kinds.add("process")
    return frozenset(kinds)


def select_conventions(
    name: str, *, registry: ConventionsRegistry | None = None
) -> AppliedConventions:
    """Return the convention entries that apply to ``name``.

    ``name`` is parsed with the public grammar parser and the entries are
    selected from the parse — never by a text search. A concept entry for a
    token whose vocabulary entry carries a definition returns that definition,
    so there is one definition per token.
    """
    ir = parse(name, strict=True).ir
    conventions = registry or load_conventions()
    tokens = _ir_tokens(ir)
    segments = _ir_segments(ir)
    definitions = _vocabulary_definitions()

    concepts = tuple(
        AppliedConcept(
            token=token,
            phrase=entry.phrase,
            definition=entry.definition or definitions.get(token, ""),
            equation=entry.equation,
            symbols=tuple(
                ConceptSymbolUse(symbol=s.symbol, meaning=s.meaning)
                for s in entry.symbols
            ),
            forbidden_variants=tuple(entry.forbidden_variants),
            restates_equation=entry.restates_equation,
        )
        for token, entry in sorted(conventions.concepts.concepts.items())
        if token in tokens
    )
    notation = tuple(
        AppliedNotation(
            token=token,
            symbol=entry.symbol,
            parameters=tuple(sorted(entry.parameters.items())),
            forbidden_spellings=tuple(entry.forbidden_spellings),
        )
        for token, entry in sorted(conventions.notation.notation.items())
        if token in tokens
    )
    templates = tuple(
        AppliedTemplate(
            base=entry.base,
            segments=tuple(entry.segments),
            description=entry.description,
            documentation=entry.documentation,
        )
        for entry in conventions.templates.templates
        if entry.base == ir.base.token and set(entry.segments) <= segments
    )
    return AppliedConventions(concepts=concepts, notation=notation, templates=templates)
