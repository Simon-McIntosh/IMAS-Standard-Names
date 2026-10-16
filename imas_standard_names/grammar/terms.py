"""Governed grammar terms, distinct from complete standard names."""

from collections.abc import Iterator
from functools import lru_cache

from pydantic import BaseModel, Field

from imas_standard_names.grammar.ir import (
    BaseKind,
    LocusType,
    OperatorApplication,
    OperatorKind,
    ProjectionShape,
    StandardNameIR,
)
from imas_standard_names.grammar.model import _split_fused_indexed_operator
from imas_standard_names.grammar.parser import parse
from imas_standard_names.grammar.vocab_loaders import (
    ConventionsRegistry,
    TemplateEntry,
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


_DEFINITION_SEGMENTS: frozenset[str] = frozenset({"population", "zone", "aggregation"})


class AppliedDefinition(BaseModel, frozen=True):
    """A definition carried by a vocabulary token in a name.

    A population, zone or aggregation token states what it means but names no
    shared phrase or equation, so it applies as a definition alone rather than
    as an ``AppliedConcept``, whose phrase and equation a token definition does
    not have.
    """

    token: str
    segment: str
    definition: str


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
    note: str = ""


class AppliedConventions(BaseModel, frozen=True):
    """The convention entries that apply to one parsed name."""

    concepts: tuple[AppliedConcept, ...] = ()
    definitions: tuple[AppliedDefinition, ...] = ()
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


def _operator_token(operator: OperatorApplication) -> str:
    """Resolve a fused indexed application to its registered operator key.

    The model owns the split of a fused indexed token into its base operator
    and coordinate index, so the accessor asks it rather than re-deriving the
    boundary against a second copy of the operator registry.
    """
    split = _split_fused_indexed_operator(operator.op)
    return split[0] if split is not None else operator.op


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


def _ir_segment_tokens(ir: StandardNameIR) -> dict[str, set[str]]:
    """The grammar tokens the parse of a name fills, grouped by segment kind."""
    tokens: dict[str, set[str]] = {}

    def add(kind: str, token: str) -> None:
        tokens.setdefault(kind, set()).add(token)

    for operator in _iter_operators(ir.operators):
        add("transformation", _operator_token(operator))
    for qualifier in ir.qualifiers:
        add(_qualifier_segment_kind(qualifier.token), qualifier.token)
    if ir.projection is not None:
        add(
            "component"
            if ir.projection.shape is ProjectionShape.COMPONENT
            else "coordinate",
            ir.projection.axis,
        )
    if ir.base.token != "placeholder":
        add(
            "physical_base" if ir.base.kind is BaseKind.QUANTITY else "geometric_base",
            ir.base.token,
        )
    if ir.locus is not None:
        kind = _locus_segment_kind(ir.locus.type)
        add(kind, ir.locus.token)
        for qualifier in ir.locus.qualifiers:
            add(kind, qualifier)
    if ir.mechanism is not None:
        add("process", ir.mechanism.token)
    return tokens


def _ir_tokens(ir: StandardNameIR) -> frozenset[str]:
    """Every grammar token named by the parse of a name."""
    return frozenset(
        token for tokens in _ir_segment_tokens(ir).values() for token in tokens
    )


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


def _template_conditions_met(
    entry: TemplateEntry,
    segment_tokens: dict[str, set[str]],
    segments: frozenset[str],
) -> bool:
    """Whether a name filling ``segments`` satisfies an entry's conditions."""
    if set(entry.excludes) & segments:
        return False
    return all(
        set(required) & segment_tokens.get(kind, set())
        for kind, required in entry.requires.items()
    )


def _select_templates(
    entries: list[TemplateEntry],
    ir: StandardNameIR,
    segments: frozenset[str],
) -> list[TemplateEntry]:
    """The templates a parsed name selects, in file order.

    A conditioned entry takes precedence over an unconditioned sibling: among
    entries sharing a base and the same required segment kinds, a matching
    conditioned entry supersedes its unconditioned siblings for that name, so
    the unconditioned openings and the conditioned one never both render. An
    entry with no conditions selects exactly as before.
    """
    segment_tokens = _ir_segment_tokens(ir)
    template_bases = {
        operator.op for operator in ir.operators if operator.kind is OperatorKind.BINARY
    }
    if ir.base.token != "placeholder":
        template_bases.add(ir.base.token)
    matched = [
        entry
        for entry in entries
        if entry.base in template_bases
        and set(entry.segments) <= segments
        and _template_conditions_met(entry, segment_tokens, segments)
    ]
    conditioned = {
        (entry.base, tuple(entry.segments))
        for entry in matched
        if entry.requires or entry.excludes
    }
    return [
        entry
        for entry in matched
        if entry.requires or entry.excludes
        or (entry.base, tuple(entry.segments)) not in conditioned
    ]


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
    definitions_applied = tuple(
        AppliedDefinition(
            token=token,
            segment=kind,
            definition=definitions[token],
        )
        for token in sorted(tokens)
        if (kind := _qualifier_segment_kind(token)) in _DEFINITION_SEGMENTS
        and kind in segments
        and token in definitions
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
            note=entry.note,
        )
        for entry in _select_templates(conventions.templates.templates, ir, segments)
    )
    return AppliedConventions(
        concepts=concepts,
        definitions=definitions_applied,
        notation=notation,
        templates=templates,
    )
