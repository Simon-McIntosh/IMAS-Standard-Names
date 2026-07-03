"""Semantic validation checks for provenance/operator logic."""

from __future__ import annotations

from ..grammar.model import parse_standard_name
from ..grammar.model_types import GeometricBase
from ..models import StandardNameEntry, StandardNameMetadataEntry
from ..provenance import OperatorProvenance

__all__ = ["run_semantic_checks"]

# Geometric bases that describe orientations (require object qualification)
ORIENTATION_BASES = {
    GeometricBase.SURFACE_NORMAL.value,
    GeometricBase.SENSOR_NORMAL.value,
    GeometricBase.TANGENT_VECTOR.value,
}

# Geometric bases that describe paths/boundaries (require object qualification)
PATH_BASES = {
    GeometricBase.TRAJECTORY.value,
    GeometricBase.OUTLINE.value,
    GeometricBase.CONTOUR.value,
}

# Geometric base requiring dimension specification
EXTENT_BASE = GeometricBase.EXTENT.value


def run_semantic_checks(entries: dict[str, StandardNameEntry]) -> list[str]:
    issues: list[str] = []
    for name, entry in entries.items():
        # Existing provenance checks
        prov = getattr(entry, "provenance", None)
        if isinstance(prov, OperatorProvenance):
            # Example rule: if gradient operator present, unit should include division by length
            if "gradient" in list(prov.operators):
                unit = getattr(entry, "unit", "")
                # Accept units with .m or negative exponent (e.g., m^-4, m^-1)
                if unit and ".m" not in unit and "^-" not in unit and unit != "":
                    issues.append(
                        f"{name}: gradient operator present but unit '{unit}' does not look like derivative (heuristic)."
                    )

        # New grammar-based semantic checks
        issues.extend(_check_geometric_qualifier_requirement(name, entry))
        issues.extend(_check_component_with_base_type(name, entry))
        issues.extend(_check_coordinate_with_base_type(name, entry))
        issues.extend(_check_orientation_vector_completeness(name, entry))
        issues.extend(_check_trajectory_path_qualification(name, entry))
        issues.extend(_check_extent_dimensionality(name, entry))
        issues.extend(_check_physical_base_with_object(name, entry))
        issues.extend(_check_dimensionless_physical_quantity(name, entry))
        issues.extend(_check_none_unit_with_quantitative_kind(name, entry))

    return issues


def _check_geometric_qualifier_requirement(
    name: str, entry: StandardNameEntry
) -> list[str]:
    """Geometric bases MUST have object OR geometry qualification.

    Rule: Names with geometric_base require either object or geometry segment.
    Rationale: Geometric quantities describe spatial properties *of something*.
    Severity: Error
    """
    issues: list[str] = []
    try:
        parsed = parse_standard_name(entry.standard_name)
        geometric_base = getattr(parsed, "geometric_base", None)

        if geometric_base:
            obj = getattr(parsed, "object", None)
            geom = getattr(parsed, "geometry", None)

            if not obj and not geom:
                issues.append(
                    f"{name}: ERROR - geometric quantity '{geometric_base}' requires "
                    "object or geometry qualifier to specify what is being described. "
                    f"Example: {geometric_base}_of_flux_loop or {geometric_base}_at_midplane"
                )
    except Exception:
        # If parsing fails, skip this check (structural validation will catch it)
        pass

    return issues


def _check_component_with_base_type(name: str, entry: StandardNameEntry) -> list[str]:
    """Component segment should primarily be used with physical bases, not geometric.

    Rule: component (radial/toroidal/etc.) describes directional projections of
    physical vector fields, not geometric positions (use coordinate for those).
    Severity: Warning
    """
    issues: list[str] = []
    try:
        parsed = parse_standard_name(entry.standard_name)
        component = getattr(parsed, "component", None)
        geometric_base = getattr(parsed, "geometric_base", None)

        if component and geometric_base:
            issues.append(
                f"{name}: WARNING - 'component' is typically for physical vectors "
                f"(magnetic_field, velocity), not geometric quantities like '{geometric_base}'. "
                f"Consider using 'coordinate' instead: {component}_coordinate_{geometric_base}_of_..."
            )
    except Exception:
        pass

    return issues


def _check_coordinate_with_base_type(name: str, entry: StandardNameEntry) -> list[str]:
    """Coordinate segment should be used with geometric bases, not physical bases.

    Rule: coordinate defines spatial reference frames for geometric quantities.
    Severity: Warning
    """
    issues: list[str] = []
    try:
        parsed = parse_standard_name(entry.standard_name)
        coordinate = getattr(parsed, "coordinate", None)
        physical_base = getattr(parsed, "physical_base", None)

        if coordinate and physical_base:
            issues.append(
                f"{name}: WARNING - 'coordinate' is for geometric/spatial quantities, "
                f"not physical fields like '{physical_base}'. Consider using 'component' "
                f"for directional decomposition: {coordinate}_component_of_{physical_base}"
            )
    except Exception:
        pass

    return issues


