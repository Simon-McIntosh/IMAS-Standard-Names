"""Ambiguity harness for grammar vNext (plan 38 §A10, item 2).

Provides 50 curated pairs of standard names that MUST parse to distinct IR
objects under the vNext parser. Each pair is documented with the specific
IR attribute that distinguishes it.

The pairs cover:
- Locus relation variants (``_at_`` vs ``_of_`` for same token)
- Operator kind variants (unary_prefix vs unary_postfix)
- Different operators on the same base
- Nested operator ordering (outer/inner swapped)
- Binary operator type (``product`` vs ``ratio``)
- Presence vs absence of locus
- Presence vs absence of mechanism
- Different mechanisms on the same base
- Different loci on the same base
- Different axes (radial vs toroidal projection)
- Projection present vs absent
- Operator + locus vs just locus
- Operator + mechanism vs just mechanism
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.parser import (
    Vocabularies,
    load_default_vocabularies,
    parse,
)

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vocabs() -> Vocabularies:
    return load_default_vocabularies()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_distinct_ir(name_a: str, name_b: str, vocabs: Vocabularies) -> None:
    """Assert that *name_a* and *name_b* parse to different IR objects."""
    result_a = parse(name_a, vocabs)
    result_b = parse(name_b, vocabs)
    assert result_a.ir != result_b.ir, (
        f"Expected distinct IR for:\n"
        f"  A = {name_a!r}  →  {result_a.ir!r}\n"
        f"  B = {name_b!r}  →  {result_b.ir!r}"
    )


# ---------------------------------------------------------------------------
# Group 1: locus relation variants (at vs of)  [pairs 1–10]
# ---------------------------------------------------------------------------


def test_ambiguity_at_vs_of_plasma_boundary(vocabs: Vocabularies) -> None:
    """``_at_plasma_boundary`` vs ``_of_plasma_boundary`` differ in locus relation."""
    _assert_distinct_ir(
        "pressure_at_plasma_boundary",
        "pressure_of_plasma_boundary",
        vocabs,
    )


def test_ambiguity_at_vs_of_magnetic_axis(vocabs: Vocabularies) -> None:
    """Same for magnetic_axis locus."""
    _assert_distinct_ir(
        "temperature_at_magnetic_axis",
        "temperature_of_magnetic_axis",
        vocabs,
    )


def test_ambiguity_at_vs_of_pedestal(vocabs: Vocabularies) -> None:
    """Same for pedestal locus."""
    _assert_distinct_ir(
        "safety_factor_at_pedestal",
        "safety_factor_of_pedestal",
        vocabs,
    )


def test_ambiguity_at_vs_of_separatrix(vocabs: Vocabularies) -> None:
    """Same for a position locus with both at+of: active_limiter_point."""
    # separatrix is entity-typed (only allows 'of'), so use active_limiter_point
    # which allows both 'at' and 'of'
    _assert_distinct_ir(
        "safety_factor_at_active_limiter_point",
        "safety_factor_of_active_limiter_point",
        vocabs,
    )


def test_ambiguity_at_vs_of_active_limiter_point(vocabs: Vocabularies) -> None:
    """Same for active_limiter_point locus."""
    _assert_distinct_ir(
        "temperature_at_active_limiter_point",
        "temperature_of_active_limiter_point",
        vocabs,
    )


def test_ambiguity_at_vs_of_q_95(vocabs: Vocabularies) -> None:
    """``_at_along_beam`` vs ``_of_along_beam`` — position locus with both relations."""
    _assert_distinct_ir(
        "pressure_at_along_beam",
        "pressure_of_along_beam",
        vocabs,
    )


def test_ambiguity_at_vs_of_sawtooth_inversion_radius(vocabs: Vocabularies) -> None:
    """``_at_sawtooth_inversion_radius`` vs ``_of_`` form."""
    _assert_distinct_ir(
        "temperature_at_sawtooth_inversion_radius",
        "temperature_of_sawtooth_inversion_radius",
        vocabs,
    )


def test_ambiguity_at_vs_of_x_point(vocabs: Vocabularies) -> None:
    """``_at_x_point`` vs ``_of_x_point``."""
    _assert_distinct_ir(
        "pressure_at_x_point",
        "pressure_of_x_point",
        vocabs,
    )


def test_ambiguity_at_vs_of_inner_divertor_target(vocabs: Vocabularies) -> None:
    """Inner divertor target: at vs of."""
    _assert_distinct_ir(
        "temperature_at_inner_divertor_target",
        "temperature_of_inner_divertor_target",
        vocabs,
    )


def test_ambiguity_at_vs_of_outer_divertor_target(vocabs: Vocabularies) -> None:
    """Outer divertor target: at vs of."""
    _assert_distinct_ir(
        "temperature_at_outer_divertor_target",
        "temperature_of_outer_divertor_target",
        vocabs,
    )


# ---------------------------------------------------------------------------
# Group 2: operator kind — prefix vs postfix  [pairs 11–15]
# ---------------------------------------------------------------------------


def test_ambiguity_prefix_maximum_vs_postfix_magnitude(vocabs: Vocabularies) -> None:
    """``maximum_of_pressure`` (prefix) vs ``pressure_magnitude`` (postfix)."""
    _assert_distinct_ir("maximum_of_pressure", "pressure_magnitude", vocabs)


def test_ambiguity_prefix_amplitude_vs_postfix_magnitude(vocabs: Vocabularies) -> None:
    """``amplitude_of_temperature`` (prefix) vs ``temperature_magnitude`` (postfix)."""
    _assert_distinct_ir("amplitude_of_temperature", "temperature_magnitude", vocabs)


def test_ambiguity_prefix_vs_no_operator(vocabs: Vocabularies) -> None:
    """``maximum_of_pressure`` vs bare ``pressure``."""
    _assert_distinct_ir("maximum_of_pressure", "pressure", vocabs)


def test_ambiguity_postfix_vs_no_operator(vocabs: Vocabularies) -> None:
    """``pressure_magnitude`` vs bare ``pressure``."""
    _assert_distinct_ir("pressure_magnitude", "pressure", vocabs)


def test_ambiguity_prefix_flux_surface_averaged_vs_no_op(vocabs: Vocabularies) -> None:
    """``flux_surface_averaged_of_pressure`` vs bare ``pressure``."""
    _assert_distinct_ir("flux_surface_averaged_of_pressure", "pressure", vocabs)


# ---------------------------------------------------------------------------
# Group 3: different prefix operators on same base  [pairs 16–20]
# ---------------------------------------------------------------------------


def test_ambiguity_maximum_vs_amplitude_prefix(vocabs: Vocabularies) -> None:
    """``maximum_of_X`` vs ``amplitude_of_X`` differ in operator."""
    _assert_distinct_ir("maximum_of_pressure", "amplitude_of_pressure", vocabs)


def test_ambiguity_maximum_vs_time_average(vocabs: Vocabularies) -> None:
    """``maximum_of_X`` vs ``time_average_of_X``."""
    _assert_distinct_ir("maximum_of_temperature", "time_average_of_temperature", vocabs)


def test_ambiguity_derivative_vs_gradient(vocabs: Vocabularies) -> None:
    """``derivative_of_X`` vs ``gradient_of_X``."""
    _assert_distinct_ir("derivative_of_pressure", "gradient_of_pressure", vocabs)


def test_ambiguity_accumulated_vs_cumulative(vocabs: Vocabularies) -> None:
    """``accumulated_of_X`` vs ``cumulative_of_X``."""
    _assert_distinct_ir("accumulated_of_pressure", "cumulative_of_pressure", vocabs)


def test_ambiguity_flux_surface_averaged_vs_volume_average(
    vocabs: Vocabularies,
) -> None:
    """``flux_surface_averaged_of_X`` vs ``volume_averaged_of_X``."""
    _assert_distinct_ir(
        "flux_surface_averaged_of_temperature",
        "volume_averaged_of_temperature",
        vocabs,
    )


# ---------------------------------------------------------------------------
# Group 4: nested operator ordering  [pairs 21–25]
# ---------------------------------------------------------------------------


def test_ambiguity_nested_order_max_then_amplitude(vocabs: Vocabularies) -> None:
    """``maximum_of_amplitude_of_X`` vs ``amplitude_of_maximum_of_X``."""
    _assert_distinct_ir(
        "maximum_of_amplitude_of_pressure",
        "amplitude_of_maximum_of_pressure",
        vocabs,
    )


def test_ambiguity_nested_order_max_then_flux_surface_averaged(
    vocabs: Vocabularies,
) -> None:
    """``maximum_of_flux_surface_averaged_of_X`` vs reversed."""
    _assert_distinct_ir(
        "maximum_of_flux_surface_averaged_of_pressure",
        "flux_surface_averaged_of_maximum_of_pressure",
        vocabs,
    )


def test_ambiguity_nested_order_time_average_then_max(vocabs: Vocabularies) -> None:
    """``time_average_of_maximum_of_X`` vs reversed."""
    _assert_distinct_ir(
        "time_average_of_maximum_of_temperature",
        "maximum_of_time_average_of_temperature",
        vocabs,
    )


def test_ambiguity_nested_derivative_gradient(vocabs: Vocabularies) -> None:
    """``derivative_of_gradient_of_X`` vs ``gradient_of_derivative_of_X``."""
    _assert_distinct_ir(
        "derivative_of_gradient_of_pressure",
        "gradient_of_derivative_of_pressure",
        vocabs,
    )


def test_ambiguity_three_operators_ordering(vocabs: Vocabularies) -> None:
    """Three operators: different outer vs inner."""
    _assert_distinct_ir(
        "maximum_of_amplitude_of_gradient_of_pressure",
        "amplitude_of_maximum_of_gradient_of_pressure",
        vocabs,
    )


# ---------------------------------------------------------------------------
# Group 5: binary operator types  [pairs 26–28]
# ---------------------------------------------------------------------------


def test_ambiguity_product_vs_ratio(vocabs: Vocabularies) -> None:
    """``product_of_A_and_B`` vs ``ratio_of_A_to_B``."""
    _assert_distinct_ir(
        "product_of_pressure_and_temperature",
        "ratio_of_pressure_to_temperature",
        vocabs,
    )


def test_ambiguity_binary_arg_order(vocabs: Vocabularies) -> None:
    """``product_of_A_and_B`` vs ``product_of_B_and_A`` differ in arg order."""
    _assert_distinct_ir(
        "product_of_pressure_and_temperature",
        "product_of_temperature_and_pressure",
        vocabs,
    )


def test_ambiguity_unary_vs_binary(vocabs: Vocabularies) -> None:
    """Unary prefix ``maximum_of_pressure`` vs binary ``product_of_pressure_and_temperature``."""
    _assert_distinct_ir(
        "maximum_of_pressure",
        "product_of_pressure_and_temperature",
        vocabs,
    )


# ---------------------------------------------------------------------------
# Group 6: locus presence / identity  [pairs 29–35]
# ---------------------------------------------------------------------------


def test_ambiguity_with_vs_without_locus(vocabs: Vocabularies) -> None:
    """``X_at_plasma_boundary`` vs bare ``X``."""
    _assert_distinct_ir("pressure_at_plasma_boundary", "pressure", vocabs)


def test_ambiguity_different_loci_position(vocabs: Vocabularies) -> None:
    """Same base, different position loci."""
    _assert_distinct_ir(
        "temperature_at_plasma_boundary",
        "temperature_at_magnetic_axis",
        vocabs,
    )


def test_ambiguity_entity_vs_position_locus(vocabs: Vocabularies) -> None:
    """Entity locus ``_of_`` vs position locus ``_at_`` with different tokens."""
    _assert_distinct_ir(
        "temperature_of_plasma_boundary",  # position-typed but with OF
        "temperature_at_plasma_boundary",  # position-typed with AT
        vocabs,
    )


def test_ambiguity_different_entity_loci(vocabs: Vocabularies) -> None:
    """Same base, different entity loci."""
    _assert_distinct_ir(
        "pressure_of_bolometer",
        "pressure_of_antenna_strap",
        vocabs,
    )


def test_ambiguity_locus_entity_vs_no_locus(vocabs: Vocabularies) -> None:
    """``pressure_of_bolometer`` vs bare ``pressure``."""
    _assert_distinct_ir("pressure_of_bolometer", "pressure", vocabs)


def test_ambiguity_geometry_locus_of_vs_position_locus_of(vocabs: Vocabularies) -> None:
    """Geometry locus ``_of_`` vs position locus ``_of_`` — differ in locus type."""
    # beam_path is geometry-typed; plasma_boundary is position-typed
    _assert_distinct_ir(
        "pressure_of_beam_path",
        "pressure_of_plasma_boundary",
        vocabs,
    )


def test_ambiguity_locus_plus_mechanism_vs_just_locus(vocabs: Vocabularies) -> None:
    """``X_at_L_due_to_P`` vs ``X_at_L``."""
    _assert_distinct_ir(
        "pressure_at_plasma_boundary_due_to_conduction",
        "pressure_at_plasma_boundary",
        vocabs,
    )


# ---------------------------------------------------------------------------
# Group 7: mechanism variants  [pairs 36–40]
# ---------------------------------------------------------------------------


def test_ambiguity_mechanism_vs_none(vocabs: Vocabularies) -> None:
    """``X_due_to_conduction`` vs bare ``X``."""
    _assert_distinct_ir("pressure_due_to_conduction", "pressure", vocabs)


def test_ambiguity_different_mechanisms(vocabs: Vocabularies) -> None:
    """Different processes produce different mechanisms."""
    _assert_distinct_ir(
        "pressure_due_to_conduction",
        "pressure_due_to_diffusion",
        vocabs,
    )


def test_ambiguity_mechanism_conduction_vs_convection(vocabs: Vocabularies) -> None:
    """``conduction`` vs ``convection`` mechanism."""
    _assert_distinct_ir(
        "temperature_due_to_conduction",
        "temperature_due_to_convection",
        vocabs,
    )


def test_ambiguity_mechanism_turbulent_vs_neoclassical(vocabs: Vocabularies) -> None:
    """``turbulent`` vs ``neoclassical`` mechanism."""
    _assert_distinct_ir(
        "temperature_due_to_turbulent",
        "temperature_due_to_neoclassical",
        vocabs,
    )


def test_ambiguity_operator_mechanism_vs_just_operator(vocabs: Vocabularies) -> None:
    """``max_of_X_due_to_P`` vs ``max_of_X``."""
    _assert_distinct_ir(
        "maximum_of_pressure_due_to_conduction",
        "maximum_of_pressure",
        vocabs,
    )


# ---------------------------------------------------------------------------
# Group 8: projection variants  [pairs 41–47]
# ---------------------------------------------------------------------------


def test_ambiguity_radial_vs_toroidal_component(vocabs: Vocabularies) -> None:
    """``radial_component_of_X`` vs ``toroidal_component_of_X``."""
    _assert_distinct_ir(
        "radial_component_of_pressure",
        "toroidal_component_of_pressure",
        vocabs,
    )


def test_ambiguity_radial_vs_poloidal_component(vocabs: Vocabularies) -> None:
    """``radial_component_of_X`` vs ``poloidal_component_of_X``."""
    _assert_distinct_ir(
        "radial_component_of_temperature",
        "poloidal_component_of_temperature",
        vocabs,
    )


def test_ambiguity_component_vs_coordinate_projection(vocabs: Vocabularies) -> None:
    """``radial_component_of_<base>`` vs ``radial_coordinate_of_<carrier>``
    differ in projection shape and base kind."""
    _assert_distinct_ir(
        "radial_component_of_pressure",
        "radial_coordinate_of_normalized_minor_radius",
        vocabs,
    )


def test_ambiguity_projection_vs_no_projection(vocabs: Vocabularies) -> None:
    """``radial_component_of_pressure`` vs bare ``pressure``."""
    _assert_distinct_ir("radial_component_of_pressure", "pressure", vocabs)


def test_ambiguity_parallel_vs_perpendicular_component(vocabs: Vocabularies) -> None:
    """``parallel_component_of_X`` vs ``perpendicular_component_of_X``."""
    _assert_distinct_ir(
        "parallel_component_of_pressure",
        "perpendicular_component_of_pressure",
        vocabs,
    )


def test_ambiguity_projection_plus_locus_vs_just_projection(
    vocabs: Vocabularies,
) -> None:
    """``radial_component_of_X_at_L`` vs ``radial_component_of_X``."""
    _assert_distinct_ir(
        "radial_component_of_pressure_at_plasma_boundary",
        "radial_component_of_pressure",
        vocabs,
    )


def test_ambiguity_projection_plus_locus_vs_just_locus(vocabs: Vocabularies) -> None:
    """``radial_component_of_X_at_L`` vs ``X_at_L``."""
    _assert_distinct_ir(
        "radial_component_of_pressure_at_plasma_boundary",
        "pressure_at_plasma_boundary",
        vocabs,
    )


# ---------------------------------------------------------------------------
# Group 9: different bases (sanity)  [pairs 48–50]
# ---------------------------------------------------------------------------


def test_ambiguity_different_bases(vocabs: Vocabularies) -> None:
    """Different physical_bases always produce different IR."""
    _assert_distinct_ir("pressure", "temperature", vocabs)


def test_ambiguity_base_vs_carrier(vocabs: Vocabularies) -> None:
    """A physical_base vs a geometry_carrier (different BaseKind)."""
    _assert_distinct_ir("pressure", "normalized_minor_radius", vocabs)


def test_ambiguity_operator_plus_different_bases(vocabs: Vocabularies) -> None:
    """Same operator, different bases."""
    _assert_distinct_ir("maximum_of_pressure", "maximum_of_temperature", vocabs)
