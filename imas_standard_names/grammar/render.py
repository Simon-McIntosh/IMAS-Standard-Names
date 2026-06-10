"""Grammar canonical renderer (strict generator).

Plan 38 / W1a deliverable. Implements :func:`compose` — a pure function
that maps a :class:`StandardNameIR` to its single canonical string form.
There are no fallbacks: malformed IR raises :class:`RenderError`.

The renderer is deliberately isolated from vocabulary resolution. It
consumes validated IR structures (see :mod:`imas_standard_names.grammar.ir`)
and emits token strings; vocabulary lookups happen at parse time in W2b.

See the grammar specification §4 for the template spec.
"""

from __future__ import annotations

from collections.abc import Iterable

from imas_standard_names.grammar.ir import (
    AxisProjection,
    LocusRef,
    OperatorApplication,
    OperatorKind,
    Process,
    Qualifier,
    StandardNameIR,
    assert_binary_has_separator,
    assert_locus_is_trailing,
    assert_operator_of_form,
)

__all__ = [
    "RenderError",
    "compose",
    "render_mechanism",
    "render_operators",
    "render_projection",
    "render_qualifiers",
    "render_locus",
]


class RenderError(ValueError):
    """Raised when the generator cannot produce a canonical form."""


# ---------------------------------------------------------------------------
# Leaf renderers
# ---------------------------------------------------------------------------


def render_projection(projection: AxisProjection | None) -> str:
    """Render a projection as the axis prefix token.

    Both COMPONENT and COORDINATE shapes render identically as just
    ``<axis>`` — the ``_component_of_`` / ``_coordinate_of_`` long forms
    are removed. The caller joins this with the base via ``_``.

    Returns an empty string when ``projection`` is ``None``.
    """

    if projection is None:
        return ""
    return projection.axis


def render_qualifiers(qualifiers: Iterable[Qualifier]) -> str:
    """Render qualifiers in parse order (insertion order).

    Qualifiers are emitted in the order they appear in the IR list,
    which matches the left-to-right order extracted by the parser.
    This ensures parse→compose round-trip fidelity.

    Returns an empty string when no qualifiers are present. Otherwise
    returns the tokens joined by ``_`` with no leading or trailing
    underscore; the caller is responsible for gluing it onto the base.
    """

    tokens = [q.token for q in qualifiers]
    return "_".join(tokens)


def render_locus(locus: LocusRef | None) -> str:
    """Render a locus as ``_<relation>_<token>[_equal_to_<value>]``.

    Returns an empty string when ``locus`` is ``None``. Relation/type
    compatibility and value constraints are enforced by :class:`LocusRef`'s
    own validators.
    """

    if locus is None:
        return ""
    rendered = f"_{locus.relation.value}_{locus.token}"
    if locus.value is not None:
        rendered += f"_equal_to_{locus.value}"
    return rendered


def render_mechanism(mechanism: Process | None) -> str:
    """Render a mechanism as ``_due_to_<process>``.

    Returns an empty string when ``mechanism`` is ``None``.
    """

    if mechanism is None:
        return ""
    return f"_due_to_{mechanism.token}"


# ---------------------------------------------------------------------------
# Base + inner-IR rendering
# ---------------------------------------------------------------------------


def _render_base_with_decorators(ir: StandardNameIR) -> str:
    """Render the projection + qualifiers + base + locus + mechanism core.

    This is the inner function the operator stack wraps around. It does
    **not** include operator decoration. See :func:`render_operators`.
    """

    parts: list[str] = []

    # Short form: both COMPONENT and COORDINATE render as ``<axis>_<rest>``
    projection_str = render_projection(ir.projection)
    if projection_str:
        parts.append(projection_str)

    qualifiers_str = render_qualifiers(ir.qualifiers)
    if qualifiers_str:
        parts.append(qualifiers_str)

    parts.append(ir.base.token)

    core = "_".join(parts)

    # Locus and mechanism are suffixes; their leading underscore is baked in.
    core += render_locus(ir.locus)
    core += render_mechanism(ir.mechanism)
    return core


# ---------------------------------------------------------------------------
# Operator stack rendering
# ---------------------------------------------------------------------------