def _check_orientation_vector_completeness(
    name: str, entry: StandardNameEntry
) -> list[str]:
    """Orientation vectors (normals, tangents) must have object qualification.

    Rule: Normals and tangents are properties of surfaces/sensors/curves.
    Severity: Error
    """
    issues: list[str] = []
    try:
        parsed = parse_standard_name(entry.standard_name)
        geometric_base = getattr(parsed, "geometric_base", None)

        if geometric_base in ORIENTATION_BASES:
            obj = getattr(parsed, "object", None)
            if not obj:
                base_type = "normal" if "normal" in geometric_base else "tangent"
                issues.append(
                    f"{name}: ERROR - {base_type} vector '{geometric_base}' must specify "
                    f"the object/surface it belongs to. Example: {geometric_base}_of_divertor_tile"
                )
    except Exception:
        pass

    return issues


def _check_trajectory_path_qualification(
    name: str, entry: StandardNameEntry
) -> list[str]:
    """Trajectories and paths must specify what is moving/bounded.

    Rule: Trajectories describe motion; outlines/contours describe boundaries.
    Severity: Error
    """
    issues: list[str] = []
    try:
        parsed = parse_standard_name(entry.standard_name)
        geometric_base = getattr(parsed, "geometric_base", None)

        if geometric_base in PATH_BASES:
            obj = getattr(parsed, "object", None)
            if not obj:
                example_obj = (
                    "neutral_beam" if geometric_base == "trajectory" else "limiter_tile"
                )
                issues.append(
                    f"{name}: ERROR - '{geometric_base}' must specify what entity's path/boundary "
                    f"is described. Example: {geometric_base}_of_{example_obj}"
                )
    except Exception:
        pass

    return issues


def _check_extent_dimensionality(name: str, entry: StandardNameEntry) -> list[str]:
    """Extent should typically specify dimension via component.

    Rule: 'extent' (size/span) often needs directional qualification.
    Severity: Info
    """
    issues: list[str] = []
    try:
        parsed = parse_standard_name(entry.standard_name)
        geometric_base = getattr(parsed, "geometric_base", None)
        component = getattr(parsed, "component", None)

        if geometric_base == EXTENT_BASE and not component:
            obj = getattr(parsed, "object", None)
            obj_str = f"_of_{obj}" if obj else ""
            issues.append(
                f"{name}: INFO - 'extent' typically specifies dimension. "
                f"Consider: radial_extent{obj_str} or vertical_extent{obj_str}"
            )
    except Exception:
        pass

    return issues


def _check_physical_base_with_object(name: str, entry: StandardNameEntry) -> list[str]:
    """Physical bases with object qualification may indicate confusion.

    Rule: Physical quantities (temperature, density) are properties of subjects,
    not objects. Object qualification suggests measuring location rather than
    intrinsic property.
    Severity: Info
    """
    issues: list[str] = []
    try:
        parsed = parse_standard_name(entry.standard_name)
        physical_base = getattr(parsed, "physical_base", None)
        obj = getattr(parsed, "object", None)

        if physical_base and obj:
            # Check if subject is also present (which would be more appropriate)
            subject = getattr(parsed, "subject", None)
            if not subject:
                issues.append(
                    f"{name}: INFO - physical quantity '{physical_base}' with object '{obj}' "
                    "may indicate measurement location. Consider using subject (electron, ion) "
                    f"for intrinsic properties, or _at_{obj} for field evaluation location."
                )
    except Exception:
        pass

    return issues


# ---------------------------------------------------------------------------
# Dimensionless physical quantity check — vocabulary-driven
# ---------------------------------------------------------------------------


def _load_inherently_dimensional_bases() -> frozenset[str]:
    """Load the set of physical bases marked ``inherently_dimensional`` in vocab."""
    from ..grammar.vocab_loaders import load_physical_bases  # noqa: PLC0415

    registry = load_physical_bases()
    return frozenset(
        token for token, defn in registry.bases.items() if defn.inherently_dimensional
    )


def _load_dimensionless_operators() -> frozenset[str]:
    """Load operators marked ``dimensionless: true`` in the operator vocabulary."""
    from ..grammar.vocab_loaders import load_operators  # noqa: PLC0415

    registry = load_operators()
    return frozenset(
        token for token, defn in registry.operators.items() if defn.dimensionless
    )


def _load_dimension_transforming_operators() -> frozenset[str]:
    """Load operators marked ``dimension_transforming: true`` in the vocabulary.

    These change the dimensions of their argument (integrals, derivatives,
    inverse, square), so the base-implies-unit heuristic does not apply —
    ``volume_integrated_<density>`` is a dimensionless count.
    """
    from ..grammar.vocab_loaders import load_operators  # noqa: PLC0415

    registry = load_operators()
    return frozenset(
        token
        for token, defn in registry.operators.items()
        if defn.dimension_transforming
    )


