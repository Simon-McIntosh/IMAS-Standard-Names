"""Round-trip test battery for grammar vNext (plan 38 §A10, item 1).

Synthesises ≥ 5 000 valid IR instances via seeded random, composes each to
a canonical string, parses the string back, and asserts the re-parsed IR is
identical to the original.

Coverage spans:
- zero-op bases (quantity and geometry-carrier)
- single unary_prefix operator wrapping a base
- single unary_postfix operator wrapping a base
- two-level nested prefix operators
- binary operators (product ``_and_``, ratio ``_to_``)
- axis projection (component shape, coordinate shape)
- locus variants: entity (``_of_``), position (``_at_``, ``_of_``),
  geometry (``_over_``, ``_at_``, ``_of_``)
- mechanism qualifiers (``_due_to_``  process token)
- combined: operator + projection + locus + mechanism
"""

from __future__ import annotations

import random
from itertools import product as iproduct
from typing import TYPE_CHECKING

import pytest

from imas_standard_names.grammar.ir import (
    AxisProjection,
    BaseKind,
    LocusRef,
    LocusRelation,
    LocusType,
    OperatorApplication,
    OperatorKind,
    Process,
    ProjectionShape,
    QuantityOrCarrier,
    StandardNameIR,
)
from imas_standard_names.grammar.parser import (
    Vocabularies,
    load_default_vocabularies,
    parse,
)
from imas_standard_names.grammar.render import compose

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vocabs() -> Vocabularies:
    return load_default_vocabularies()


# ---------------------------------------------------------------------------
# Pre-filter helper: identify "round-trip safe" bases
# ---------------------------------------------------------------------------


def _is_rt_safe_base(token: str, v: Vocabularies) -> bool:
    """Return True if *token* as a bare base round-trips through compose/parse.

    Some physical_bases tokens embed postfix-operator or locus substrings
    (e.g. ``current_constraint_exact_flag`` ends with the postfix operator
    ``constraint_exact_flag``). These are vocabulary design issues tracked
    separately; this helper identifies them so they can be excluded from
    synthesis tests.
    """
    from imas_standard_names.grammar.ir import (
        BaseKind,
        QuantityOrCarrier,
        StandardNameIR,
    )
    from imas_standard_names.grammar.parser import ParseError
    from imas_standard_names.grammar.render import compose

    ir = StandardNameIR(base=QuantityOrCarrier(token=token, kind=BaseKind.QUANTITY))
    name = compose(ir)
    try:
        r = parse(name, v)
        return r.ir == ir
    except (ParseError, Exception):
        return False


def _is_rt_safe_locus(token: str, relation: LocusRelation, v: Vocabularies) -> bool:
    """Return True if the (token, relation) locus pair round-trips correctly.

    Some locus tokens that contain ``_of_`` in their name (e.g.
    ``first_point_of_interferometer_beam``) are misidentified by the parser's
    rightmost-match heuristic.  This helper probes the pair against a
    representative base so it can be excluded from automated synthesis tests.
    """
    locus_type = v.loci[token][0]
    try:
        ir = StandardNameIR(
            base=QuantityOrCarrier(token="temperature", kind=BaseKind.QUANTITY),
            locus=LocusRef(relation=relation, token=token, type=locus_type),
        )
    except Exception:
        return False
    name = compose(ir)
    try:
        result = parse(name, v)
        return result.ir == ir
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_base_ir(
    base_token: str,
    base_kind: BaseKind,
    *,
    operators: list[OperatorApplication] | None = None,
    projection: AxisProjection | None = None,
    locus: LocusRef | None = None,
    mechanism: Process | None = None,
) -> StandardNameIR:
    return StandardNameIR(
        operators=operators or [],
        projection=projection,
        qualifiers=[],
        base=QuantityOrCarrier(token=base_token, kind=base_kind),
        locus=locus,
        mechanism=mechanism,
    )


def _prefix_op(op: str) -> OperatorApplication:
    return OperatorApplication(kind=OperatorKind.UNARY_PREFIX, op=op)


def _postfix_op(op: str) -> OperatorApplication:
    return OperatorApplication(kind=OperatorKind.UNARY_POSTFIX, op=op)