def _render_operator_stack(
    operators: list[OperatorApplication],
    inner: str,
    enclosing_ir: StandardNameIR,
) -> str:
    """Recursively apply the operator stack outer-to-inner.

    ``operators[0]`` is the outermost operator. ``inner`` is the rendered
    form to be decorated by the remaining stack. ``enclosing_ir`` is the
    IR whose base produced ``inner`` — used for diagnostics only.
    """

    if not operators:
        return inner

    op = operators[0]
    rest = operators[1:]

    if op.kind is OperatorKind.UNARY_PREFIX:
        # If the operator carries an explicit sub-IR arg, render that arg
        # as the operator's operand instead of the inner stream. This is
        # how nested operator trees are represented (args: [sub_ir]).
        if op.args:
            operand = compose(op.args[0])
        else:
            operand = _render_operator_stack(rest, inner, enclosing_ir)
            rest = []
        assert_operator_of_form(op, registry=None)
        outer = f"{op.op}_of_{operand}"
        # Any remaining operators in ``rest`` still need to wrap the result.
        return _render_operator_stack(rest, outer, enclosing_ir)

    if op.kind is OperatorKind.UNARY_POSTFIX:
        if op.args:
            operand = compose(op.args[0])
        else:
            operand = _render_operator_stack(rest, inner, enclosing_ir)
            rest = []
        outer = f"{operand}_{op.op}"
        return _render_operator_stack(rest, outer, enclosing_ir)

    if op.kind is OperatorKind.BINARY:
        assert_binary_has_separator(op, registry=None)
        if len(op.args) != 2:  # pragma: no cover - guarded by IR validator
            raise RenderError(
                f"binary operator {op.op!r} requires 2 args, got {len(op.args)}"
            )
        a = compose(op.args[0])
        b = compose(op.args[1])
        outer = f"{op.op}_of_{a}_{op.separator}_{b}"
        return _render_operator_stack(rest, outer, enclosing_ir)

    raise RenderError(  # pragma: no cover - StrEnum is exhaustive
        f"unknown operator kind {op.kind!r} for operator {op.op!r}"
    )


def render_operators(
    operators: list[OperatorApplication],
    inner: str,
    enclosing_ir: StandardNameIR | None = None,
) -> str:
    """Public operator-stack renderer.

    ``enclosing_ir`` is optional and used only for error messages. When the
    caller has no enclosing IR (e.g. a test calling this helper directly)
    a placeholder IR may be omitted.
    """

    if not operators:
        return inner
    if enclosing_ir is None:
        # Build a trivial no-op context: we need only identity for diagnostics.
        enclosing_ir = operators[0].args[0] if operators[0].args else None  # type: ignore[assignment]
    return _render_operator_stack(operators, inner, enclosing_ir)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Top-level compose
# ---------------------------------------------------------------------------


def compose(ir: StandardNameIR) -> str:
    """Render ``ir`` into its single canonical string form.

    Raises :class:`RenderError` when the IR is structurally inconsistent
    beyond what the Pydantic validators already catch (e.g. a trailing
    locus that the operator stack has displaced).
    """

    if not isinstance(ir, StandardNameIR):  # pragma: no cover - type guard
        raise RenderError(
            f"compose() expects a StandardNameIR, got {type(ir).__name__}"
        )

    try:
        inner = _render_base_with_decorators(ir)
        rendered = _render_operator_stack(list(ir.operators), inner, ir)
    except RenderError:
        raise
    except ValueError as exc:
        raise RenderError(str(exc)) from exc

    # Binary operators replace `inner` entirely, losing any locus/mechanism
    # that was rendered into `inner` by _render_base_with_decorators.
    # Re-append them from the top-level IR.
    if any(op.kind is OperatorKind.BINARY for op in ir.operators):
        rendered += render_locus(ir.locus)
        rendered += render_mechanism(ir.mechanism)

    # Safety net: enforce the §A3 trailing-locus rule on the final string.
    # When the outermost operator pushes text after the locus suffix, the
    # resulting name violates the trailing-position invariant and must be
    # rejected rather than emitted.
    if ir.locus is not None and not ir.operators:
        try:
            assert_locus_is_trailing(rendered, ir)
        except ValueError as exc:
            raise RenderError(str(exc)) from exc
    return rendered
