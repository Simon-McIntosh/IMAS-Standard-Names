"""A flux-surface reduction wrapping a binary-operator form.

The equilibrium metric coefficients are flux-surface averages OF A RATIO, not
ratios of flux-surface averages:

    <|grad rho|^2 / R^2>    (DD unit m^-2)
    <|grad rho|^2 / B^2>    (DD unit T^-2)

Expressing them needs a reduction operator to wrap a binary form. The reduction
spells BARE (``flux_surface_averaged_<inner>``), so the operator has to survive
parse as a first-class segment while still rendering without an ``_of_`` joiner.

Scope of the relaxation exercised here:

* The PARSER accepts any bare-prefix unary operator in front of a binary form.
  A uniform spelling rule keeps physics policy out of the tokenizer and yields a
  domain-specific rejection message instead of "residue does not match any base".
* The VALIDITY ORACLE (``parse_standard_name``) admits only a FLUX-SURFACE
  REDUCTION operator over a binary form. A non-reduction bare prefix
  (``volume_averaged``, ``normalized``, ...) parses at the IR level and is then
  refused by the flat model, whose ``binary_operator`` stays exclusive with every
  other transformation. Widening that to the whole averaging family is a
  vocabulary-flag decision, not a code change.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.ir import OperatorKind
from imas_standard_names.grammar.model import parse_standard_name
from imas_standard_names.grammar.parser import (
    ParseError,
    Vocabularies,
    load_default_vocabularies,
    parse,
)
from imas_standard_names.grammar.render import compose

GRADIENT_OVER_SQUARE_MAJOR_RADIUS = (
    "flux_surface_averaged_ratio_of"
    "_square_toroidal_flux_coordinate_gradient_magnitude"
    "_to_square_major_radius"
)
GRADIENT_OVER_SQUARE_FIELD = (
    "flux_surface_averaged_ratio_of"
    "_square_toroidal_flux_coordinate_gradient_magnitude"
    "_to_square_magnetic_field_magnitude"
)

METRIC_COEFFICIENT_NAMES = (
    GRADIENT_OVER_SQUARE_MAJOR_RADIUS,
    GRADIENT_OVER_SQUARE_FIELD,
)


@pytest.fixture(scope="module")
def vocabs() -> Vocabularies:
    return load_default_vocabularies()


# ---------------------------------------------------------------------------
# Parse + round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", METRIC_COEFFICIENT_NAMES)
def test_metric_coefficient_parses(name: str, vocabs: Vocabularies) -> None:
    parse(name, vocabs=vocabs)


@pytest.mark.parametrize("name", METRIC_COEFFICIENT_NAMES)
def test_metric_coefficient_round_trips(name: str, vocabs: Vocabularies) -> None:
    """compose(parse(name)) reproduces the input byte-for-byte."""
    assert compose(parse(name, vocabs=vocabs).ir) == name


@pytest.mark.parametrize("name", METRIC_COEFFICIENT_NAMES)
def test_metric_coefficient_is_valid(name: str) -> None:
    """The strict oracle accepts it, so the canonical spelling is exactly this."""
    model = parse_standard_name(name)
    assert model.transformation == "flux_surface_averaged"
    assert model.binary_operator == "ratio_of"


# ---------------------------------------------------------------------------
# The reduction must be a VISIBLE segment, not glued into a base token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", METRIC_COEFFICIENT_NAMES)
def test_reduction_is_a_distinct_operator_segment(
    name: str, vocabs: Vocabularies
) -> None:
    """The reduction is its own IR operator wrapping the binary application.

    A reduction absorbed into the base string (physical_base
    ``flux_surface_averaged_...``) would be invisible to the flux-surface
    reduction gate, which keys off operator and qualifier tokens. Assert the
    segment structure, not just the rendered string.
    """
    ir = parse(name, vocabs=vocabs).ir
    kinds = [(op.kind, op.op) for op in ir.operators]
    assert (OperatorKind.UNARY_PREFIX, "flux_surface_averaged") in kinds
    assert any(kind is OperatorKind.BINARY and op == "ratio" for kind, op in kinds)
    # The reduction wraps the binary application, not the reverse.
    reduction_at = kinds.index((OperatorKind.UNARY_PREFIX, "flux_surface_averaged"))
    binary_at = next(
        i for i, (kind, _) in enumerate(kinds) if kind is OperatorKind.BINARY
    )
    assert reduction_at < binary_at
    # No reduction token smuggled into the base or the qualifier list.
    assert "flux_surface_averaged" not in ir.base.token
    assert all("flux_surface_averaged" != q.token for q in ir.qualifiers)


def test_operand_postfix_stays_inside_the_operand(vocabs: Vocabularies) -> None:
    """A trailing ``magnitude`` belongs to the second operand, not the ratio.

    ``ratio_of_A_to_square_magnetic_field_magnitude`` renders identically whether
    the magnitude is read as the ratio's postfix or as part of operand B, so the
    grammar has to pick one. The magnitude of a ratio of scalars is meaningless
    (``magnitude`` takes vector/complex), so the operand reading is the only
    sound one — and it is the reading that keeps the second operand intact.
    """
    ir = parse(GRADIENT_OVER_SQUARE_FIELD, vocabs=vocabs).ir
    binary = next(op for op in ir.operators if op.kind is OperatorKind.BINARY)
    assert compose(binary.args[1]) == "square_magnetic_field_magnitude"
    assert not any(op.kind is OperatorKind.UNARY_POSTFIX for op in ir.operators)


# ---------------------------------------------------------------------------
# The no-op reduction gate must survive the relaxation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        # flux function as the FIRST operand only
        "flux_surface_averaged_ratio_of_safety_factor_to_square_major_radius",
        # flux function as the SECOND operand only
        "flux_surface_averaged_ratio_of_square_major_radius_to_safety_factor",
        # both operands flux functions
        "flux_surface_averaged_ratio_of_safety_factor_to_magnetic_shear",
    ],
)
def test_reduction_over_binary_refuses_a_flux_function_operand(name: str) -> None:
    """The gate must name the flagged base, and must fire on a single operand.

    ``safety_factor`` and ``magnetic_shear`` are constant on a flux surface, so a
    reduction over a ratio built from one either has nothing to average (both
    operands constant) or factors out of that operand — and the factored spelling
    is the one to register. The gate must see through the binary application to
    reach it: the outer IR carries a placeholder base, so a test that only
    asserted "raises somehow" would pass for the wrong reason.
    """
    with pytest.raises(ValueError) as excinfo:
        parse_standard_name(name)
    message = str(excinfo.value)
    assert "constant on a flux surface" in message
    flagged = "safety_factor" if "safety_factor" in name else "magnetic_shear"
    assert f"cannot apply to '{flagged}'" in message


def test_reduction_over_a_non_flux_function_binary_is_accepted() -> None:
    """Control for the gate tests: the gate fires on the base, not on the shape."""
    parse_standard_name(GRADIENT_OVER_SQUARE_MAJOR_RADIUS)


def test_reduction_carries_no_dimensionality_assertion() -> None:
    """The metric coefficients keep their own DD units (m^-2, T^-2).

    ``normalized`` and ``logarithm`` declare ``dimensionless``, and the
    dimension-transforming operators declare a unit change. A flux-surface
    reduction declares neither — it is unit-preserving — so nothing in the
    grammar forces one of these names to unit '1'.
    """
    from imas_standard_names.grammar.vocab_loaders import load_operators

    operators = load_operators().operators
    for token in (
        "flux_surface_averaged",
        "maximum_over_flux_surface",
        "minimum_over_flux_surface",
    ):
        definition = operators[token]
        assert definition.flux_surface_reduction is True
        assert definition.dimensionless is False
        assert definition.dimension_transforming is False


# ---------------------------------------------------------------------------
# Non-reduction transformations over a binary form
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reduction",
    ["flux_surface_averaged", "maximum_over_flux_surface", "minimum_over_flux_surface"],
)
def test_every_flux_surface_reduction_wraps_a_binary_form(reduction: str) -> None:
    """The widened class is exactly the operators flagged ``flux_surface_reduction``.

    All three share the bare spelling and the outermost render position, so the
    relaxation covers them uniformly rather than singling out the averaging one.
    """
    name = f"{reduction}_ratio_of_electron_density_to_square_major_radius"
    model = parse_standard_name(name)
    assert model.transformation == reduction
    assert model.binary_operator == "ratio_of"


@pytest.mark.parametrize(
    "prefix",
    [
        # bare-spelling transformations that are NOT flux-surface reductions
        "volume_averaged",
        "line_averaged",
        "time_averaged",
        "normalized",
        "perturbed",
        "change_in",
        # _of_-form transformations
        "logarithm_of",
        "inverse_of",
        "tendency_of",
        "maximum_of",
        "root_mean_square_of",
    ],
)
def test_no_other_transformation_wraps_a_binary_form(prefix: str) -> None:
    """The relaxation does NOT widen beyond flux-surface reductions.

    A non-reduction transformation could sit either side of the operator
    (``normalized`` of a ratio versus a ratio of normalized operands), and the
    flat model has one transformation slot and no wrap-order field, so it stays
    refused. Pin the whole list: silently admitting one of these would let the
    composer emit a name whose structure the model records ambiguously.
    """
    name = f"{prefix}_ratio_of_electron_density_to_square_major_radius"
    with pytest.raises(ValueError, match="not representable in the flat"):
        parse_standard_name(name)


def test_non_reduction_bare_prefix_parses_but_is_not_valid(
    vocabs: Vocabularies,
) -> None:
    """``volume_averaged`` over a binary form parses; the oracle refuses it.

    The parser applies one uniform bare-prefix spelling rule; the flat model
    admits only a flux-surface reduction alongside ``binary_operator``. Refusing
    at the oracle rather than at the tokenizer produces an actionable message.
    """
    name = "volume_averaged_ratio_of_electron_density_to_square_major_radius"
    parse(name, vocabs=vocabs)  # IR layer: accepted
    with pytest.raises(ValueError):
        parse_standard_name(name)


@pytest.mark.parametrize(
    "reduction",
    ["flux_surface_averaged", "maximum_over_flux_surface", "minimum_over_flux_surface"],
)
def test_of_form_reduction_over_binary_is_not_the_canonical_spelling(
    reduction: str,
) -> None:
    """One admissible spelling per name across the whole widened class.

    ``<reduction>_of_ratio_of_...`` parses at the IR level (the generic
    ``<op>_of_`` prefix peel), so without this it would be a second valid
    spelling of a name the bare form already denotes.
    """
    of_form = f"{reduction}_of_ratio_of_electron_density_to_square_major_radius"
    bare_form = f"{reduction}_ratio_of_electron_density_to_square_major_radius"
    parse_standard_name(bare_form)  # the canonical one is accepted
    with pytest.raises(ValueError):
        parse_standard_name(of_form)


# ---------------------------------------------------------------------------
# Ambiguity: the new form cannot be mis-split
# ---------------------------------------------------------------------------


def test_reduction_prefix_is_not_split_as_a_reduction_of_a_ratio_base(
    vocabs: Vocabularies,
) -> None:
    """``ratio`` is not a base, so ``flux_surface_averaged_ratio`` cannot resolve.

    The reduction prefix renders ``<op>_<inner>`` and a binary operator renders
    ``<op>_of_<A>_<sep>_<B>``, so both spell an ``_of_``. The only reading that
    resolves is reduction-over-binary — provided ``ratio`` never becomes a base
    token. Pin that, because a future ``ratio`` base would silently create a
    second parse of every name in this module.
    """
    assert "ratio" not in vocabs.bases
    assert "ratio" not in vocabs.carriers
    with pytest.raises(ParseError):
        parse("flux_surface_averaged_ratio", vocabs=vocabs)


def test_reduction_over_binary_is_distinct_from_the_ratio_of_reductions(
    vocabs: Vocabularies,
) -> None:
    """<A/B> and <A>/<B> are different quantities and must be different names."""
    average_of_ratio = parse(GRADIENT_OVER_SQUARE_MAJOR_RADIUS, vocabs=vocabs).ir
    ratio_of_averages = parse(
        "ratio_of_flux_surface_averaged_square_toroidal_flux_coordinate_gradient_magnitude"
        "_to_flux_surface_averaged_square_major_radius",
        vocabs=vocabs,
    ).ir
    assert average_of_ratio != ratio_of_averages
    assert compose(average_of_ratio) != compose(ratio_of_averages)


def test_separator_inside_an_operand_does_not_mis_split(vocabs: Vocabularies) -> None:
    """The ``_to_`` split must not land inside a base that contains ``to``.

    The binary split walks candidate separator positions right-to-left and keeps
    the first whose BOTH sides resolve, so a base token containing the separator
    word cannot strand an unresolvable operand.
    """
    ir = parse(GRADIENT_OVER_SQUARE_MAJOR_RADIUS, vocabs=vocabs).ir
    binary = next(op for op in ir.operators if op.kind is OperatorKind.BINARY)
    assert compose(binary.args[0]) == (
        "square_toroidal_flux_coordinate_gradient_magnitude"
    )
    assert compose(binary.args[1]) == "square_major_radius"


def test_bare_reduction_prefix_over_a_plain_base_is_unchanged(
    vocabs: Vocabularies,
) -> None:
    """The new peel must not steal the qualifier reading of a non-binary name.

    ``flux_surface_averaged_electron_density`` has no binary form after the
    prefix, so the reduction stays a qualifier and the name keeps its existing
    IR shape.
    """
    ir = parse("flux_surface_averaged_electron_density", vocabs=vocabs).ir
    assert not ir.operators
    assert [q.token for q in ir.qualifiers] == ["flux_surface_averaged", "electron"]