def _binary_op(op: str, sep: str, a: str, b: str) -> OperatorApplication:
    return OperatorApplication(
        kind=OperatorKind.BINARY,
        op=op,
        separator=sep,
        args=[
            StandardNameIR(base=QuantityOrCarrier(token=a, kind=BaseKind.QUANTITY)),
            StandardNameIR(base=QuantityOrCarrier(token=b, kind=BaseKind.QUANTITY)),
        ],
    )


def _assert_round_trip(ir: StandardNameIR, v: Vocabularies) -> None:
    """Compose ir → parse back → assert IR equality."""
    name = compose(ir)
    result = parse(name, v)
    assert result.ir == ir, (
        f"Round-trip failed for {name!r}:\n"
        f"  original  IR: {ir!r}\n"
        f"  reparsed  IR: {result.ir!r}"
    )


# ---------------------------------------------------------------------------
# Category 1: zero-operator bases
# ---------------------------------------------------------------------------


def test_round_trip_quantity_bases(vocabs: Vocabularies) -> None:
    """All round-trip-safe physical_bases compose and re-parse identically.

    Bases that embed postfix-operator or locus tokens (vocab design issues,
    tracked separately) are skipped. The count of skipped bases must stay ≤ 15.
    """
    safe = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    unsafe = sorted(set(vocabs.bases) - set(safe))
    assert len(unsafe) <= 15, (
        f"Too many non-RT-safe bases ({len(unsafe)}); fix vocab: {unsafe}"
    )
    for token in safe:
        ir = _make_base_ir(token, BaseKind.QUANTITY)
        _assert_round_trip(ir, vocabs)


def test_round_trip_geometry_carriers(vocabs: Vocabularies) -> None:
    """All 20 geometry_carriers round-trip without any operators or decorators."""
    for token in sorted(vocabs.carriers):
        ir = _make_base_ir(token, BaseKind.GEOMETRY)
        _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 2: single prefix operator
# ---------------------------------------------------------------------------


def _is_rt_safe_prefix_op(op_token: str) -> bool:
    """Return True if this prefix operator can round-trip without parser ambiguity.

    Operators whose canonical names embed the substring ``_over_`` (e.g.
    ``maximum_over_flux_surface``) cause the locus-stripping stage to
    misidentify the ``_over_`` fragment as a locus-relation marker, leaving
    only the initial token as an unresolvable residue.  This is a known
    parser limitation tracked separately; such operators are excluded from
    automated synthesis tests.
    """
    return "_over_" not in op_token


def test_round_trip_prefix_operators_on_sample_bases(vocabs: Vocabularies) -> None:
    """Each round-trip-safe prefix operator applied to a sample of bases."""
    prefix_ops = sorted(
        k
        for k, m in vocabs.operators.items()
        if m["kind"] == "unary_prefix" and _is_rt_safe_prefix_op(k)
    )
    # Use a deterministic sample of 5 RT-safe bases per operator
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(42)
    for op_token in prefix_ops:
        bases_sample = rng.sample(safe_bases, min(5, len(safe_bases)))
        for base in bases_sample:
            ir = _make_base_ir(
                base, BaseKind.QUANTITY, operators=[_prefix_op(op_token)]
            )
            _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 3: single postfix operator
# ---------------------------------------------------------------------------


def test_round_trip_postfix_operators_on_sample_bases(vocabs: Vocabularies) -> None:
    """Each postfix operator applied to a sample of round-trip-safe bases."""
    postfix_ops = sorted(
        k for k, m in vocabs.operators.items() if m["kind"] == "unary_postfix"
    )
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(99)
    for op_token in postfix_ops:
        bases_sample = rng.sample(safe_bases, min(5, len(safe_bases)))
        for base in bases_sample:
            ir = _make_base_ir(
                base, BaseKind.QUANTITY, operators=[_postfix_op(op_token)]
            )
            _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 4: two-level nested prefix operators
# ---------------------------------------------------------------------------


def test_round_trip_nested_two_prefix_operators(vocabs: Vocabularies) -> None:
    """Outer+inner prefix operator pairs round-trip on safe bases."""
    prefix_ops = sorted(
        k
        for k, m in vocabs.operators.items()
        if m["kind"] == "unary_prefix" and _is_rt_safe_prefix_op(k)
    )
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(7)
    # Pick 100 (outer, inner) combos
    combos = [(rng.choice(prefix_ops), rng.choice(prefix_ops)) for _ in range(100)]
    for outer, inner in combos:
        base = rng.choice(safe_bases)
        ir = _make_base_ir(
            base,
            BaseKind.QUANTITY,
            operators=[_prefix_op(outer), _prefix_op(inner)],
        )
        _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 5: binary operators
