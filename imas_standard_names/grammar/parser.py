"""Standard name grammar parser.

Implements a *staged, liberal* parser that turns a standard-name string
into a :class:`~imas_standard_names.grammar.ir.StandardNameIR` plus a
list of :class:`Diagnostic` records. The parser is the inverse of
:func:`imas_standard_names.grammar.render.compose`; together they form
the required round-trip pair.

Parsing is driven by closed vocabularies loaded from
``grammar/vocabularies/*.yml`` via :mod:`vocab_loaders`. Callers may
inject their own :class:`Vocabularies` bundle for testing.

Algorithm::

    1. Strip trailing _due_to_<process>                -> mechanism
    2. Strip trailing _of_/_at_/_over_/_along_<locus>  -> locus
       (longest registry-backed match; only _at_ may
       fall back with a vocab_gap diagnostic — _over_
       and _along_ require a registered locus)
    3. Peel outer operators right-to-outermost         -> operators
       a) unary_postfix (longest match at end)
       b) unary_prefix  (longest match `<op>_of_...`)
       c) binary        (`<binary_op>_of_<A>_<sep>_<B>`)
       repeat until no operator peels
    4. Match residue: carrier > base > axis+resolve > qualifier+recurse
       Projection is detected inline when an axis prefix precedes
       a resolvable base (COMPONENT) or carrier (COORDINATE).
       Short form only — ``_component_of_`` and ``_coordinate_of_``
       markers are parse errors.

Liberal acceptance: the parser accepts grammatically valid forms
only. Unknown base residues raise :class:`ParseError` with top-3
edit-distance suggestions. No legacy open-fallback behaviour is retained.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Any

from imas_standard_names.grammar import vocab_loaders
from imas_standard_names.grammar.ir import (
    TOKEN_PATTERN,
    AxisProjection,
    BaseKind,
    LocusRef,
    LocusRelation,
    LocusType,
    OperatorApplication,
    OperatorKind,
    Process,
    ProjectionShape,
    Qualifier,
    QuantityOrCarrier,
    StandardNameIR,
)
from imas_standard_names.grammar.model_types import Component, Object, Subject
from imas_standard_names.grammar.render import compose

__all__ = [
    "Diagnostic",
    "ParseError",
    "ParseResult",
    "Vocabularies",
    "load_default_vocabularies",
    "parse",
    "validate_round_trip",
]


# ---------------------------------------------------------------------------
# Vocabulary bundle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Vocabularies:
    """Closed-vocabulary bundle consumed by the parser.

    All fields are immutable collections. Callers may synthesise a bundle
    directly for tests (bypassing YAML loading); the parser never
    introspects loader-level types.
    """

    axes: frozenset[str] = field(default_factory=frozenset)
    component_axes: frozenset[str] = field(default_factory=frozenset)
    loci: Mapping[str, tuple[LocusType, frozenset[LocusRelation]]] = field(
        default_factory=dict
    )
    operators: Mapping[str, dict[str, Any]] = field(default_factory=dict)
    bases: frozenset[str] = field(default_factory=frozenset)
    carriers: frozenset[str] = field(default_factory=frozenset)
    qualifiers: frozenset[str] = field(default_factory=frozenset)
    # token → normalized category for the genuine modifier qualifiers
    # (qualifiers.yml). Empty for tokens that only peel as qualifiers via the
    # acceptance union (operators, loci, subjects); IR metadata only.
    qualifier_categories: Mapping[str, str] = field(default_factory=dict)
    # Ordered geometric qualifiers (canonical intra-order) that compose onto a
    # ``qualifiable`` locus feature (inner_strike_point, upper_outer_strike_point).
    locus_qualifiers: tuple[str, ...] = ()
    # Locus feature tokens that admit ``locus_qualifiers`` prefixes.
    qualifiable_loci: frozenset[str] = field(default_factory=frozenset)

    def base_universe(self) -> frozenset[str]:
        return self.bases | self.carriers

    def closed_universe(self) -> frozenset[str]:
        return (
            self.bases
            | self.carriers
            | self.qualifiers
            | frozenset(self.axes)
            | self.component_axes
            | frozenset(self.operators)
            | frozenset(self.loci)
        )


def _normalise_separator(sep: str | None) -> str | None:
    if sep is None:
        return None
    return sep.strip("_") or None


def load_default_vocabularies() -> Vocabularies:
    """Load all five grammar vocabularies from YAML into a :class:`Vocabularies`.

    Falls back to an empty set for any registry whose YAML stub is empty
    (physical_bases.yml, geometry_carriers.yml).

    Qualifiers are populated from:
    - ``Subject`` enum tokens (electron, ion, deuterium, …)
    - Physics modifier tokens (energy, particle, momentum, …) that act as
      recursive prefixes before a physical_base.
    """
    axes_reg = vocab_loaders.load_coordinate_axes()
    loci_reg = vocab_loaders.load_locus_registry()
    ops_reg = vocab_loaders.load_operators()
    bases_reg = vocab_loaders.load_physical_bases()
    carriers_reg = vocab_loaders.load_geometry_carriers()

    loci: dict[str, tuple[LocusType, frozenset[LocusRelation]]] = {}
    qualifiable_loci_set: set[str] = set()
    for token, entry in loci_reg.loci.items():
        locus_type = LocusType(entry.type)
        allowed = frozenset(LocusRelation(r) for r in entry.allowed_relations)
        loci[token] = (locus_type, allowed)
        if entry.qualifiable:
            qualifiable_loci_set.add(token)

    operators: dict[str, dict[str, Any]] = {}
    for token, entry in ops_reg.operators.items():
        operators[token] = {
            "kind": entry.kind,
            "precedence": entry.precedence,
            "separator": _normalise_separator(entry.separator),
            "indexed": entry.indexed,
            "index_params": entry.index_params,
            "returns": entry.returns,
            "arg_types": entry.arg_types,
            "flux_surface_reduction": entry.flux_surface_reduction,
        }

    # Build qualifier set: Subject tokens + Object tokens + YAML-loaded
    # modifier prefixes.  Tokens that are also in bases/carriers are safe —
    # the parser tries full base match first; qualifiers only strip
    # recursively when the full string is NOT itself a registered base or
    # carrier.
    subject_quals = frozenset(s.value for s in Subject)
    object_quals = frozenset(o.value for o in Object)
    modifier_quals = vocab_loaders.load_qualifiers()
    # Aggregation (total/net) + population (energy-state) + orbit (transit
    # class) modifiers peel like qualifiers; the StandardName model retains
    # them in the dedicated ``aggregation`` / ``population`` / ``orbit``
    # single-token segments.
    aggregation_quals = vocab_loaders.load_aggregations()
    population_quals = vocab_loaders.load_populations()
    orbit_quals = vocab_loaders.load_orbits()
    # State-resolution tokens (charge_state, internal_state) peel like
    # qualifiers; the model retains the single token in the ``state`` segment.
    state_quals = vocab_loaders.load_states()

    # Add unary_prefix operator tokens as qualifiers so that "bare" prefix
    # operators (those that attach without _of_, like volume_averaged,
    # normalized, flux_surface_averaged) can be stripped during qualifier
    # matching.  Operators that DO use _of_ form are peeled first by
    # _peel_outer_operator and never reach the qualifier stage.
    prefix_op_quals = frozenset(
        name
        for name, meta in operators.items()
        if meta.get("kind") == OperatorKind.UNARY_PREFIX.value
    )

    # Zone tokens (core, edge, inner, outer, lower, ...) are an ordered prefix
    # segment; they peel like qualifiers and the model retains them in the
    # ``zone`` segment.
    zone_quals = frozenset(vocab_loaders.load_zones())

    # Channel tokens (heat, particle, energy, momentum) name what is
    # transported. They peel like qualifiers (innermost prefix, just before the
    # base); the model retains the single token in the ``channel`` segment.
    # energy/momentum are also bases — the parser tries the full base match
    # first, so standalone energy/momentum resolve as base and only the
    # *_flux/*_diffusivity/... compounds strip the channel.
    channel_quals = frozenset(vocab_loaders.load_channels())

    # Channel-qualifier tokens (kinetic, plasma) bind to the transport channel.
    # They peel like qualifiers (outer of the channel, inner of the zone); the
    # model retains the single token in the ``channel_qualifier`` segment.
    # kinetic also forms the atomic base kinetic_energy — the parser tries the
    # longest base match first, so electron_kinetic_energy resolves as the base
    # while ion_kinetic_energy_flux strips channel_qualifier=kinetic.
    channel_qualifier_quals = frozenset(vocab_loaders.load_channel_qualifiers())

    qualifiers = (
        subject_quals
        | object_quals
        | modifier_quals
        | aggregation_quals
        | population_quals
        | orbit_quals
        | state_quals
        | prefix_op_quals
        | zone_quals
        | channel_quals
        | channel_qualifier_quals
    )

    return Vocabularies(
        axes=frozenset(axes_reg.axes),
        component_axes=frozenset(member.value for member in Component),
        loci=loci,
        operators=operators,
        bases=frozenset(bases_reg.bases),
        carriers=frozenset(carriers_reg.carriers),
        qualifiers=qualifiers,
        qualifier_categories=vocab_loaders.load_qualifier_categories(),
        locus_qualifiers=tuple(loci_reg.locus_qualifiers),
        qualifiable_loci=frozenset(qualifiable_loci_set),
    )


_DEFAULT_CACHE: Vocabularies | None = None


def _default_vocabs() -> Vocabularies:
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        _DEFAULT_CACHE = load_default_vocabularies()
    return _DEFAULT_CACHE


# ---------------------------------------------------------------------------
# Diagnostics / result types
# ---------------------------------------------------------------------------


@dataclass
class Diagnostic:
    """A single parser/validator diagnostic entry.

    Matches the contract confirmed by W1b: ``category`` is one of
    ``"non_canonical"``, ``"vocab_gap"``, or ``"ambiguity"``; ``layer`` is
    ``"parser"`` or ``"validator"``; ``severity`` is ``"info"``,
    ``"warning"``, or ``"error"``.
    """

    category: str
    layer: str
    message: str
    suggestion: str | None = None
    severity: str = "info"


@dataclass
class ParseResult:
    ir: StandardNameIR
    diagnostics: list[Diagnostic] = field(default_factory=list)


class ParseError(ValueError):
    """Raised when the parser cannot produce a valid IR."""

    def __init__(
        self,
        message: str,
        *,
        suggestions: list[str] | None = None,
        residue: str | None = None,
    ) -> None:
        super().__init__(message)
        self.suggestions: list[str] = list(suggestions or [])
        self.residue: str | None = residue


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------


def _strip_mechanism(s: str) -> tuple[Process | None, str]:
    marker = "_due_to_"
    idx = s.rfind(marker)
    if idx <= 0:
        return None, s
    token = s[idx + len(marker) :]
    if not token or not TOKEN_PATTERN.match(token):
        return None, s
    head = s[:idx]
    if not head:
        return None, s
    return Process(token=token), head


# Value-parameterized at-locus: ``at_<token>_equal_to_<value>`` where <value>
# is a numeric literal with underscores as decimal separators (0_95, 1_0, 2).
_LOCUS_VALUE_SUFFIX = re.compile(
    r"^(?P<head>[a-z][a-z0-9_]*)_equal_to_(?P<value>\d+(?:_\d+)?)$"
)


def _match_locus_feature(
    token: str, v: Vocabularies
) -> tuple[str, tuple[str, ...], LocusType, frozenset[LocusRelation]] | None:
    """Resolve a locus token to ``(feature, qualifiers, type, relations)``.

    Direct registry hit first (bare feature or non-qualifiable flat token); then
    the compositional form — strip leading geometric qualifiers off a
    ``qualifiable`` feature (``inner_strike_point`` -> ``strike_point`` + ``inner``;
    ``upper_outer_strike_point`` -> ``strike_point`` + ``upper``, ``outer``).
    Qualifiers are returned in canonical intra-order; a non-canonically-authored
    input therefore fails the compose round-trip and is rejected as non-canonical.
    """
    if token in v.loci:
        lt, allowed = v.loci[token]
        return token, (), lt, allowed
    if not v.locus_qualifiers or not v.qualifiable_loci:
        return None
    qset = set(v.locus_qualifiers)
    order = {q: i for i, q in enumerate(v.locus_qualifiers)}
    quals: list[str] = []
    rest = token
    while "_" in rest:
        head, _, tail = rest.partition("_")
        if head not in qset:
            break
        quals.append(head)
        rest = tail
        if rest in v.qualifiable_loci:
            lt, allowed = v.loci[rest]
            canon = tuple(sorted(quals, key=lambda q: order[q]))
            return rest, canon, lt, allowed
    return None


def _strip_locus(
    s: str, v: Vocabularies
) -> tuple[LocusRef | None, str, list[Diagnostic]]:
    """Strip a trailing locus suffix.

    Preference order: rightmost registry-backed ``_<rel>_<token>`` match,
    including the value-parameterized form ``_at_<token>_equal_to_<value>``
    (the ``_equal_to_<value>`` suffix is split off BEFORE registry lookup;
    only position-typed registry tokens admit a value). ``_at_`` has no
    operator collisions, so an unregistered token still strips with a
    ``vocab_gap`` diagnostic. ``_over_`` and ``_along_`` require a
    registered locus — an unregistered token is left in the residue so the
    unknown-base match rejects the name rather than fabricating a locus.
    ``_of_`` without a registry hit is LEFT alone so step-4 operator peeling
    can resolve it as a binary-operator template.
    """

    diagnostics: list[Diagnostic] = []

    # 1. Registry-backed rightmost match (direct feature or composed
    #    <qualifier>..._<feature>, e.g. inner_strike_point).
    best: tuple[str, int, str, str | None, tuple[str, ...]] | None = None
    for rel in ("over", "at", "along", "of"):
        marker = f"_{rel}_"
        idx = s.rfind(marker)
        while idx > 0:
            token = s[idx + len(marker) :]
            m = _match_locus_feature(token, v) if token else None
            if m is not None:
                if best is None or idx > best[1]:
                    best = (rel, idx, m[0], None, m[1])
                break
            # Value-parameterized position: at_<token>_equal_to_<value>.
            # Split the value suffix BEFORE the registry lookup; only
            # position-typed tokens admit a value (relation 'at').
            if rel == "at" and token:
                value_match = _LOCUS_VALUE_SUFFIX.match(token)
                if value_match:
                    hm = _match_locus_feature(value_match.group("head"), v)
                    if hm is not None and hm[2] is LocusType.POSITION:
                        if best is None or idx > best[1]:
                            best = (
                                rel,
                                idx,
                                hm[0],
                                value_match.group("value"),
                                hm[1],
                            )
                        break
            idx = s.rfind(marker, 0, idx)

    if best is not None:
        rel_str, idx, token, value, quals = best
        locus_type, allowed = v.loci[token]
        relation = LocusRelation(rel_str)
        if relation not in allowed:
            allowed_names = sorted(r.value for r in allowed)
            diagnostics.append(
                Diagnostic(
                    category="non_canonical",
                    layer="parser",
                    message=(
                        f"relation '_{rel_str}_' not permitted for locus "
                        f"{token!r} (type={locus_type.value}); "
                        f"allowed: {allowed_names}"
                    ),
                    severity="warning",
                )
            )
            return None, s, diagnostics
        locus = LocusRef(
            relation=relation,
            token=token,
            qualifiers=quals,
            type=locus_type,
            value=value,
        )
        return locus, s[:idx], diagnostics

    # 2. Unregistered-but-unambiguous fallback for _at_ only.
    #    Skip if the core that would remain is a known qualifier or operator
    #    token — that indicates the _at_ is part of a compound token, not a
    #    locus marker (e.g. maximum_over_flux_surface for the analogous _over_
    #    case).
    #
    #    The _over_ relation does NOT take this fallback: it is valid solely
    #    for region-typed loci (the locus_registry compatibility matrix), and
    #    those are matched in step 1. An unregistered _over_<X> would otherwise
    #    fabricate a spurious region locus (e.g. velocity_over_magnetic_field),
    #    masking the correct construction (ratio_of_velocity_to_magnetic_field).
    #    Leaving it in the residue makes the base match fail → ParseError.
    for rel, default_type in (("at", LocusType.POSITION),):
        marker = f"_{rel}_"
        idx = s.rfind(marker)
        if idx <= 0:
            continue
        token = s[idx + len(marker) :]
        if not token or not TOKEN_PATTERN.match(token):
            continue
        core = s[:idx]
        # Check if the whole string up to and including the marker token
        # is a registered qualifier/operator (e.g. "maximum_over_flux_surface")
        if any(
            q.startswith(core + marker.rstrip("_"))
            for q in v.qualifiers
            if len(q) > len(core)
        ):
            continue
        try:
            locus = LocusRef(
                relation=LocusRelation(rel),
                token=token,
                type=default_type,
            )
        except Exception:
            continue
        diagnostics.append(
            Diagnostic(
                category="vocab_gap",
                layer="parser",
                message=(
                    f"locus token {token!r} not in locus_registry "
                    f"(defaulted type={default_type.value})"
                ),
                severity="info",
            )
        )
        return locus, s[:idx], diagnostics

    return None, s, diagnostics


def _longest_match(s: str, candidates: frozenset[str] | set[str]) -> str | None:
    """Return the longest candidate in ``candidates`` that matches.

    ``candidates`` should be raw tokens; ``s`` is the full string we are
    searching. This helper is used for operator detection where we match
    against an exact equality family, not a prefix/suffix — callers
    compose the full boundary marker themselves.
    """
    best: str | None = None
    for token in candidates:
        if token == s and (best is None or len(token) > len(best)):
            best = token
    return best


def _peel_outer_operator(
    s: str, v: Vocabularies
) -> tuple[OperatorApplication | None, str, list[StandardNameIR]]:
    """Peel ONE outer operator off ``s``.

    Returns (op_application, new_inner_string_if_unary, binary_args).
    For unary operators, ``binary_args`` is empty and the caller keeps
    parsing ``new_inner_string_if_unary``. For binary operators the inner
    string is empty and ``binary_args`` holds the two parsed sub-IRs; the
    caller attaches them to the op_application and stops operator peeling
    (a binary operator has no further prefix/postfix beyond its args).
    """

    # Split operators by kind.
    postfix_ops = {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.UNARY_POSTFIX.value
    }
    prefix_ops = {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.UNARY_PREFIX.value
    }
    binary_ops = {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.BINARY.value
    }

    # a) unary postfix: s ends with "_<op>", longest op first
    postfix_match = _longest_suffix_match(s, postfix_ops)
    if postfix_match is not None:
        new_s = s[: -len(postfix_match) - 1]  # drop "_<op>"
        if new_s:
            return (
                OperatorApplication(kind=OperatorKind.UNARY_POSTFIX, op=postfix_match),
                new_s,
                [],
            )

    # b) unary prefix: s starts with "<op>_of_"
    prefix_match = _longest_prefix_operator_match(s, prefix_ops)
    if prefix_match is not None:
        new_s = s[len(prefix_match) + len("_of_") :]
        if new_s:
            return (
                OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op=prefix_match),
                new_s,
                [],
            )

    # b1) indexed unary prefix: s starts with "<op>_<coord>_of_" where <op> is
    # an indexed prefix operator (index_params) and <coord> is a registered
    # coordinate token. The bound index is fused into the operator token
    # (<op>_<coord>) so the canonical renderer reproduces the prefix form
    # "<op>_<coord>_of_<inner>" verbatim.
    indexed_match = _longest_indexed_prefix_operator_match(s, prefix_ops, v)
    if indexed_match is not None:
        fused_op, consumed_len = indexed_match
        new_s = s[consumed_len + len("_of_") :]
        if new_s:
            return (
                OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op=fused_op),
                new_s,
                [],
            )

    # b2) bare unary prefix: These operators (normalized, volume_averaged, etc.)
    # fall through to the qualifier + base matching stage and are handled
    # by the IR→Model adapter in model.py. We do NOT peel them here because
    # they can form compound axes (e.g. normalized_radial) that projection
    # stripping needs to see intact.

    # c) binary: s starts with "<op>_of_" and contains its declared separator
    for op in sorted(binary_ops, key=len, reverse=True):
        prefix = f"{op}_of_"
        if not s.startswith(prefix):
            continue
        rest = s[len(prefix) :]
        sep = v.operators[op].get("separator")
        if sep is None:
            continue
        sep_marker = f"_{sep}_"
        # Use rightmost split to maximize the first operand (compound bases
        # may contain the separator word).
        sep_idx = rest.rfind(sep_marker)
        while sep_idx > 0:
            a_str = rest[:sep_idx]
            b_str = rest[sep_idx + len(sep_marker) :]
            if not a_str or not b_str:
                break
            # Try strict parsing first; fall back to literal bases when
            # sub-expressions contain unregistered compound tokens (e.g.
            # "magnetic_pressure").
            a_ir = _try_parse_or_literal(a_str, v)
            b_ir = _try_parse_or_literal(b_str, v)
            if a_ir is not None and b_ir is not None:
                return (
                    OperatorApplication(
                        kind=OperatorKind.BINARY,
                        op=op,
                        separator=sep,
                        args=[a_ir, b_ir],
                    ),
                    "",
                    [a_ir, b_ir],
                )
            sep_idx = rest.rfind(sep_marker, 0, sep_idx)

    return None, s, []


def _peel_trailing_postfix_operator(
    s: str, v: Vocabularies
) -> tuple[OperatorApplication | None, str]:
    """Peel ONE trailing unary-postfix operator off the END of ``s``.

    A postfix decomposition operator renders at the very tail of the canonical
    string (``{core}_{op}``), after any locus/mechanism suffix. Peeling it
    before the mechanism/locus strips keeps those strips from greedily
    absorbing the operator token into a fabricated process/locus token.

    Returns ``(None, s)`` when no postfix operator suffix is present.
    """
    postfix_ops = {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.UNARY_POSTFIX.value
    }
    match = _longest_suffix_match(s, postfix_ops)
    if match is None:
        return None, s
    new_s = s[: -len(match) - 1]  # drop "_<op>"
    if not new_s:
        return None, s
    return (
        OperatorApplication(kind=OperatorKind.UNARY_POSTFIX, op=match),
        new_s,
    )


def _longest_suffix_match(s: str, tokens: set[str]) -> str | None:
    best: str | None = None
    for tok in tokens:
        marker = f"_{tok}"
        if s.endswith(marker) and len(s) > len(marker):
            if best is None or len(tok) > len(best):
                best = tok
    return best


def _longest_prefix_operator_match(s: str, tokens: set[str]) -> str | None:
    best: str | None = None
    for tok in tokens:
        marker = f"{tok}_of_"
        if s.startswith(marker) and len(s) > len(marker):
            if best is None or len(tok) > len(best):
                best = tok
    return best


def _coordinate_universe(v: Vocabularies) -> frozenset[str]:
    """Tokens admissible as an indexed-operator coordinate index.

    The ``coord`` index of operators like ``derivative_with_respect_to`` is
    drawn from the coordinate / flux-coordinate vocabulary: the geometry
    carriers (``radial_coordinate``, ``toroidal_flux_coordinate``,
    ``normalized_poloidal_flux_coordinate``, …) plus the bare coordinate axes
    (``radial``, ``poloidal``, …).
    """
    return v.carriers | frozenset(v.axes)


def _longest_indexed_prefix_operator_match(
    s: str, prefix_ops: set[str], v: Vocabularies
) -> tuple[str, int] | None:
    """Match ``<op>_<coord>_of_`` for an indexed unary-prefix operator.

    ``<op>`` must be an indexed prefix operator (``index_params`` declared with
    a single ``coord`` parameter) and ``<coord>`` must be a registered
    coordinate token (see :func:`_coordinate_universe`). Returns the fused
    operator token ``<op>_<coord>`` together with the byte length consumed up
    to (but excluding) the ``_of_`` separator, or ``None`` when no indexed
    operator binds.

    The longest fused match wins (operator length first, then coordinate
    length) so an overlapping plain-prefix match never shadows it.
    """
    coords = _coordinate_universe(v)
    best: tuple[str, int] | None = None
    for op in prefix_ops:
        meta = v.operators.get(op, {})
        if not meta.get("indexed"):
            continue
        params = meta.get("index_params") or []
        # Only the single-coordinate index form is supported in the prefix
        # position (``<op>_<coord>_of_<base>``).
        if list(params) != ["coord"]:
            continue
        op_prefix = f"{op}_"
        if not s.startswith(op_prefix):
            continue
        remainder = s[len(op_prefix) :]
        of_idx = remainder.find("_of_")
        if of_idx <= 0:
            continue
        coord = remainder[:of_idx]
        if coord not in coords:
            continue
        fused = f"{op}_{coord}"
        consumed = len(fused)
        if best is None or consumed > best[1]:
            best = (fused, consumed)
    return best


def _try_parse_or_literal(s: str, v: Vocabularies) -> StandardNameIR | None:
    """Try to parse ``s`` as a full standard name; fall back to a literal base.

    Returns ``None`` only when ``s`` is syntactically invalid (not
    snake_case). For valid-looking tokens that don't match the closed
    vocabulary, returns a literal ``QuantityOrCarrier`` so binary operator
    operands with unregistered compound bases (e.g. ``magnetic_pressure``)
    are accepted.
    """
    try:
        return parse(s, vocabs=v).ir
    except ParseError:
        if TOKEN_PATTERN.match(s):
            return StandardNameIR(
                base=QuantityOrCarrier(token=s, kind=BaseKind.QUANTITY)
            )
        return None


def _match_base_with_qualifiers(
    s: str, v: Vocabularies, *, _allow_projection: bool = True
) -> tuple[QuantityOrCarrier, list[Qualifier], AxisProjection | None]:
    """Match ``s`` as ``[axis_][qualifier_]*(base|carrier)``.

    Resolution priority: carrier > base > axis > qualifier.

    When ``_allow_projection`` is True (the default), an axis prefix
    followed by a resolvable base/carrier is interpreted as a projection:
    axis + quantity base → COMPONENT, axis + carrier → COORDINATE.
    Nested projections (projection inside a projection) are blocked by
    recursing with ``_allow_projection=False``.

    Returns ``(base_or_carrier, qualifiers, projection_or_none)``.
    """

    if s in v.carriers:
        return QuantityOrCarrier(token=s, kind=BaseKind.GEOMETRY), [], None
    if s in v.bases:
        return QuantityOrCarrier(token=s, kind=BaseKind.QUANTITY), [], None

    parts = s.split("_")

    # --- Priority 3: axis prefix → projection ---
    if _allow_projection:
        projection_axes = v.axes | v.component_axes
        for split in range(len(parts) - 1, 0, -1):
            prefix = "_".join(parts[:split])
            rest = "_".join(parts[split:])
            if prefix not in projection_axes or not rest:
                continue
            try:
                base, quals, inner_proj = _match_base_with_qualifiers(
                    rest, v, _allow_projection=False
                )
            except ParseError:
                continue
            if inner_proj is not None:
                continue  # nested projections not allowed
            shape = (
                ProjectionShape.COORDINATE
                if base.kind is BaseKind.GEOMETRY
                else ProjectionShape.COMPONENT
            )
            allowed_axes = (
                v.axes
                if shape is ProjectionShape.COORDINATE
                else (v.component_axes or v.axes)
            )
            if prefix not in allowed_axes:
                continue
            return base, quals, AxisProjection(axis=prefix, shape=shape)

    # --- Priority 4: qualifier prefix ---
    for split in range(len(parts) - 1, 0, -1):
        prefix = "_".join(parts[:split])
        rest = "_".join(parts[split:])
        if prefix not in v.qualifiers:
            continue
        if not rest:
            continue
        try:
            base, deeper, proj = _match_base_with_qualifiers(
                rest, v, _allow_projection=_allow_projection
            )
        except ParseError:
            continue
        return (
            base,
            [
                Qualifier(token=prefix, category=v.qualifier_categories.get(prefix)),
                *deeper,
            ],
            proj,
        )

    suggestions = get_close_matches(s, list(v.base_universe()), n=3)
    raise ParseError(
        f"residue {s!r} does not match any physical_base or geometry_carrier; "
        f"nearest candidates: {suggestions or '(none)'}",
        suggestions=suggestions,
        residue=s,
    )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def parse(name: str, vocabs: Vocabularies | None = None) -> ParseResult:
    """Parse ``name`` into a :class:`ParseResult`.

    Raises :class:`ParseError` when the residue cannot be resolved
    against the closed base vocabulary.
    """

    if not isinstance(name, str) or not name:
        raise ParseError("name must be a non-empty string")
    if not TOKEN_PATTERN.match(name):
        raise ParseError(
            f"name {name!r} is not a valid grammar token (must be lowercase snake_case)"
        )

    v = vocabs if vocabs is not None else _default_vocabs()
    diagnostics: list[Diagnostic] = []
    s = name

    # Stage 0: trailing postfix operators.
    #
    # A postfix decomposition operator (``magnitude``, ``moment``, ...) renders
    # at the very END of the canonical string — AFTER any locus/mechanism
    # suffix (``compose`` wraps ``base + locus + mechanism`` as
    # ``{core}_{op}``). Peel these BEFORE the mechanism/locus strips so a
    # postfix token sitting after a locus/mechanism is not greedily absorbed
    # into the process/locus token (which would silently drop the operator,
    # e.g. ``velocity_due_to_pellet_injection_magnitude`` fabricating a
    # ``pellet_injection_magnitude`` process). These ops are the OUTERMOST
    # trailing wrap, so they go to the FRONT of the operator stack.
    trailing_postfix: list[OperatorApplication] = []
    while True:
        op_app, new_s = _peel_trailing_postfix_operator(s, v)
        if op_app is None:
            break
        trailing_postfix.append(op_app)
        s = new_s

    # Stage 1: mechanism
    mechanism, s = _strip_mechanism(s)

    # Stage 2: locus
    locus, s, locus_diags = _strip_locus(s, v)
    diagnostics.extend(locus_diags)

    # Stage 3: operator peeling (outermost layer after locus/mechanism).
    # Trailing postfix operators peeled in stage 0 are the outermost wrap and
    # precede anything peeled here (a prefix/binary operator-of form).
    operator_stack: list[OperatorApplication] = list(trailing_postfix)
    binary_terminator: OperatorApplication | None = None
    while True:
        op_app, new_s, _ = _peel_outer_operator(s, v)
        if op_app is None:
            break
        if op_app.kind is OperatorKind.BINARY:
            binary_terminator = op_app
            s = ""
            break
        operator_stack.append(op_app)
        s = new_s

    if binary_terminator is not None:
        # Binary consumed everything. Base/qualifiers/projection must be empty.
        if s:
            raise ParseError(
                f"binary operator {binary_terminator.op!r} cannot combine with "
                "residue; got unexpected trailing content"
            )
        # Synthesise a placeholder base so the outer IR validates. The
        # binary operator lives on the outer IR's operators stack and its
        # args carry the real structure. The placeholder is never rendered.
        # The full operator stack — trailing postfix (stage 0) plus any
        # prefix operators peeled before the binary terminator — wraps the
        # binary result, outermost first.
        ir = StandardNameIR(
            operators=[*operator_stack, binary_terminator],
            base=QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY),
            locus=locus,
            mechanism=mechanism,
        )
        return ParseResult(ir=ir, diagnostics=diagnostics)

    # Stage 4: carrier > base > axis (projection) > qualifier
    if not s:
        raise ParseError(
            "empty residue after peeling operators and decorators",
        )
    base, qualifiers, projection = _match_base_with_qualifiers(s, v)

    ir = StandardNameIR(
        operators=operator_stack,
        projection=projection,
        qualifiers=qualifiers,
        base=base,
        locus=locus,
        mechanism=mechanism,
    )
    return ParseResult(ir=ir, diagnostics=diagnostics)


def validate_round_trip(name: str, vocabs: Vocabularies | None = None) -> bool:
    """Return ``True`` iff ``compose(parse(name).ir) == name``.

    Raises :class:`ParseError` when the name fails to parse. Otherwise
    compares the rendered form against the input byte-for-byte.

    IR-diagnostics tool only — NOT the validity oracle. It runs on the lenient
    IR parser and answers "does this name render back to itself?", which is
    weaker than validity: it does not enforce segment compatibility, the
    generic-base gate, or the flux-surface reduction gate. Use
    :func:`imas_standard_names.grammar.model.parse_standard_name` (strict) to
    decide whether a name is valid; use this helper to locate IR
    parse/compose round-trip drift (see docs/architecture/boundary.md).
    """

    result = parse(name, vocabs=vocabs)
    try:
        rendered = compose(result.ir)
    except Exception:
        return False
    return rendered == name