def _load_normalizing_qualifiers() -> frozenset[str]:
    """Load qualifier tokens that imply dimensionless output from vocab."""
    from ..grammar.vocab_loaders import load_normalizing_qualifiers  # noqa: PLC0415

    return load_normalizing_qualifiers()


def _check_dimensionless_physical_quantity(
    name: str, entry: StandardNameEntry
) -> list[str]:
    """Flag dimensionless unit on physical bases that inherently carry units.

    Rule: Scalar/vector entries with ``unit="1"`` whose physical base is a
    quantity that normally carries SI units are likely misconfigured. The
    following constructs are excluded because they can legitimately be
    dimensionless:

    - binary operators (ratio, product, difference);
    - operators marked ``dimensionless: true`` in the operator vocabulary
      (e.g. normalized, perturbed, logarithm);
    - any qualifier listed in ``normalizing_qualifiers.yml``
      (e.g. ``gyrocenter_pressure`` is gyrokinetic-normalized by convention).

    Severity: Warning
    """
    issues: list[str] = []

    # Only applies to scalar/vector entries that have a unit field
    if isinstance(entry, StandardNameMetadataEntry):
        return issues

    unit = getattr(entry, "unit", None)
    if unit != "1":
        return issues

    try:
        parsed = parse_standard_name(entry.name)
        physical_base = getattr(parsed, "physical_base", None)
        binary_operator = getattr(parsed, "binary_operator", None)
        transformation = getattr(parsed, "transformation", None)

        # Binary operators (ratio, product, difference) can legitimately yield
        # dimensionless results, so skip the check for those.
        if binary_operator:
            return issues

        # normalized_<direction> components (components.yml "normalized
        # spatial directions") absorb the normalized token into the component
        # (normalized_parallel_momentum_flux parses component=
        # normalized_parallel), so the SI-unit inference from the base is
        # unreliable for them.
        component = getattr(parsed, "component", None)
        component_value = getattr(component, "value", component)
        if isinstance(component_value, str) and component_value.startswith(
            "normalized_"
        ):
            return issues

        # Operators marked dimensionless in the vocabulary always produce
        # dimensionless output (normalized, perturbed, logarithm, etc.);
        # dimension-transforming operators (integrals, derivatives, inverse)
        # change the unit of the base, so the base-implies-unit inference is
        # invalid for them (volume_integrated density is a count).
        dimensionless_ops = _load_dimensionless_operators()
        transforming_ops = _load_dimension_transforming_operators()
        exempt_ops = dimensionless_ops | transforming_ops
        tx_value = getattr(transformation, "value", transformation)
        if tx_value in exempt_ops:
            return issues

        # Qualifiers that imply normalization (from normalizing_qualifiers.yml)
        # or that correspond to dimensionless operator tokens produce
        # dimensionless output even when parsed as qualifiers.
        normalizing_quals = _load_normalizing_qualifiers()
        # Operator tokens can surface in the IR qualifier list (the parser's
        # acceptance union), so exempt the transforming set there too.
        exempt_qualifiers = dimensionless_ops | normalizing_quals | transforming_ops
        try:
            from ..grammar.parser import parse as ir_parse  # noqa: PLC0415

            ir = ir_parse(entry.name).ir
            if ir is not None:
                qualifier_tokens = {q.token for q in (ir.qualifiers or [])}
                if qualifier_tokens & exempt_qualifiers:
                    return issues
                operator_tokens = {
                    getattr(op, "token", op) for op in (ir.operators or [])
                }
                if operator_tokens & exempt_ops:
                    return issues
        except Exception:
            pass

        inherently_dimensional = _load_inherently_dimensional_bases()
        if physical_base and physical_base in inherently_dimensional:
            issues.append(
                f"{name}: WARNING - dimensionless unit '1' on physical quantity "
                f"'{physical_base}' is unexpected. Quantities like '{physical_base}' "
                "normally carry SI units. Use '1' only for true dimensionless "
                "quantities (ratios, coefficients, counts)."
            )
    except Exception:
        pass

    return issues


def _check_none_unit_with_quantitative_kind(
    name: str, entry: StandardNameEntry
) -> list[str]:
    """Flag None unit on scalar/vector entries that should have units.

    Rule: Scalar and vector entries represent physical quantities that should
    have explicit units. ``unit=None`` is reserved for metadata entries
    (identifiers, labels, enumerations). Scalar/vector entries with no unit
    likely need either a specific SI unit or ``'1'`` for dimensionless quantities.
    Severity: Warning
    """
    issues: list[str] = []

    # Only metadata entries are exempt from unit requirement
    if isinstance(entry, StandardNameMetadataEntry):
        return issues

    unit = getattr(entry, "unit", None)
    if unit is not None:
        return issues

    kind = getattr(entry, "kind", None)
    issues.append(
        f"{name}: WARNING - {kind} entry has no unit (unit=None). "
        "Scalar and vector entries should have explicit units. "
        "Use a specific SI unit, or '1' for dimensionless quantities "
        "(ratios, coefficients, counts). "
        "Reserve unit=None for metadata entries only."
    )

    return issues