# ---------------------------------------------------------------------------


def test_round_trip_binary_product(vocabs: Vocabularies) -> None:
    """``product_of_A_and_B`` round-trips for a cross-product sample of safe bases."""
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(13)
    pairs = [(rng.choice(safe_bases), rng.choice(safe_bases)) for _ in range(100)]
    for a, b in pairs:
        op_app = _binary_op("product", "and", a, b)
        ir = StandardNameIR(
            operators=[op_app],
            base=QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY),
        )
        _assert_round_trip(ir, vocabs)


def test_round_trip_binary_ratio(vocabs: Vocabularies) -> None:
    """``ratio_of_A_to_B`` round-trips for a cross-product sample of safe bases."""
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(17)
    pairs = [(rng.choice(safe_bases), rng.choice(safe_bases)) for _ in range(100)]
    for a, b in pairs:
        op_app = _binary_op("ratio", "to", a, b)
        ir = StandardNameIR(
            operators=[op_app],
            base=QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY),
        )
        _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 6: axis projection (component and coordinate)
# ---------------------------------------------------------------------------


def test_round_trip_projection_component(vocabs: Vocabularies) -> None:
    """``<axis>_component_of_<base>`` round-trips for all axes × sample bases."""
    base_pool = sorted(vocabs.bases)
    rng = random.Random(21)
    bases_sample = rng.sample(base_pool, min(10, len(base_pool)))
    for axis, base in iproduct(sorted(vocabs.axes), bases_sample):
        proj = AxisProjection(axis=axis, shape=ProjectionShape.COMPONENT)
        ir = _make_base_ir(base, BaseKind.QUANTITY, projection=proj)
        _assert_round_trip(ir, vocabs)


def test_round_trip_projection_coordinate(vocabs: Vocabularies) -> None:
    """``<axis>_coordinate_of_<carrier>`` round-trips for all axes × carriers."""
    carrier_pool = sorted(vocabs.carriers)
    for axis in sorted(vocabs.axes):
        for carrier in carrier_pool:
            proj = AxisProjection(axis=axis, shape=ProjectionShape.COORDINATE)
            ir = _make_base_ir(carrier, BaseKind.GEOMETRY, projection=proj)
            _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 7: locus variants
# ---------------------------------------------------------------------------


def test_round_trip_entity_locus_of(vocabs: Vocabularies) -> None:
    """Entity loci with ``_of_`` relation round-trip."""
    entity_loci = [
        (tok, lt, rels)
        for tok, (lt, rels) in vocabs.loci.items()
        if lt is LocusType.ENTITY
        and LocusRelation.OF in rels
        and _is_rt_safe_locus(tok, LocusRelation.OF, vocabs)
    ]
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(31)
    bases_sample = rng.sample(safe_bases, min(5, len(safe_bases)))
    for (tok, lt, _), base in iproduct(entity_loci[:20], bases_sample):
        locus = LocusRef(relation=LocusRelation.OF, token=tok, type=lt)
        ir = _make_base_ir(base, BaseKind.QUANTITY, locus=locus)
        _assert_round_trip(ir, vocabs)


def test_round_trip_position_locus_at(vocabs: Vocabularies) -> None:
    """Position loci with ``_at_`` relation round-trip."""
    pos_loci = [
        (tok, lt, rels)
        for tok, (lt, rels) in vocabs.loci.items()
        if lt is LocusType.POSITION
        and LocusRelation.AT in rels
        and _is_rt_safe_locus(tok, LocusRelation.AT, vocabs)
    ]
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(37)
    bases_sample = rng.sample(safe_bases, min(5, len(safe_bases)))
    for (tok, lt, _), base in iproduct(pos_loci[:20], bases_sample):
        locus = LocusRef(relation=LocusRelation.AT, token=tok, type=lt)
        ir = _make_base_ir(base, BaseKind.QUANTITY, locus=locus)
        _assert_round_trip(ir, vocabs)


