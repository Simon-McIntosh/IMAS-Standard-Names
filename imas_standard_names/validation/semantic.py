"""Semantic validation checks for provenance/operator logic."""

from __future__ import annotations

from ..grammar.model import parse_standard_name
from ..grammar.types import GeometricBase
from ..models import StandardNameEntry
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
