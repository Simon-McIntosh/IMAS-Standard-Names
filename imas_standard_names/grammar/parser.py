"""Grammar vNext parser (plan 38 / W2b deliverable).

Implements a *staged, liberal* parser that turns a standard-name string
into a :class:`~imas_standard_names.grammar.ir.StandardNameIR` plus a
list of :class:`Diagnostic` records. The parser is the inverse of
:func:`imas_standard_names.grammar.render.compose`; together they form
the round-trip pair required by plan 38.

Parsing is driven by closed vocabularies loaded from
``grammar/vocabularies/*.yml`` via :mod:`vocab_loaders`. Callers may
inject their own :class:`Vocabularies` bundle for testing.

Algorithm (plan §A8)::

    1. Strip trailing _due_to_<process>                -> mechanism
    2. Strip trailing _of_/_at_/_over_<locus>          -> locus
       (longest registry-backed match; _at_ and _over_
       may fall back with a vocab_gap diagnostic)
    3. Strip projection  (prefix <axis>_component_of_  -> projection
       or <axis>_coordinate_of_; canonical emitted by
       compose() is the PREFIX form)
    4. Peel outer operators right-to-outermost         -> operators
       a) unary_postfix (longest match at end)
       b) unary_prefix  (longest match `<op>_of_...`)
       c) binary        (`<binary_op>_of_<A>_<sep>_<B>`)
       repeat until no operator peels
    5. Strip closed qualifier prefixes                  -> qualifiers
    6. Match residue against physical_bases U
       geometry_carriers                                -> base

Liberal acceptance: the parser accepts grammatically valid vNext forms
only. Unknown base residues raise :class:`ParseError` with top-3
edit-distance suggestions. No rc20 open-fallback behaviour is retained.
"""

from __future__ import annotations

import warnings
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
    loci: Mapping[str, tuple[LocusType, frozenset[LocusRelation]]] = field(
        default_factory=dict
    )
    operators: Mapping[str, dict[str, Any]] = field(default_factory=dict)
    bases: frozenset[str] = field(default_factory=frozenset)
    carriers: frozenset[str] = field(default_factory=frozenset)
    qualifiers: frozenset[str] = field(default_factory=frozenset)

    def base_universe(self) -> frozenset[str]:
        return self.bases | self.carriers

    def closed_universe(self) -> frozenset[str]:
        return (
            self.bases
            | self.carriers
            | self.qualifiers
            | frozenset(self.axes)
            | frozenset(self.operators)
            | frozenset(self.loci)
        )


def _normalise_separator(sep: str | None) -> str | None:
    if sep is None:
        return None
    return sep.strip("_") or None