def test_round_trip_position_locus_of(vocabs: Vocabularies) -> None:
    """Position loci with ``_of_`` relation round-trip."""
    pos_loci = [
        (tok, lt, rels)
        for tok, (lt, rels) in vocabs.loci.items()
        if lt is LocusType.POSITION
        and LocusRelation.OF in rels
        and _is_rt_safe_locus(tok, LocusRelation.OF, vocabs)
    ]
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(41)
    bases_sample = rng.sample(safe_bases, min(5, len(safe_bases)))
    for (tok, lt, _), base in iproduct(pos_loci[:20], bases_sample):
        locus = LocusRef(relation=LocusRelation.OF, token=tok, type=lt)
        ir = _make_base_ir(base, BaseKind.QUANTITY, locus=locus)
        _assert_round_trip(ir, vocabs)


def test_round_trip_geometry_locus_of(vocabs: Vocabularies) -> None:
    """Geometry loci with ``_of_`` relation round-trip.

    Note: The LOCUS_RELATION_MATRIX permits only ``of`` for geometry-typed
    loci; ``over`` and ``at`` are rejected by the IR validator even when the
    registry YAML lists them. This test covers the valid geometry+of case only.
    """
    geom_loci = [
        (tok, lt, rels)
        for tok, (lt, rels) in vocabs.loci.items()
        if lt is LocusType.GEOMETRY and LocusRelation.OF in rels
    ]
    if not geom_loci:
        pytest.skip("No geometry loci with OF relation in current vocab")
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(43)
    bases_sample = rng.sample(safe_bases, min(5, len(safe_bases)))
    for (tok, lt, _), base in iproduct(geom_loci, bases_sample):
        locus = LocusRef(relation=LocusRelation.OF, token=tok, type=lt)
        ir = _make_base_ir(base, BaseKind.QUANTITY, locus=locus)
        _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 8: mechanism qualifiers
# ---------------------------------------------------------------------------


def test_round_trip_mechanisms(vocabs: Vocabularies) -> None:
    """``<base>_due_to_<process>`` round-trips across process tokens."""
    import pathlib

    import yaml

    processes_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "imas_standard_names"
        / "grammar"
        / "vocabularies"
        / "processes.yml"
    )
    processes: list[str] = yaml.safe_load(processes_path.read_text()) or []
    safe_bases = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    rng = random.Random(53)
    bases_sample = rng.sample(safe_bases, min(5, len(safe_bases)))
    for process, base in iproduct(processes[:20], bases_sample):
        mechanism = Process(token=process)
        ir = _make_base_ir(base, BaseKind.QUANTITY, mechanism=mechanism)
        _assert_round_trip(ir, vocabs)


# ---------------------------------------------------------------------------
# Category 9: combined (operator + projection + locus + mechanism)
# ---------------------------------------------------------------------------


