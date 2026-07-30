"""Standard name grammar parser.

Implements a multi-pass parser that turns a standard-name string
into a :class:`~imas_standard_names.grammar.ir.StandardNameIR` plus a
list of :class:`Diagnostic` records. The parser is the inverse of
:func:`imas_standard_names.grammar.render.compose`; together they form
the required round-trip pair. Diagnostic mode is liberal where explicitly
documented; ``strict=True`` validates the lossless ordered expression against
the operator-expression contract without projecting through the flat model.

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
       c) bare prefix over a nested operator expression
       d) binary        (`<binary_op>_of_<A>_<sep>_<B>`)
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
from imas_standard_names.grammar.constants import GENERIC_PHYSICAL_BASES
from imas_standard_names.grammar.ir import (
    BARE_PREFIX_OPERATORS,
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
    base_aliases: Mapping[str, str] = field(default_factory=dict)
    carrier_aliases: Mapping[str, str] = field(default_factory=dict)
    base_kinds: Mapping[str, str] = field(default_factory=dict)
    flux_function_bases: frozenset[str] = field(default_factory=frozenset)
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
    # recursively when the full string is not itself a registered base or
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
        base_aliases={
            alias: token
            for token, definition in bases_reg.bases.items()
            for alias in definition.aliases
        },
        carrier_aliases={
            alias: token
            for token, definition in carriers_reg.carriers.items()
            for alias in definition.aliases
        },
        base_kinds={
            token: definition.kind for token, definition in bases_reg.bases.items()
        }
        | dict.fromkeys(carriers_reg.carriers, "geometry"),
        flux_function_bases=frozenset(
            token
            for token, definition in bases_reg.bases.items()
            if definition.constant_on_flux_surface
        )
        | frozenset(
            token
            for token, definition in carriers_reg.carriers.items()
            if definition.constant_on_flux_surface
        ),
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

    Contract: ``category`` is one of
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
    ``_of_`` without a registry hit is left for operator peeling
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
    #    The _over_ relation does not take this fallback: it is valid solely
    #    for region-typed loci (the locus_registry compatibility matrix), and
    #    those are matched by the registry-backed pass. An unregistered
    #    _over_<X> would otherwise
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
    s: str,
    v: Vocabularies,
    diagnostics: list[Diagnostic] | None = None,
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

    # a) unary postfix: s ends with "_<op>", longest op first. A postfix at the
    # tail of an explicit prefix or binary form belongs to that operator's
    # operand, so leave it for the operand's own parse rather than hoisting it
    # outside the leading application.
    postfix_match = _longest_suffix_match(s, postfix_ops)
    if postfix_match is not None and _postfix_belongs_to_an_operator_operand(s, v):
        postfix_match = None
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
    # by the IR→Model adapter in model.py. We do not peel them here because
    # they can form compound axes (e.g. normalized_radial) that projection
    # stripping needs to see intact.

    # b3) bare unary prefix wrapping an explicit operator expression:
    # "<bare_prefix_op>_<unary_or_binary_application>". The fall-through in b2
    # relies on qualifier + base matching, but an operator application is not a
    # base. Peeling keeps the outer reduction first-class and preserves the
    # nested operator order; bare_prefix reproduces the joiner-free spelling.
    bare_over_operator = _longest_bare_prefix_over_operator_match(
        s, prefix_ops, binary_ops, v
    )
    if bare_over_operator is not None:
        return (
            OperatorApplication(
                kind=OperatorKind.UNARY_PREFIX,
                op=bare_over_operator,
                bare_prefix=True,
            ),
            s[len(bare_over_operator) + 1 :],
            [],
        )

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
        # Collect rightmost-first candidates, then prefer the first split
        # whose operands both resolve strictly. A connector word may occur
        # inside a registered operand (for example signal_to_noise_ratio);
        # accepting literal fallbacks at the first split would cut that base
        # apart before the parser reaches its registered boundary.
        candidates: list[tuple[str, str]] = []
        sep_idx = rest.rfind(sep_marker)
        while sep_idx > 0:
            a_str = rest[:sep_idx]
            b_str = rest[sep_idx + len(sep_marker) :]
            if not a_str or not b_str:
                break
            candidates.append((a_str, b_str))
            sep_idx = rest.rfind(sep_marker, 0, sep_idx)

        for a_str, b_str in candidates:
            try:
                a_ir = parse(a_str, vocabs=v).ir
                b_ir = parse(b_str, vocabs=v).ir
            except ParseError:
                continue
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

        # No fully registered split resolved. Retain the liberal IR fallback
        # for diagnostics; the strict validity oracle gates its vocabulary.
        for a_str, b_str in candidates:
            a_ir = _try_parse_or_literal(a_str, v, diagnostics)
            b_ir = _try_parse_or_literal(b_str, v, diagnostics)
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
    return v.carriers | frozenset(v.carrier_aliases) | frozenset(v.axes)


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
        canonical_coord = v.carrier_aliases.get(coord, coord)
        fused = f"{op}_{canonical_coord}"
        consumed = len(f"{op}_{coord}")
        if best is None or consumed > best[1]:
            best = (fused, consumed)
    return best


_BARE_PREFIX_OPERATORS_LONGEST_FIRST: tuple[str, ...] = tuple(
    sorted(BARE_PREFIX_OPERATORS, key=len, reverse=True)
)


def _postfix_belongs_to_an_operator_operand(s: str, v: Vocabularies) -> bool:
    """Whether a trailing postfix sits inside a leading operator application.

    ``square_of_magnetic_field_magnitude`` is the square of the field
    magnitude, not the magnitude of its square. The same rule keeps a trailing
    postfix inside the right operand of a binary application. A bare reduction
    may wrap either form, so look through a bare prefix only when its remainder
    is itself an explicit operator application.
    """
    binary_ops = _binary_operator_tokens(v)
    prefix_ops = {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.UNARY_PREFIX.value
    }
    if _spells_leading_operator_application(s, prefix_ops, binary_ops, v):
        return True
    postfix_ops = {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.UNARY_POSTFIX.value
    }
    postfix = _longest_suffix_match(s, postfix_ops)
    if postfix is not None:
        undecorated = s[: -len(postfix) - 1]
        if undecorated in v.base_universe():
            return False
    for op in _BARE_PREFIX_OPERATORS_LONGEST_FIRST:
        head = f"{op}_"
        if not s.startswith(head):
            continue
        return _spells_nested_operator_application(
            s[len(head) :], prefix_ops, binary_ops, v
        )
    return False


def _binary_operator_tokens(v: Vocabularies) -> set[str]:
    """Registered binary operator tokens."""
    return {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.BINARY.value
    }


def _spells_binary_application(s: str, binary_ops: set[str], v: Vocabularies) -> bool:
    """Whether ``s`` spells ``<binary_op>_of_<A>_<sep>_<B>``.

    A cheap string test — it does not parse the operands, so a true result means
    "shaped like a binary application", not "resolves". Callers use it to choose
    a peel order, and the operand parse in the binary peel is the real gate.
    """
    for op in binary_ops:
        prefix = f"{op}_of_"
        if not s.startswith(prefix):
            continue
        sep = v.operators[op].get("separator")
        if sep and f"_{sep}_" in s[len(prefix) :]:
            return True
    return False


def _spells_nested_operator_application(
    s: str,
    prefix_ops: set[str],
    binary_ops: set[str],
    v: Vocabularies,
) -> bool:
    """Whether ``s`` is a registered explicit operator application."""
    if _spells_leading_operator_application(s, prefix_ops, binary_ops, v):
        return True

    postfix_ops = {
        name
        for name, meta in v.operators.items()
        if meta.get("kind") == OperatorKind.UNARY_POSTFIX.value
    }
    postfix = _longest_suffix_match(s, postfix_ops)
    if postfix is None:
        return False
    operand = s[: -len(postfix) - 1]
    # Locus/mechanism tails are stripped before ordinary operator peeling.
    # Do not steal those forms into a bare-prefix tree here; this predicate is
    # for an unambiguously nested postfix expression.
    return bool(operand) and not any(
        marker in operand
        for marker in ("_at_", "_over_", "_along_", "_due_to_", "_of_")
    )


def _spells_leading_operator_application(
    s: str,
    prefix_ops: set[str],
    binary_ops: set[str],
    v: Vocabularies,
) -> bool:
    """Whether ``s`` starts with a registered prefix or binary application."""
    if _spells_binary_application(s, binary_ops, v):
        return True
    if _longest_prefix_operator_match(s, prefix_ops) is not None:
        return True
    return _longest_indexed_prefix_operator_match(s, prefix_ops, v) is not None


def _longest_bare_prefix_over_operator_match(
    s: str, prefix_ops: set[str], binary_ops: set[str], v: Vocabularies
) -> str | None:
    """Longest bare prefix whose remainder spells an explicit operator form.

    Restricting the match to an operator remainder keeps this from stealing the
    qualifier reading of an ordinary name: in
    ``flux_surface_averaged_electron_density`` the remainder is a base, so the
    operator stays a qualifier.
    """
    best: str | None = None
    for op in prefix_ops & BARE_PREFIX_OPERATORS:
        head = f"{op}_"
        if not s.startswith(head):
            continue
        if not _spells_nested_operator_application(
            s[len(head) :], prefix_ops, binary_ops, v
        ):
            continue
        if best is None or len(op) > len(best):
            best = op
    return best


def _try_parse_or_literal(
    s: str,
    v: Vocabularies,
    diagnostics: list[Diagnostic] | None = None,
) -> StandardNameIR | None:
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
            if diagnostics is not None:
                diagnostics.append(
                    Diagnostic(
                        category="vocab_gap",
                        layer="parser",
                        message=(
                            f"binary operand {s!r} used the literal-base fallback; "
                            "the validity oracle will require registered or "
                            "qualifier-elided operand vocabulary"
                        ),
                        severity="warning",
                    )
                )
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

    if s in v.carrier_aliases:
        return (
            QuantityOrCarrier(token=v.carrier_aliases[s], kind=BaseKind.GEOMETRY),
            [],
            None,
        )
    if s in v.base_aliases:
        return (
            QuantityOrCarrier(token=v.base_aliases[s], kind=BaseKind.QUANTITY),
            [],
            None,
        )
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
# Strict ordered-IR validation
# ---------------------------------------------------------------------------


def _operator_metadata(
    operator: OperatorApplication, v: Vocabularies
) -> tuple[str, Mapping[str, Any]]:
    """Resolve an IR operator to its registered token and metadata."""
    direct = v.operators.get(operator.op)
    if direct is not None:
        return operator.op, direct

    for token in sorted(v.operators, key=len, reverse=True):
        meta = v.operators[token]
        marker = f"{token}_"
        if not operator.op.startswith(marker) or not meta.get("indexed"):
            continue
        index = operator.op[len(marker) :]
        if list(meta.get("index_params") or []) == ["coord"] and index in (
            _coordinate_universe(v)
        ):
            return token, meta

    raise ParseError(f"operator {operator.op!r} is not registered")


def _strict_operator_spelling(ir: StandardNameIR, v: Vocabularies) -> None:
    """Enforce one canonical spelling for every registered operator."""
    ordered_precedence: list[tuple[str, int]] = []
    for qualifier in ir.qualifiers:
        meta = v.operators.get(qualifier.token)
        if (
            meta is not None
            and meta.get("kind") == OperatorKind.UNARY_PREFIX.value
            and qualifier.token not in BARE_PREFIX_OPERATORS
        ):
            raise ParseError(
                f"operator spelling for {qualifier.token!r} requires "
                f"'{qualifier.token}_of_<operand>'; the glued form is not canonical"
            )
        if qualifier.token in BARE_PREFIX_OPERATORS and meta is not None:
            ordered_precedence.append((qualifier.token, int(meta.get("precedence", 0))))

    binary_seen = False
    for index, operator in enumerate(ir.operators):
        registered_token, meta = _operator_metadata(operator, v)
        declared_kind = meta.get("kind")
        if declared_kind != operator.kind.value:
            raise ParseError(
                f"operator {operator.op!r} has kind {operator.kind.value!r}, "
                f"but the registry declares {declared_kind!r}"
            )
        ordered_precedence.append((registered_token, int(meta.get("precedence", 0))))
        if operator.kind is OperatorKind.BINARY:
            if binary_seen or index != len(ir.operators) - 1:
                raise ParseError(
                    f"binary operator {operator.op!r} must terminate its "
                    "enclosing outer-to-inner operator chain"
                )
            binary_seen = True
            registered_separator = meta.get("separator")
            if registered_separator != operator.separator:
                raise ParseError(
                    f"binary operator {operator.op!r} requires separator "
                    f"{registered_separator!r}, got {operator.separator!r}"
                )
        elif operator.kind is OperatorKind.UNARY_PREFIX:
            canonical_bare = registered_token in BARE_PREFIX_OPERATORS
            if operator.bare_prefix != canonical_bare:
                form = (
                    f"{registered_token}_<operand>"
                    if canonical_bare
                    else f"{registered_token}_of_<operand>"
                )
                raise ParseError(
                    f"operator spelling for {registered_token!r} must be {form!r}"
                )
        for argument in operator.args:
            _strict_operator_spelling(argument, v)

    for outer, inner in zip(ordered_precedence, ordered_precedence[1:], strict=False):
        if outer[1] < inner[1]:
            raise ParseError(
                f"operator {outer[0]!r} with precedence {outer[1]} cannot "
                f"wrap {inner[0]!r} with precedence {inner[1]}"
            )


def _operand_is_resolved(ir: StandardNameIR, v: Vocabularies) -> bool:
    """Whether an operator operand bottoms out in registered base vocabulary."""
    binary = next(
        (operator for operator in ir.operators if operator.kind is OperatorKind.BINARY),
        None,
    )
    if binary is not None:
        return all(_operand_is_resolved(argument, v) for argument in binary.args)
    if ir.base.token not in v.base_universe():
        return False
    return all(
        _operand_is_resolved(argument, v)
        for operator in ir.operators
        for argument in operator.args
    )


def _operand_is_qualifier_elision(
    ir: StandardNameIR, v: Vocabularies, *, sibling_is_resolved: bool
) -> bool:
    """Whether an unresolved operand safely elides a shared sibling base."""
    return (
        sibling_is_resolved
        and not ir.operators
        and ir.projection is None
        and ir.locus is None
        and ir.mechanism is None
        and all(word in v.qualifiers for word in ir.base.token.split("_"))
    )


def _strict_binary_operands(
    ir: StandardNameIR, v: Vocabularies, allowed_elisions: set[int]
) -> None:
    """Validate closed binary operands and record safe qualifier elisions."""
    for operator in ir.operators:
        if operator.kind is not OperatorKind.BINARY:
            for argument in operator.args:
                _strict_binary_operands(argument, v, allowed_elisions)
            continue

        left, right = operator.args
        left_resolved = _operand_is_resolved(left, v)
        right_resolved = _operand_is_resolved(right, v)
        if not left_resolved:
            if _operand_is_qualifier_elision(
                left, v, sibling_is_resolved=right_resolved
            ):
                allowed_elisions.add(id(left))
            else:
                raise ParseError(f"binary operand {compose(left)!r} is not registered")
        if not right_resolved:
            if _operand_is_qualifier_elision(
                right, v, sibling_is_resolved=left_resolved
            ):
                allowed_elisions.add(id(right))
            else:
                raise ParseError(f"binary operand {compose(right)!r} is not registered")
        _strict_binary_operands(left, v, allowed_elisions)
        _strict_binary_operands(right, v, allowed_elisions)


def _operator_accepts(actual: str, allowed: list[str]) -> bool:
    """Whether an inferred operand kind satisfies a registry constraint."""
    if actual in allowed:
        return True
    if "scalar_or_vector" in allowed and actual in {"scalar", "vector"}:
        return True
    if actual == "scalar_or_vector" and {"scalar", "vector"} & set(allowed):
        return False
    return False


def _operator_result_kind(meta: Mapping[str, Any], operand_kinds: list[str]) -> str:
    """Infer the output kind declared by an operator application."""
    declared = meta.get("returns")
    if declared in {None, "scalar_or_vector", "rate"}:
        concrete = {kind for kind in operand_kinds if kind in {"scalar", "vector"}}
        if len(concrete) == 1:
            return concrete.pop()
        return "scalar_or_vector"
    return str(declared)


def _strict_expression_kind(
    ir: StandardNameIR,
    v: Vocabularies,
    allowed_elisions: set[int],
    *,
    enclosing_operator: bool = False,
) -> str:
    """Validate one ordered expression and return its inferred result kind."""
    binary = next(
        (operator for operator in ir.operators if operator.kind is OperatorKind.BINARY),
        None,
    )
    if binary is None:
        if ir.base.token in v.base_universe():
            current_kind = v.base_kinds.get(
                ir.base.token,
                "geometry" if ir.base.kind is BaseKind.GEOMETRY else "scalar_or_vector",
            )
        elif id(ir) in allowed_elisions:
            current_kind = "scalar_or_vector"
        else:
            raise ParseError(f"base token {ir.base.token!r} is not registered")
    else:
        current_kind = "scalar_or_vector"

    has_local_operator = bool(ir.operators) or any(
        qualifier.token in BARE_PREFIX_OPERATORS for qualifier in ir.qualifiers
    )
    if (
        ir.base.token in GENERIC_PHYSICAL_BASES
        and not enclosing_operator
        and not has_local_operator
        and not ir.qualifiers
        and ir.projection is None
        and ir.locus is None
        and ir.mechanism is None
    ):
        raise ParseError(f"generic base {ir.base.token!r} requires qualification")

    for operator in reversed(ir.operators):
        _, meta = _operator_metadata(operator, v)
        if operator.kind is OperatorKind.BINARY:
            operand_kinds = [
                _strict_expression_kind(
                    argument,
                    v,
                    allowed_elisions,
                    enclosing_operator=True,
                )
                for argument in operator.args
            ]
        elif operator.args:
            operand_kinds = [
                _strict_expression_kind(
                    operator.args[0],
                    v,
                    allowed_elisions,
                    enclosing_operator=True,
                )
            ]
        else:
            operand_kinds = [current_kind]

        if "geometry" in operand_kinds:
            raise ParseError(
                f"operator {operator.op!r} cannot apply to a geometry carrier"
            )
        allowed = list(meta.get("arg_types") or [])
        if allowed:
            for actual in operand_kinds:
                if not _operator_accepts(actual, allowed):
                    raise ParseError(
                        f"operator {operator.op!r} requires one of {allowed}, "
                        f"got {actual!r}"
                    )
        current_kind = _operator_result_kind(meta, operand_kinds)

    for qualifier in reversed(ir.qualifiers):
        if qualifier.token not in BARE_PREFIX_OPERATORS:
            continue
        meta = v.operators[qualifier.token]
        if current_kind == "geometry":
            raise ParseError(
                f"operator {qualifier.token!r} cannot apply to a geometry carrier"
            )
        allowed = list(meta.get("arg_types") or [])
        if allowed and not _operator_accepts(current_kind, allowed):
            raise ParseError(
                f"operator {qualifier.token!r} requires one of {allowed}, "
                f"got {current_kind!r}"
            )
        current_kind = _operator_result_kind(meta, [current_kind])
    return current_kind


def _strict_flux_surface_reductions(
    ir: StandardNameIR,
    v: Vocabularies,
    *,
    inherited: frozenset[str] = frozenset(),
) -> None:
    """Reject reductions recursively applied to flux-function bases."""
    reductions = {
        token
        for token, meta in v.operators.items()
        if meta.get("flux_surface_reduction")
    }
    active = set(inherited)
    active.update(
        qualifier.token for qualifier in ir.qualifiers if qualifier.token in reductions
    )
    binary_seen = False
    for operator in ir.operators:
        if operator.op in reductions:
            active.add(operator.op)
        if operator.kind is OperatorKind.BINARY:
            binary_seen = True
            for argument in operator.args:
                _strict_flux_surface_reductions(
                    argument, v, inherited=frozenset(active)
                )
        else:
            for argument in operator.args:
                _strict_flux_surface_reductions(
                    argument, v, inherited=frozenset(active)
                )
    if not binary_seen and active and ir.base.token in v.flux_function_bases:
        operator = sorted(active)[0]
        raise ParseError(
            f"operator {operator!r} cannot apply to {ir.base.token!r}: "
            "the base is constant on a flux surface"
        )


def _strict_validate(name: str, ir: StandardNameIR, v: Vocabularies) -> None:
    """Validate the lossless ordered IR without projecting to the flat model."""
    _strict_operator_spelling(ir, v)
    allowed_elisions: set[int] = set()
    _strict_binary_operands(ir, v, allowed_elisions)
    _strict_flux_surface_reductions(ir, v)
    _strict_expression_kind(ir, v, allowed_elisions)
    rendered = compose(ir)
    if rendered != name:
        raise ParseError(
            f"name is not canonical: rendered ordered expression is {rendered!r}"
        )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def parse(
    name: str,
    vocabs: Vocabularies | None = None,
    *,
    strict: bool = False,
) -> ParseResult:
    """Parse ``name`` into a :class:`ParseResult`.

    Raises :class:`ParseError` when the residue cannot be resolved
    against the closed base vocabulary. With ``strict=True``, additionally
    validate the lossless ordered IR against operator registry metadata,
    closed operand vocabulary, generic-base qualification, recursive
    flux-surface semantics, and canonical spelling. Strict validation does not
    project through the flat :class:`StandardName` model, so every operator in
    a nested expression remains structurally visible.
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

    # Trailing-postfix pass.
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
        if _postfix_belongs_to_an_operator_operand(s, v):
            # Leave it for the leading application's operand parse; hoisting it
            # here would reverse the authored operator order.
            break
        trailing_postfix.append(op_app)
        s = new_s

    # Mechanism pass.
    mechanism, s = _strip_mechanism(s)

    # Locus pass.
    locus, s, locus_diags = _strip_locus(s, v)
    diagnostics.extend(locus_diags)

    # Operator-peeling pass (outermost layer after locus/mechanism).
    # Trailing postfix operators peeled first are the outermost wrap and
    # precede anything peeled here (a prefix/binary operator-of form).
    operator_stack: list[OperatorApplication] = list(trailing_postfix)
    binary_terminator: OperatorApplication | None = None
    while True:
        op_app, new_s, _ = _peel_outer_operator(s, v, diagnostics)
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
        # The full operator stack — trailing postfix plus any
        # prefix operators peeled before the binary terminator — wraps the
        # binary result, outermost first.
        ir = StandardNameIR(
            operators=[*operator_stack, binary_terminator],
            base=QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY),
            locus=locus,
            mechanism=mechanism,
        )
        result = ParseResult(ir=ir, diagnostics=diagnostics)
        if strict:
            _strict_validate(name, result.ir, v)
        return result

    # Base-resolution pass: carrier > base > axis (projection) > qualifier.
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
    result = ParseResult(ir=ir, diagnostics=diagnostics)
    if strict:
        _strict_validate(name, result.ir, v)
    return result


def validate_round_trip(name: str, vocabs: Vocabularies | None = None) -> bool:
    """Return ``True`` iff ``compose(parse(name).ir) == name``.

    Raises :class:`ParseError` when the name fails to parse. Otherwise
    compares the rendered form against the input byte-for-byte.

    IR-diagnostics tool only — not a validity oracle. It runs on the lenient
    IR parser and answers "does this name render back to itself?", which is
    weaker than validity: it does not enforce segment compatibility, the
    generic-base gate, or the flux-surface reduction gate. Use
    :func:`parse` with ``strict=True`` for a lossless ordered operator
    expression, or
    :func:`imas_standard_names.grammar.model.parse_standard_name` for a name
    representable by the flat model. Use this helper only to locate IR
    parse/compose round-trip drift.
    """

    result = parse(name, vocabs=vocabs)
    try:
        rendered = compose(result.ir)
    except Exception:
        return False
    return rendered == name