def load_default_vocabularies() -> Vocabularies:
    """Load all five vNext vocabularies from YAML into a :class:`Vocabularies`.

    Falls back to an empty set for any registry whose YAML stub is empty
    (physical_bases.yml, geometry_carriers.yml are populated by W2a).
    """

    axes_reg = vocab_loaders.load_coordinate_axes()
    loci_reg = vocab_loaders.load_locus_registry()
    ops_reg = vocab_loaders.load_operators()
    bases_reg = vocab_loaders.load_physical_bases()
    carriers_reg = vocab_loaders.load_geometry_carriers()

    loci: dict[str, tuple[LocusType, frozenset[LocusRelation]]] = {}
    for token, entry in loci_reg.loci.items():
        locus_type = LocusType(entry.type)
        allowed = frozenset(LocusRelation(r) for r in entry.allowed_relations)
        loci[token] = (locus_type, allowed)

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
        }

    return Vocabularies(
        axes=frozenset(axes_reg.axes),
        loci=loci,
        operators=operators,
        bases=frozenset(bases_reg.bases),
        carriers=frozenset(carriers_reg.carriers),
        qualifiers=frozenset(),  # W2a populates via species/source_entity closure
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


def _strip_locus(
    s: str, v: Vocabularies
) -> tuple[LocusRef | None, str, list[Diagnostic]]:
    """Strip a trailing locus suffix.

    Preference order: rightmost registry-backed ``_<rel>_<token>`` match.
    ``_at_`` and ``_over_`` have no operator collisions, so an unregistered
    token still strips with a ``vocab_gap`` diagnostic. ``_of_`` without a
    registry hit is LEFT alone so step-4 operator peeling can resolve it
    as a binary-operator template.
    """

    diagnostics: list[Diagnostic] = []

    # 1. Registry-backed rightmost match.
    best: tuple[str, int, str] | None = None
    for rel in ("over", "at", "of"):
        marker = f"_{rel}_"
        idx = s.rfind(marker)
        while idx > 0:
            token = s[idx + len(marker) :]
            if token and token in v.loci:
                if best is None or idx > best[1]:
                    best = (rel, idx, token)
                break
            idx = s.rfind(marker, 0, idx)

    if best is not None:
        rel_str, idx, token = best
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
        locus = LocusRef(relation=relation, token=token, type=locus_type)
        return locus, s[:idx], diagnostics

    # 2. Unregistered-but-unambiguous fallback for _at_ / _over_.
    for rel, default_type in (
        ("at", LocusType.POSITION),
        ("over", LocusType.REGION),
    ):
        marker = f"_{rel}_"
        idx = s.rfind(marker)
        if idx <= 0:
            continue
        token = s[idx + len(marker) :]
        if not token or not TOKEN_PATTERN.match(token):
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


def _strip_projection(
    s: str, v: Vocabularies
) -> tuple[AxisProjection | None, str, list[Diagnostic]]:
    """Strip a ``<axis>_component_of_…`` or ``<axis>_coordinate_of_…`` prefix.

    This is the canonical (prefix) projection form emitted by
    :func:`compose`. Postfix projection is intentionally NOT accepted here
    — it yields an IR that does not round-trip.
    """

    diagnostics: list[Diagnostic] = []
    for shape_str, shape in (
        ("component", ProjectionShape.COMPONENT),
        ("coordinate", ProjectionShape.COORDINATE),
    ):
        for axis in v.axes:
            prefix = f"{axis}_{shape_str}_of_"
            if s.startswith(prefix):
                remainder = s[len(prefix) :]
                if not remainder:
                    continue
                return (
                    AxisProjection(axis=axis, shape=shape),
                    remainder,
                    diagnostics,
                )
    # Vocab-gap check: if the string contains `_component_of_` or
    # `_coordinate_of_` but the axis prefix is not in v.axes, flag it.
    for shape_str in ("component", "coordinate"):
        marker = f"_{shape_str}_of_"
        if marker in s:
            head, _, _ = s.partition(marker)
            if head and "_" not in head and head not in v.axes and v.axes:
                diagnostics.append(
                    Diagnostic(
                        category="vocab_gap",
                        layer="parser",
                        message=(
                            f"axis {head!r} not in coordinate_axes registry "
                            f"(expected one of {sorted(v.axes)})"
                        ),
                        severity="info",
                    )
                )
                break
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
        sep_idx = rest.find(sep_marker)
        while sep_idx > 0:
            a_str = rest[:sep_idx]
            b_str = rest[sep_idx + len(sep_marker) :]
            if not a_str or not b_str:
                break
            try:
                a_ir = parse(a_str, vocabs=v).ir
                b_ir = parse(b_str, vocabs=v).ir
            except ParseError:
                sep_idx = rest.find(sep_marker, sep_idx + 1)
                continue
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


def _match_base_with_qualifiers(
    s: str, v: Vocabularies
) -> tuple[QuantityOrCarrier, list[Qualifier]]:
    """Match ``s`` as ``[qualifier_]*(base|carrier)``.

    Tries the longest-match base first; only strips qualifier prefixes
    when the full string is not itself a registered base/carrier. This
    preserves compound bases like ``electron_pressure`` when they are
    explicitly registered.
    """

    if s in v.bases:
        return QuantityOrCarrier(token=s, kind=BaseKind.QUANTITY), []
    if s in v.carriers:
        return QuantityOrCarrier(token=s, kind=BaseKind.GEOMETRY), []

    parts = s.split("_")
    for split in range(1, len(parts)):
        prefix = "_".join(parts[:split])
        rest = "_".join(parts[split:])
        if prefix not in v.qualifiers:
            continue
        if not rest:
            continue
        try:
            base, deeper = _match_base_with_qualifiers(rest, v)
        except ParseError:
            continue
        return base, [Qualifier(token=prefix), *deeper]

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
            f"name {name!r} is not a valid vNext token (must be lowercase snake_case)"
        )

    v = vocabs if vocabs is not None else _default_vocabs()
    diagnostics: list[Diagnostic] = []

    # Stage 1: mechanism
    mechanism, s = _strip_mechanism(name)

    # Stage 2: locus
    locus, s, locus_diags = _strip_locus(s, v)
    diagnostics.extend(locus_diags)

    # Stage 3: operator peeling (outermost layer after locus/mechanism).
    operator_stack: list[OperatorApplication] = []
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

    # Stage 4: projection (prefix form only — matches compose() output).
    # Inside the operator shell, the core has: projection + qualifiers + base.
    projection: AxisProjection | None = None
    proj_diags: list[Diagnostic] = []
    if binary_terminator is None:
        projection, s, proj_diags = _strip_projection(s, v)
        diagnostics.extend(proj_diags)

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
        ir = StandardNameIR(
            operators=[binary_terminator],
            base=QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY),
            locus=locus,
            mechanism=mechanism,
        )
        return ParseResult(ir=ir, diagnostics=diagnostics)

    # Stage 5 + 6: qualifiers then base
    if not s:
        raise ParseError(
            "empty residue after peeling operators and decorators",
        )
    base, qualifiers = _match_base_with_qualifiers(s, v)

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
    """

    result = parse(name, vocabs=vocabs)
    try:
        rendered = compose(result.ir)
    except Exception:
        return False
    return rendered == name


# ---------------------------------------------------------------------------
# Deprecation wrapper for rc20 parser (plan 38 W2b hand-off to W2c)
# ---------------------------------------------------------------------------


def _install_rc20_deprecation() -> None:
    """Install a DeprecationWarning on the rc20 ``parse_standard_name`` shim.

    Called at import time. Does nothing if the rc20 module is absent
    (build-time code-generation tolerance).
    """

    try:
        from imas_standard_names.grammar import (  # noqa: PLC0415
            support as _rc20_support,
        )
    except Exception:  # pragma: no cover - defensive
        return

    original = getattr(_rc20_support, "parse_standard_name", None)
    if original is None or getattr(original, "_vnext_deprecated", False):
        return

    def _wrapper(name: str, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        warnings.warn(
            "imas_standard_names.grammar.support.parse_standard_name is "
            "deprecated; use imas_standard_names.grammar.parser.parse() "
            "which returns a full StandardNameIR.",
            DeprecationWarning,
            stacklevel=2,
        )
        return original(name, *args, **kwargs)

    _wrapper._vnext_deprecated = True  # type: ignore[attr-defined]
    _wrapper.__wrapped__ = original  # type: ignore[attr-defined]
    _wrapper.__name__ = getattr(original, "__name__", "parse_standard_name")
    _wrapper.__doc__ = getattr(original, "__doc__", None)
    _rc20_support.parse_standard_name = _wrapper  # type: ignore[attr-defined]


_install_rc20_deprecation()