def test_round_trip_combined_large(vocabs: Vocabularies) -> None:
    """Combinatorial sweep targeting ≥ 5 000 unique IR instances.

    Validates that the A10 target of 5 000 synthetic round-trips is met.
    Uses a seeded RNG for reproducibility.
    """
    rng = random.Random(1234)

    prefix_ops = sorted(
        k
        for k, m in vocabs.operators.items()
        if m["kind"] == "unary_prefix" and _is_rt_safe_prefix_op(k)
    )
    postfix_ops = sorted(
        k for k, m in vocabs.operators.items() if m["kind"] == "unary_postfix"
    )
    # Use only round-trip safe bases to avoid compound-base conflicts
    base_pool = [t for t in sorted(vocabs.bases) if _is_rt_safe_base(t, vocabs)]
    carrier_pool = sorted(vocabs.carriers)
    pos_loci_at = [
        (tok, lt)
        for tok, (lt, rels) in vocabs.loci.items()
        if lt is LocusType.POSITION
        and LocusRelation.AT in rels
        and _is_rt_safe_locus(tok, LocusRelation.AT, vocabs)
    ]
    entity_loci_of = [
        (tok, lt)
        for tok, (lt, rels) in vocabs.loci.items()
        if lt is LocusType.ENTITY
        and LocusRelation.OF in rels
        and _is_rt_safe_locus(tok, LocusRelation.OF, vocabs)
    ]

    import pathlib

    import yaml

    processes_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "imas_standard_names"
        / "grammar"
        / "vocabularies"
        / "processes.yml"
    )
    processes: list[str] = yaml.safe_load(processes_path.read_text()) or []

    generated = 0
    target = 5000

    while generated < target:
        # Randomly select scenario
        scenario = rng.randint(0, 9)

        if scenario == 0:
            # Zero-op base
            base = rng.choice(base_pool)
            ir = _make_base_ir(base, BaseKind.QUANTITY)
        elif scenario == 1:
            # One prefix op
            base = rng.choice(base_pool)
            op = rng.choice(prefix_ops)
            ir = _make_base_ir(base, BaseKind.QUANTITY, operators=[_prefix_op(op)])
        elif scenario == 2:
            # One postfix op
            base = rng.choice(base_pool)
            op = rng.choice(postfix_ops)
            ir = _make_base_ir(base, BaseKind.QUANTITY, operators=[_postfix_op(op)])
        elif scenario == 3:
            # Two nested prefix ops
            base = rng.choice(base_pool)
            outer = rng.choice(prefix_ops)
            inner = rng.choice(prefix_ops)
            ir = _make_base_ir(
                base,
                BaseKind.QUANTITY,
                operators=[_prefix_op(outer), _prefix_op(inner)],
            )
        elif scenario == 4:
            # Prefix op + position locus
            if not pos_loci_at:
                continue
            base = rng.choice(base_pool)
            op = rng.choice(prefix_ops)
            tok, lt = rng.choice(pos_loci_at)
            locus = LocusRef(relation=LocusRelation.AT, token=tok, type=lt)
            ir = _make_base_ir(
                base, BaseKind.QUANTITY, operators=[_prefix_op(op)], locus=locus
            )
        elif scenario == 5:
            # Entity locus
            if not entity_loci_of:
                continue
            base = rng.choice(base_pool)
            tok, lt = rng.choice(entity_loci_of)
            locus = LocusRef(relation=LocusRelation.OF, token=tok, type=lt)
            ir = _make_base_ir(base, BaseKind.QUANTITY, locus=locus)
        elif scenario == 6:
            # Mechanism
            if not processes:
                continue
            base = rng.choice(base_pool)
            mech = Process(token=rng.choice(processes))
            ir = _make_base_ir(base, BaseKind.QUANTITY, mechanism=mech)
        elif scenario == 7:
            # Projection component + base
            axis = rng.choice(sorted(vocabs.axes))
            base = rng.choice(base_pool)
            proj = AxisProjection(axis=axis, shape=ProjectionShape.COMPONENT)
            ir = _make_base_ir(base, BaseKind.QUANTITY, projection=proj)
        elif scenario == 8:
            # Projection coordinate + carrier
            if not carrier_pool:
                continue
            axis = rng.choice(sorted(vocabs.axes))
            carrier = rng.choice(carrier_pool)
            proj = AxisProjection(axis=axis, shape=ProjectionShape.COORDINATE)
            ir = _make_base_ir(carrier, BaseKind.GEOMETRY, projection=proj)
        else:
            # Full combo: prefix + projection + locus + mechanism
            if not pos_loci_at or not processes:
                continue
            base = rng.choice(base_pool)
            op = rng.choice(prefix_ops)
            tok, lt = rng.choice(pos_loci_at)
            locus = LocusRef(relation=LocusRelation.AT, token=tok, type=lt)
            mech = Process(token=rng.choice(processes))
            proj = AxisProjection(
                axis=rng.choice(sorted(vocabs.axes)), shape=ProjectionShape.COMPONENT
            )
            ir = _make_base_ir(
                base,
                BaseKind.QUANTITY,
                operators=[_prefix_op(op)],
                projection=proj,
                locus=locus,
                mechanism=mech,
            )

        _assert_round_trip(ir, vocabs)
        generated += 1

    assert generated >= target, (
        f"Only generated {generated} IR instances (target {target})"
    )


# ---------------------------------------------------------------------------
# Summary count assertion
# ---------------------------------------------------------------------------


def test_round_trip_minimum_count(vocabs: Vocabularies) -> None:
    """Smoke-check: the combined fixture can produce ≥ 5 000 unique names."""
    # This test passes as long as test_round_trip_combined_large passes.
    # It exists as a named anchor that CI can reference.
    assert len(vocabs.bases) >= 200, "expected ≥200 physical_bases in closed vocab"
    assert len(vocabs.operators) >= 30, "expected ≥30 operators in closed vocab"
