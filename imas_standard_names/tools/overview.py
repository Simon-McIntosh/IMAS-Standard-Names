from collections import Counter

from fastmcp import Context

import imas_standard_names.grammar.types as grammar_types
from imas_standard_names import __version__ as package_version
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.grammar.types import (
    EXCLUSIVE_SEGMENT_PAIRS,
    SCOPE_EXCLUDE,
    SCOPE_INCLUDE,
    SCOPE_RATIONALE,
    SEGMENT_ORDER,
    SEGMENT_RULES,
    SEGMENT_TEMPLATES,
)
from imas_standard_names.tools.base import BaseTool


def _enum_values[
    E: (
        grammar_types.Component,
        grammar_types.Subject,
        grammar_types.Object,
        grammar_types.Source,
        grammar_types.Position,
        grammar_types.Process,
    )
](
    enum_cls: type[E],
) -> list[str]:
    """Return the allowed string values for a StrEnum type."""
    return [e.value for e in enum_cls]


def _build_canonical_pattern() -> str:
    """Build the canonical pattern string dynamically from SEGMENT_RULES.

    This ensures the pattern stays in sync with the grammar specification.
    """
    pattern_parts = []
    processed_exclusive = set()

    for rule in SEGMENT_RULES:
        seg_id = rule.identifier

        # Skip if already handled as part of an exclusive group
        if seg_id in processed_exclusive:
            continue

        # Check if this segment is part of an exclusive group
        exclusive_with = set(rule.exclusive_with)
        if exclusive_with:
            # Build exclusive pattern for this group
            group_patterns = []

            # Add current segment's pattern
            if rule.template:
                template = rule.template.replace("{token}", f"<{seg_id}>")
                group_patterns.append(template)
            else:
                group_patterns.append(f"<{seg_id}>")

            # Add patterns for exclusive segments
            for excl_id in exclusive_with:
                excl_rule = next(
                    (r for r in SEGMENT_RULES if r.identifier == excl_id), None
                )
                if excl_rule is None:
                    continue
                if excl_rule.template:
                    excl_template = excl_rule.template.replace(
                        "{token}", f"<{excl_id}>"
                    )
                    group_patterns.append(excl_template)
                else:
                    group_patterns.append(f"<{excl_id}>")
                processed_exclusive.add(excl_id)

            seg_pattern = f"[{' | '.join(group_patterns)}]?"
            processed_exclusive.add(seg_id)
        else:
            # Build pattern for non-exclusive segment
            if rule.template:
                template = rule.template.replace("{token}", f"<{seg_id}>")
                seg_pattern = f"[{template}]?" if rule.optional else template
            elif seg_id == "base":
                seg_pattern = "<base>"  # base is never optional
            else:
                seg_pattern = f"[<{seg_id}>]?" if rule.optional else f"<{seg_id}>"

        pattern_parts.append(seg_pattern)

    return " ".join(pattern_parts)


def _build_segment_order_constraint() -> str:
    """Build the segment order constraint dynamically from SEGMENT_RULES."""
    parts = []
    processed_exclusive = set()

    for rule in SEGMENT_RULES:
        seg_id = rule.identifier

        if seg_id in processed_exclusive:
            continue

        # Check if this segment is part of an exclusive group
        exclusive_with = set(rule.exclusive_with)
        if exclusive_with:
            group_ids = [seg_id] + list(exclusive_with)
            group_label = "|".join(group_ids)
            parts.append(f"[{group_label}]")
            processed_exclusive.add(seg_id)
            processed_exclusive.update(exclusive_with)
        elif rule.optional:
            parts.append(f"[{seg_id}]")
        else:
            parts.append(seg_id)

    return " → ".join(parts)


def _get_segment_descriptions() -> dict[str, str]:
    """Load segment descriptions directly from the grammar specification YAML."""
    from importlib import resources

    import yaml

    from imas_standard_names.grammar_codegen.spec import IncludeLoader

    grammar_path = resources.files("imas_standard_names.grammar") / "specification.yml"
    with grammar_path.open("r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=IncludeLoader) or {}

    descriptions = {}
    for segment in data.get("segments", []):
        seg_id = segment.get("id", "")
        desc = segment.get("description", "")
        if seg_id:
            descriptions[seg_id] = desc

    return descriptions


def _get_vocabulary_description(segment_id: str) -> str:
    """Generate a human-readable vocabulary description."""
    descriptions = {
        "component": "Spatial or field-aligned direction (e.g., radial, toroidal, parallel)",
        "subject": "Particle species or plasma component (e.g., electron, ion, deuterium)",
        "object": "Physical object, diagnostic hardware, or equipment (e.g., flux_loop, bolometer)",
        "position": "Spatial location where field is evaluated (use with at_ template)",
        "geometry": "Intrinsic geometric property of the object (use with of_ template)",
        "process": "Physical process or mechanism (e.g., conduction, ohmic, radiation)",
    }
    return descriptions.get(segment_id, "")


def _build_template_application_rule() -> str:
    """Build the template application rule dynamically from SEGMENT_TEMPLATES."""
    templated_segments = [seg for seg in SEGMENT_TEMPLATES if seg != "base"]
    non_templated = [
        rule.identifier
        for rule in SEGMENT_RULES
        if rule.template is None and rule.identifier != "base"
    ]

    parts = []
    if templated_segments:
        parts.append(
            f"Templates are applied to {', '.join(templated_segments)} segments."
        )
    if non_templated:
        parts.append(
            f"{' and '.join(non_templated)} and base are inserted as-is without template modification."
        )

    return " ".join(parts) if parts else "No templates defined."


class OverviewTool(BaseTool):
    """Tool providing a high-level overview (aggregate statistics) of the
    Standard Names catalog for quick inspection and monitoring.

    Returned structure is stable JSON for programmatic consumption.
    Every aggregation key conveys that values are counts (number of entries).
    Coordinate frames and kinds include zero-count members for full visibility.
    Units aggregation includes dimensionless as the symbolic key 'dimensionless'.
    """

    def __init__(self, repository=None):  # type: ignore[no-untyped-def]
        super().__init__(repository)
        # Optional: an attached EditCatalog instance for staged diffs
        self.edit_catalog = None

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "get_overview"

    @mcp_tool(
        description=(
            "Get IMAS Standard Names grammar rules and vocabulary. Use this first before composing names. "
            "Returns grammar_structure with canonical pattern, segment templates, vocabulary tokens, "
            "validation rules, composition examples, and catalog statistics."
        )
    )
    async def get_grammar_and_vocabulary(self, ctx: Context | None = None):
        models = self.catalog.list()
        total = len(models)

        # Load segment descriptions from spec
        segment_descriptions = _get_segment_descriptions()

        # Build grammar structure from generated metadata
        grammar_structure = {
            "canonical_pattern": _build_canonical_pattern(),
            "segment_order": list(SEGMENT_ORDER),
            "segments": [
                {
                    "id": rule.identifier,
                    "optional": rule.optional,
                    "template": rule.template,
                    "exclusive_with": list(rule.exclusive_with),
                    "vocabulary_size": len(rule.tokens),
                    "description": segment_descriptions.get(rule.identifier, ""),
                }
                for rule in SEGMENT_RULES
            ],
        }

        # Validation rules from grammar metadata
        validation_rules = {
            "base_pattern": "^[a-z][a-z0-9_]*$",
            "base_required": True,
            "exclusivity_constraints": [
                {
                    "segments": list(pair),
                    "rule": "mutually_exclusive",
                    "description": f"{pair[0]} and {pair[1]} cannot both be present",
                }
                for pair in EXCLUSIVE_SEGMENT_PAIRS
            ],
            "segment_order_constraint": _build_segment_order_constraint(),
            "template_application": _build_template_application_rule(),
        }

        # Build vocabulary dynamically from enums
        vocabulary = {}

        # Add component vocabulary if it exists
        if hasattr(grammar_types, "Component"):
            vocabulary["component"] = {
                "segment_id": "component",
                "template": SEGMENT_TEMPLATES.get("component"),
                "tokens": _enum_values(grammar_types.Component),
                "usage": "prefix",
                "description": "Spatial or field-aligned direction for physical vector quantities (magnetic_field, heat_flux, velocity, etc.). Use with fields/fluxes, not geometric positions.",
            }

        # Add coordinate vocabulary (shares tokens with component but different usage)
        if hasattr(grammar_types, "Component"):
            vocabulary["coordinate"] = {
                "segment_id": "coordinate",
                "template": SEGMENT_TEMPLATES.get("coordinate"),
                "tokens": _enum_values(grammar_types.Component),
                "usage": "prefix",
                "description": "Coordinate axis for geometric/spatial vector decomposition (position, vertex, centroid, trajectory, displacement, offset). Use ONLY with geometric bases, NOT physical fields.",
            }

        # Add subject vocabulary if it exists
        if hasattr(grammar_types, "Subject"):
            vocabulary["subject"] = {
                "segment_id": "subject",
                "template": SEGMENT_TEMPLATES.get("subject"),
                "tokens": _enum_values(grammar_types.Subject),
                "usage": "prefix",
                "description": _get_vocabulary_description("subject"),
            }

        # Add object vocabulary if it exists
        if hasattr(grammar_types, "Object"):
            vocabulary["object"] = {
                "segment_id": "object",
                "template": SEGMENT_TEMPLATES.get("object"),
                "tokens": _enum_values(grammar_types.Object),
                "usage": "suffix",
                "description": _get_vocabulary_description("object"),
            }

        # Add source vocabulary if it exists
        if hasattr(grammar_types, "Source"):
            vocabulary["source"] = {
                "segment_id": "source",
                "template": SEGMENT_TEMPLATES.get("source"),
                "tokens": _enum_values(grammar_types.Source),
                "usage": "suffix",
                "description": (
                    "Physical hardware or device (diagnostic or actuator) from which "
                    "measurement or signal is obtained. Use 'from_' to distinguish from "
                    "intrinsic properties (of_) of the same hardware."
                ),
            }

        # Add geometry and position vocabularies (share same tokens but different templates)
        if hasattr(grammar_types, "Position"):
            position_tokens = _enum_values(grammar_types.Position)

            vocabulary["geometry"] = {
                "segment_id": "geometry",
                "template": SEGMENT_TEMPLATES.get("geometry"),
                "tokens": position_tokens,
                "usage": "suffix",
                "description": (
                    "Intrinsic geometric properties OF the object/location "
                    "(e.g., radius_of_plasma_boundary, area_of_first_wall). "
                    "Uses 'of_' template. Mutually exclusive with 'position'."
                ),
            }

            vocabulary["position"] = {
                "segment_id": "position",
                "template": SEGMENT_TEMPLATES.get("position"),
                "tokens": position_tokens,
                "usage": "suffix",
                "description": (
                    "Field quantities evaluated AT spatial locations "
                    "(e.g., electron_temperature_at_magnetic_axis, poloidal_flux_at_plasma_boundary). "
                    "Uses 'at_' template. Mutually exclusive with 'geometry'."
                ),
            }

        # Add process vocabulary if it exists
        if hasattr(grammar_types, "Process"):
            vocabulary["process"] = {
                "segment_id": "process",
                "template": SEGMENT_TEMPLATES.get("process"),
                "tokens": _enum_values(grammar_types.Process),
                "usage": "suffix",
                "description": _get_vocabulary_description("process"),
            }

        # Critical naming rules for LLM understanding
        naming_rules = {
            "component_vs_coordinate": {
                "rule": "Choose 'component' for physical vectors, 'coordinate' for geometric vectors",
                "component_usage": {
                    "description": "Use 'component' segment for physical field quantities",
                    "applies_to_bases": [
                        "magnetic_field",
                        "electric_field",
                        "velocity",
                        "heat_flux",
                        "particle_flux",
                        "momentum_flux",
                        "current_density",
                        "gradient_of_*",
                    ],
                    "pattern": "{axis}_component_of_{base}",
                    "example": "radial_component_of_magnetic_field",
                },
                "coordinate_usage": {
                    "description": "Use 'coordinate' segment for geometric/spatial quantities",
                    "applies_to_bases": [
                        "position",
                        "vertex",
                        "outline",
                        "contour",
                        "centroid",
                        "trajectory",
                        "displacement",
                        "offset",
                        "extent",
                        "surface_normal",
                        "sensor_normal",
                        "tangent_vector",
                    ],
                    "pattern": "{axis}_{base}_of_{object}",
                    "example": "radial_position_of_flux_loop_contour",
                },
                "key_distinction": "Physical vectors (component) describe fields/fluxes/gradients; Geometric vectors (coordinate) describe locations/shapes/orientations",
            },
            "coordinate_base_naming": {
                "rule": "For cylindrical coordinate positions, use simple coordinate names as base",
                "preferred_bases": {
                    "radial": {
                        "base": "radial_position",
                        "note": "Preferred over 'major_radius' for geometric positions",
                        "example": "radial_position_of_flux_loop",
                        "pattern": "radial_position_of_{object}",
                    },
                    "vertical": {
                        "base": "vertical_position",
                        "note": "Also acceptable: 'height' (shorter alternative)",
                        "example": "vertical_position_of_flux_loop or height_of_flux_loop",
                        "pattern": "vertical_position_of_{object} or height_of_{object}",
                    },
                    "toroidal": {
                        "base": "toroidal_position",
                        "note": "For full position; use 'toroidal_angle' for angular coordinate only",
                        "example": "toroidal_position_of_flux_loop or toroidal_angle_of_flux_loop",
                        "pattern": "toroidal_position_of_{object} or toroidal_angle_of_{object}",
                    },
                },
                "deprecated_patterns": {
                    "major_radius_of_{object}": {
                        "reason": "Too verbose; prefer radial_position_of_{object}",
                        "replacement": "radial_position_of_{object}",
                        "note": "'major_radius' is physics terminology; standard names prefer coordinate-based naming",
                    },
                },
                "rationale": "Standard names should use coordinate-based terminology (radial, vertical, toroidal) rather than physics-specific terms (major_radius, Z) for consistency and simplicity.",
            },
            "object_vs_source": {
                "rule": "Use 'object' for properties OF hardware, 'source' for measurements FROM hardware",
                "object_usage": {
                    "description": "Intrinsic properties/characteristics OF the hardware",
                    "examples": [
                        "area_of_flux_loop",
                        "length_of_probe",
                        "number_of_turns_of_coil",
                        "radius_of_flux_loop_contour",
                    ],
                    "pattern": "{property}_of_{hardware}",
                },
                "source_usage": {
                    "description": "Measurements/signals obtained FROM the hardware",
                    "examples": [
                        "voltage_from_flux_loop",
                        "magnetic_field_from_probe",
                        "current_from_coil",
                    ],
                    "pattern": "{measurement}_from_{hardware}",
                },
                "key_distinction": "Properties are intrinsic (of_); Measurements are obtained (from_)",
            },
            "geometry_vs_position": {
                "rule": "Use 'geometry' for properties OF objects, 'position' for field values AT locations",
                "geometry_usage": {
                    "description": "Intrinsic geometric properties OF the object",
                    "examples": [
                        "radius_of_plasma_boundary",
                        "area_of_first_wall",
                    ],
                    "pattern": "{property}_of_{geometric_object}",
                },
                "position_usage": {
                    "description": "Field quantities evaluated AT spatial locations",
                    "examples": [
                        "electron_temperature_at_magnetic_axis",
                        "poloidal_flux_at_plasma_boundary",
                    ],
                    "pattern": "{field_quantity}_at_{location}",
                },
            },
        }

        # Composition examples with template expansion
        composition_examples = [
            {
                "name": "toroidal_component_of_magnetic_field",
                "parts": {"component": "toroidal", "base": "magnetic_field"},
                "template_expansion": "{toroidal}_component_of_{magnetic_field}",
                "description": "Component prefix with template applied",
            },
            {
                "name": "poloidal_component_of_magnetic_field",
                "parts": {"component": "poloidal", "base": "magnetic_field"},
                "template_expansion": "{poloidal}_component_of_{magnetic_field}",
                "description": "Poloidal component of magnetic field",
            },
            {
                "name": "time_derivative_of_toroidal_component_of_magnetic_field",
                "parts": {
                    "base": "time_derivative_of_toroidal_component_of_magnetic_field"
                },
                "template_expansion": "{time_derivative_of_toroidal_component_of_magnetic_field}",
                "description": "Time derivative of toroidal magnetic field component (e.g., induced voltage)",
            },
            {
                "name": "time_derivative_of_poloidal_magnetic_flux",
                "parts": {"base": "time_derivative_of_poloidal_magnetic_flux"},
                "template_expansion": "{time_derivative_of_poloidal_magnetic_flux}",
                "description": "Time derivative of poloidal magnetic flux (Faraday's law)",
            },
            {
                "name": "poloidal_magnetic_flux",
                "parts": {"base": "poloidal_magnetic_flux"},
                "template_expansion": "{poloidal_magnetic_flux}",
                "description": "Poloidal magnetic flux",
            },
            {
                "name": "plasma_current",
                "parts": {"base": "plasma_current"},
                "template_expansion": "{plasma_current}",
                "description": "Total toroidal plasma current",
            },
            {
                "name": "electron_temperature_at_magnetic_axis",
                "parts": {
                    "subject": "electron",
                    "base": "temperature",
                    "position": "magnetic_axis",
                },
                "template_expansion": "{electron}_{temperature}_at_{magnetic_axis}",
                "description": "Subject (no template) + base + position with at_ template",
            },
            {
                "name": "temperature",
                "parts": {"base": "temperature"},
                "template_expansion": "{temperature}",
                "description": "Minimal form: base only",
            },
            {
                "name": "radial_component_of_electron_density_of_plasma_boundary_due_to_conduction",
                "parts": {
                    "component": "radial",
                    "subject": "electron",
                    "base": "density",
                    "geometry": "plasma_boundary",
                    "process": "conduction",
                },
                "template_expansion": (
                    "{radial}_component_of_{electron}_{density}_of_{plasma_boundary}_due_to_{conduction}"
                ),
                "description": "Full composition with all segment types",
            },
            # Object vs Source examples (gold standard)
            {
                "name": "radial_position_of_flux_loop",
                "parts": {
                    "coordinate": "radial",
                    "base": "position",
                    "object": "flux_loop",
                },
                "template_expansion": "{radial}_{position}_of_{flux_loop}",
                "description": "Geometric position OF diagnostic hardware (cylindrical R coordinate)",
            },
            {
                "name": "poloidal_magnetic_flux_from_flux_loop",
                "parts": {
                    "base": "poloidal_magnetic_flux",
                    "source": "flux_loop",
                },
                "template_expansion": "{poloidal_magnetic_flux}_from_{flux_loop}",
                "description": "Measurement FROM diagnostic (signal obtained)",
            },
            {
                "name": "area_of_poloidal_magnetic_field_probe",
                "parts": {
                    "base": "area",
                    "object": "poloidal_magnetic_field_probe",
                },
                "template_expansion": "{area}_of_{poloidal_magnetic_field_probe}",
                "description": "Property OF diagnostic (intrinsic characteristic)",
            },
            {
                "name": "magnetic_field_from_poloidal_magnetic_field_probe",
                "parts": {
                    "base": "magnetic_field",
                    "source": "poloidal_magnetic_field_probe",
                },
                "template_expansion": "{magnetic_field}_from_{poloidal_magnetic_field_probe}",
                "description": "Measurement FROM diagnostic (field measured)",
            },
            {
                "name": "voltage_from_poloidal_magnetic_field_probe",
                "parts": {
                    "base": "voltage",
                    "source": "poloidal_magnetic_field_probe",
                },
                "template_expansion": "{voltage}_from_{poloidal_magnetic_field_probe}",
                "description": "Signal FROM diagnostic (induced voltage ∝ ∂B/∂t)",
            },
            {
                "name": "current_from_poloidal_field_coil",
                "parts": {
                    "base": "current",
                    "source": "poloidal_field_coil",
                },
                "template_expansion": "{current}_from_{poloidal_field_coil}",
                "description": "Signal FROM actuator (coil current measurement)",
            },
            {
                "name": "number_of_turns_of_poloidal_field_coil",
                "parts": {
                    "base": "number_of_turns",
                    "object": "poloidal_field_coil",
                },
                "template_expansion": "{number_of_turns}_of_{poloidal_field_coil}",
                "description": "Property OF actuator (intrinsic design parameter)",
            },
            # Component vs Coordinate examples (gold standard for geometric naming)
            {
                "name": "radial_component_of_magnetic_field",
                "parts": {
                    "component": "radial",
                    "base": "magnetic_field",
                },
                "template_expansion": "{radial}_component_of_{magnetic_field}",
                "description": "Physical vector: use COMPONENT for fields/fluxes/velocities",
            },
            {
                "name": "radial_position_of_flux_loop_contour",
                "parts": {
                    "coordinate": "radial",
                    "base": "position",
                    "object": "flux_loop_contour",
                },
                "template_expansion": "{radial}_{position}_of_{flux_loop_contour}",
                "description": "Geometric vector: use COORDINATE for position/vertex/centroid (R coordinate)",
            },
            {
                "name": "vertical_position_of_flux_loop_contour",
                "parts": {
                    "coordinate": "vertical",
                    "base": "position",
                    "object": "flux_loop_contour",
                },
                "template_expansion": "{vertical}_{position}_of_{flux_loop_contour}",
                "description": "Geometric vector: use COORDINATE for position/vertex/centroid (Z coordinate)",
            },
            {
                "name": "toroidal_position_of_flux_loop_contour",
                "parts": {
                    "coordinate": "toroidal",
                    "base": "position",
                    "object": "flux_loop_contour",
                },
                "template_expansion": "{toroidal}_{position}_of_{flux_loop_contour}",
                "description": "Geometric vector: use COORDINATE for position/vertex/centroid (φ coordinate)",
            },
            {
                "name": "x_vertex_of_first_wall_mesh",
                "parts": {
                    "coordinate": "x",
                    "base": "vertex",
                    "object": "first_wall_mesh",
                },
                "template_expansion": "{x}_{vertex}_of_{first_wall_mesh}",
                "description": "3D mesh geometry: COORDINATE with 'vertex' base for shape-defining points",
            },
            {
                "name": "radial_centroid_of_plasma",
                "parts": {
                    "coordinate": "radial",
                    "base": "centroid",
                    "object": "plasma",
                },
                "template_expansion": "{radial}_{centroid}_of_{plasma}",
                "description": "Geometric center: COORDINATE with 'centroid' base",
            },
            {
                "name": "radial_displacement_of_divertor_tile",
                "parts": {
                    "coordinate": "radial",
                    "base": "displacement",
                    "object": "divertor_tile",
                },
                "template_expansion": "{radial}_{displacement}_of_{divertor_tile}",
                "description": "Position change: COORDINATE with 'displacement' base (e.g., thermal expansion)",
            },
            {
                "name": "radial_surface_normal_of_first_wall",
                "parts": {
                    "coordinate": "radial",
                    "base": "surface_normal",
                    "object": "first_wall",
                },
                "template_expansion": "{radial}_{surface_normal}_of_{first_wall}",
                "description": "Surface orientation: use COORDINATE for geometric normals (describes surface geometry, not a physical field)",
            },
        ]

        # Generation rules for creating new standard names from patterns
        generation_rules = {
            "description": "Rules for generating new standard names from patterns and context",
            "vector_generation": {
                "description": "Identify and generate parent vector quantities from scalar components",
                "trigger": "When ≥2 scalars differ only in axis/component prefix but share all other segments",
                "minimum_components": 2,
                "detection_patterns": [
                    {
                        "type": "physical_vector",
                        "scalar_pattern": "{axis}_component_of_{base}[_{qualifiers}]",
                        "parent_pattern": "{base}[_{qualifiers}]",
                        "segment_used": "component",
                        "examples": [
                            {
                                "scalars": [
                                    "radial_component_of_magnetic_field",
                                    "toroidal_component_of_magnetic_field",
                                    "vertical_component_of_magnetic_field",
                                ],
                                "inferred_parent": "magnetic_field",
                                "description": "Physical field vector",
                            },
                            {
                                "scalars": [
                                    "radial_component_of_gradient_of_poloidal_flux",
                                    "vertical_component_of_gradient_of_poloidal_flux",
                                ],
                                "inferred_parent": "gradient_of_poloidal_flux",
                                "description": "Derived physical vector (gradient operator)",
                                "requires_provenance": {
                                    "mode": "operator",
                                    "operators": ["gradient"],
                                    "base": "poloidal_flux",
                                    "operator_id": "gradient",
                                },
                            },
                        ],
                    },
                    {
                        "type": "geometric_vector",
                        "scalar_pattern": "{axis}_{base}_of_{object}[_{qualifiers}]",
                        "parent_pattern": "{base}_of_{object}[_{qualifiers}]",
                        "segment_used": "coordinate",
                        "examples": [
                            {
                                "scalars": [
                                    "radial_position_of_flux_loop",
                                    "vertical_position_of_flux_loop",
                                ],
                                "inferred_parent": "position_of_flux_loop",
                                "description": "Geometric position vector",
                            },
                            {
                                "scalars": [
                                    "x_vertex_of_first_wall_mesh",
                                    "y_vertex_of_first_wall_mesh",
                                    "z_vertex_of_first_wall_mesh",
                                ],
                                "inferred_parent": "vertex_of_first_wall_mesh",
                                "description": "3D mesh geometry vector",
                            },
                        ],
                    },
                ],
                "grouping_algorithm": {
                    "description": "How to detect parent vector candidates",
                    "steps": [
                        "Parse each scalar name into segments",
                        "For component-prefixed: extract axis from '{axis}_component_of_', keep remainder",
                        "For coordinate-prefixed: extract axis token, keep remainder",
                        "Group scalars by identical remainder (potential parent name)",
                        "If group size ≥ 2, flag as parent vector candidate",
                    ],
                },
                "parent_vector_template": {
                    "base_vector": {
                        "name": "<inferred_parent_name>",
                        "kind": "vector",
                        "unit": "<same_as_components>",
                        "status": "draft",
                        "description": "<generated_description>",
                    },
                    "derived_vector": {
                        "name": "<inferred_parent_name>",
                        "kind": "vector",
                        "unit": "<derived_unit>",
                        "status": "draft",
                        "description": "<generated_description>",
                        "provenance": {
                            "mode": "operator",
                            "operators": ["<operator>"],
                            "base": "<base_quantity>",
                            "operator_id": "<operator>",
                        },
                    },
                },
                "workflow_integration": {
                    "when": "After generating component scalars, before finalization",
                    "steps": [
                        "Collect all generated scalar names",
                        "Apply grouping algorithm to identify parent candidates",
                        "For each candidate group:",
                        "  - Determine if derived (contains operator pattern) or base",
                        "  - Generate appropriate vector YAML",
                        "  - Add to generation batch",
                    ],
                },
                "key_principles": [
                    "No semantic filtering - any base can form a vector",
                    "Pattern-driven - structural detection only",
                    "Minimal vectors - no frame/components/magnitude fields in YAML",
                    "Provenance added only for derived vectors (contains operators)",
                    "Unit must match component unit",
                    "Works bidirectionally: IDS→scalars→vector OR direct generation",
                ],
            },
            "magnitude_generation": {
                "description": "Generate magnitude scalar from vector quantities",
                "trigger": "When a vector entry is created",
                "automatic": False,
                "note": "Magnitude is a computed property; optionally create explicit scalar with reduction provenance",
                "template": {
                    "name": "magnitude_of_{vector_name}",
                    "kind": "scalar",
                    "unit": "<same_as_vector>",
                    "status": "draft",
                    "description": "Magnitude (L2 norm) of {vector_name}.",
                    "provenance": {
                        "mode": "reduction",
                        "reduction": "magnitude",
                        "domain": "none",
                        "base": "{vector_name}",
                    },
                },
                "examples": [
                    {
                        "vector": "magnetic_field",
                        "magnitude_name": "magnitude_of_magnetic_field",
                        "unit": "T",
                    },
                    {
                        "vector": "gradient_of_poloidal_flux",
                        "magnitude_name": "magnitude_of_gradient_of_poloidal_flux",
                        "unit": "Wb.m^-1",
                    },
                ],
            },
        }

        # Counts by kind and status
        kind_counts = Counter(m.kind for m in models)
        status_counts = Counter(m.status for m in models)

        all_kinds = ["scalar", "vector"]
        standard_names_by_kind = {k: kind_counts.get(k, 0) for k in all_kinds}

        all_status = ["draft", "active", "deprecated", "superseded"]
        standard_names_by_status = {s: status_counts.get(s, 0) for s in all_status}

        unit_counter = Counter(
            "dimensionless" if m.unit == "" else m.unit for m in models
        )
        standard_names_by_unit = dict(sorted(unit_counter.items()))

        # Tag aggregation (flatten all tags; ignore empty tag lists)
        tag_counter = Counter(tag for m in models for tag in (m.tags or []))
        standard_names_by_tag = dict(sorted(tag_counter.items()))

        return {
            "scope": {
                "include": list(SCOPE_INCLUDE),
                "exclude": list(SCOPE_EXCLUDE),
                "rationale": SCOPE_RATIONALE,
            },
            "grammar_structure": grammar_structure,
            "vocabulary": vocabulary,
            "naming_rules": naming_rules,
            "validation_rules": validation_rules,
            "generation_rules": generation_rules,
            "composition_examples": composition_examples,
            "catalog_stats": {
                "total_standard_names": total,
                "standard_names_by_kind": standard_names_by_kind,
                "standard_names_by_status": standard_names_by_status,
                "standard_names_by_unit": standard_names_by_unit,
                "standard_names_by_tag": standard_names_by_tag,
            },
            "version": package_version,
        }

    @mcp_tool(
        description=(
            "List standard names with persistence status classification. Optional 'scope' "
            "argument filters output: all (default) | persisted | pending | new | modified | renamed | deleted. "
            "Also accepts legacy aliases: saved (for persisted) | unsaved (for pending). "
            "Returns base structure {universal_set, persisted, pending{new,modified,rename_map,deleted}, counts} "
            "for scope=all or persisted only, pending block only, or a single list depending on scope. "
            "Persisted names exist as YAML files on disk; pending names exist only in-memory. "
            "Renamed entries returned as mapping old_name->new_name. "
            "Use this when you need to enumerate/browse all available names or filter by persistence status. "
            "For finding specific names by concept use search_standard_names; for details of known names use fetch_standard_names."
        )
    )
    async def list_standard_names(self, scope: str = "all", ctx: Context | None = None):  # noqa: D401
        """Return persisted vs pending standard name identifiers.

        Fields:
            universal_set: all in-memory names.
            persisted: names written to disk as YAML files.
            pending.new / pending.deleted: set membership differences.
            pending.modified: structurally changed entries (needs EditCatalog).
            pending.rename_map: old_name -> new_name mapping for renames.
            counts: *_count metrics plus pending_total_count.
        """
        # Saved names from disk (filenames without parsing).
        saved = [
            f.stem
            for f in self.catalog.store.yaml_files()  # type: ignore[attr-defined]
        ]
        saved.sort()

        # Universal (current) names.
        universal_set = self.catalog.list_names()

        # Initialize unsaved diff containers.
        new: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        rename_map: dict[str, str] = {}

        # Use an attached EditCatalog instance (if any) for unsaved diffs
        edit_repo = getattr(self, "edit_catalog", None)
        if edit_repo is not None and hasattr(edit_repo, "diff"):
            try:
                diff = edit_repo.diff()
                new = [e["name"] for e in diff.get("added", [])]
                deleted = [e["name"] for e in diff.get("removed", [])]
                modified = [e["name"] for e in diff.get("updated", [])]
                rename_map = {
                    r.get("from"): r.get("to")  # type: ignore[dict-item]
                    for r in diff.get("renamed", [])
                    if r.get("from") and r.get("to")
                }
            except Exception:  # pragma: no cover
                edit_repo = None

        if edit_repo is None:
            saved_set = set(saved)
            current_set = set(universal_set)
            new = sorted(current_set - saved_set)
            deleted = sorted(saved_set - current_set)
            # modified + rename_map remain empty

        counts = {
            "universal_count": len(universal_set),
            "persisted_count": len(saved),
            "new_count": len(new),
            "modified_count": len(modified),
            "renamed_count": len(rename_map),
            "deleted_count": len(deleted),
            # Backward compatibility
            "saved_count": len(saved),
        }
        counts["pending_total_count"] = (
            counts["new_count"]
            + counts["modified_count"]
            + counts["renamed_count"]
            + counts["deleted_count"]
        )
        # Backward compatibility
        counts["unsaved_total_count"] = counts["pending_total_count"]

        scope_normalized = scope.lower().strip()
        # Map legacy aliases to new names
        scope_map = {
            "saved": "persisted",
            "unsaved": "pending",
        }
        scope_normalized = scope_map.get(scope_normalized, scope_normalized)

        valid_scopes = {
            "all",
            "persisted",
            "pending",
            "new",
            "modified",
            "renamed",
            "deleted",
        }
        if scope_normalized not in valid_scopes:
            raise ValueError(
                f"Invalid scope '{scope}'; expected one of: {', '.join(sorted(valid_scopes))} "
                f"(legacy aliases: saved, unsaved)"
            )

        base_payload = {
            "universal_set": universal_set,
            "persisted": saved,
            "pending": {
                "new": new,
                "modified": modified,
                "rename_map": rename_map,
                "deleted": deleted,
            },
            "counts": counts,
            # Backward compatibility
            "saved": saved,
            "unsaved": {
                "new": new,
                "modified": modified,
                "rename_map": rename_map,
                "deleted": deleted,
            },
        }

        match scope_normalized:
            case "all":
                return base_payload
            case "persisted":
                return {"persisted": saved, "counts": counts}
            case "pending":
                return {"pending": base_payload["pending"], "counts": counts}
            case "new":
                return {"new": new, "counts": counts}
            case "modified":
                return {"modified": modified, "counts": counts}
            case "renamed":
                return {"rename_map": rename_map, "counts": counts}
            case "deleted":
                return {"deleted": deleted, "counts": counts}

    @mcp_tool(
        description=(
            "Get comprehensive JSON schema and gold-standard examples for standard name catalog entries. "
            "Use this tool before staging new entries to understand required/optional fields, validation rules, "
            "provenance patterns, and best practices. Returns schemas for scalar and vector entries with "
            "realistic examples from fusion diagnostics and plasma physics, plus complete workflow guidance. "
            "Essential reference for constructing valid model dicts for edit_standard_name action='add'."
        )
    )
    async def get_catalog_entry_schema(self, ctx: Context | None = None):
        """Return comprehensive schema and examples for catalog entries.

        This tool provides everything an LLM needs to efficiently create valid catalog entries:
        - Complete Pydantic JSON schemas for scalar and vector entries
        - Provenance schema variants (operator, reduction, expression)
        - Gold-standard examples covering common patterns
        - Field descriptions, validation rules, and defaults
        - Best practices for documentation and metadata
        """
        from imas_standard_names.grammar.tag_types import (
            PRIMARY_TAG_DESCRIPTIONS,
            PRIMARY_TAGS,
            SECONDARY_TAG_DESCRIPTIONS,
            SECONDARY_TAGS,
        )
        from imas_standard_names.models import (
            _STANDARD_NAME_ENTRY_ADAPTER,
            StandardNameScalarEntry,
            StandardNameVectorEntry,
        )
        from imas_standard_names.provenance import (
            ExpressionProvenance,
            OperatorProvenance,
            ReductionProvenance,
        )

        return {
            "required_fields": {
                "scalar": ["name", "description", "kind"],
                "vector": ["name", "description", "kind"],
            },
            "field_defaults": {
                "status": "draft",
                "documentation": "",
                "unit": "",
                "validity_domain": "",
                "constraints": [],
                "deprecates": "",
                "superseded_by": "",
                "tags": [],
                "links": [],
                "provenance": None,
            },
            "schemas": {
                "scalar": StandardNameScalarEntry.model_json_schema(),
                "vector": StandardNameVectorEntry.model_json_schema(),
                "union_schema": _STANDARD_NAME_ENTRY_ADAPTER.json_schema(),
                "provenance": {
                    "operator": OperatorProvenance.model_json_schema(),
                    "reduction": ReductionProvenance.model_json_schema(),
                    "expression": ExpressionProvenance.model_json_schema(),
                },
            },
            "tag_vocabulary": {
                "primary_tags": {
                    tag: PRIMARY_TAG_DESCRIPTIONS[tag] for tag in PRIMARY_TAGS
                },
                "secondary_tags": {
                    tag: SECONDARY_TAG_DESCRIPTIONS[tag] for tag in SECONDARY_TAGS
                },
                "usage": {
                    "primary_tag": "First element (tags[0]) must be a primary tag from the controlled vocabulary. Defines catalog subdirectory organization. Common primary tags: 'magnetics', 'fundamental', 'equilibrium', 'transport', 'core-physics', 'edge-physics', 'mhd', etc.",
                    "secondary_tags": "Remaining elements (tags[1:]) provide cross-cutting classification using secondary tags. Examples: 'measured', 'calibrated', 'cylindrical-coordinates', 'local-measurement', 'time-dependent', 'spatial-profile', etc.",
                    "validation": "All tags validated against controlled vocabulary in grammar/vocabularies/tags.yml. Validation will fail if tags[0] is not a primary tag.",
                    "common_mistake": "Do not put secondary tags like 'cylindrical-coordinates' or 'local-measurement' at position 0. Always start with a primary tag like 'magnetics'.",
                },
                "all_primary_tags_list": list(PRIMARY_TAGS),
                "all_secondary_tags_list": list(SECONDARY_TAGS),
                "quick_reference": {
                    "diagnostic_primary_tags": [
                        "magnetics",
                        "thomson-scattering",
                        "interferometry",
                        "reflectometry",
                        "spectroscopy",
                        "radiation-diagnostics",
                        "imaging",
                        "neutronics",
                    ],
                    "physics_primary_tags": [
                        "fundamental",
                        "equilibrium",
                        "core-physics",
                        "transport",
                        "edge-physics",
                        "mhd",
                        "turbulence",
                        "plasma-initiation",
                    ],
                    "heating_primary_tags": [
                        "nbi",
                        "ec-heating",
                        "ic-heating",
                        "lh-heating",
                        "waves",
                    ],
                    "common_secondary_for_diagnostics": [
                        "measured",
                        "calibrated",
                        "raw-data",
                        "time-dependent",
                        "local-measurement",
                        "spatial-profile",
                        "cylindrical-coordinates",
                    ],
                    "common_secondary_for_hardware": [
                        "calibrated",
                        "local-measurement",
                        "cylindrical-coordinates",
                    ],
                    "critical_rule": "ALWAYS check: is tags[0] in PRIMARY_TAGS? If not, reorder or select correct primary tag.",
                },
            },
            "alignment_with_imas_data_dictionary": {
                "summary": (
                    "When deriving standard names from IMAS IDS paths, use IMAS DD "
                    "as the primary reference for sign conventions, units, and physical "
                    "definitions. IMAS DD has gaps and inconsistencies - adapt as needed. "
                    "Standard name entries must be standalone and self-contained."
                ),
                "principles": [
                    (
                        "Sign conventions: Use IMAS DD as primary reference; "
                        "define clearly if absent or ambiguous"
                    ),
                    (
                        "Units: Use IMAS DD units as starting point; "
                        "harmonize inconsistencies where needed"
                    ),
                    (
                        "Description field: Keep short (1-2 sentences); "
                        "basic definition without extensive detail"
                    ),
                    (
                        "Documentation field: Expand from IMAS DD source; "
                        "add context, conventions, equations, and usage notes beyond DD content"
                    ),
                    (
                        "Self-contained: Never reference IMAS DD paths - "
                        "entries must be understandable independently"
                    ),
                ],
                "example_with_explicit_convention": {
                    "imas_path": "magnetics/flux_loop/flux",
                    "imas_dd_text": (
                        "Measured magnetic flux over loop in which Z component of "
                        "normal to loop is directed downwards (negative grad Z direction)"
                    ),
                    "standard_name": "poloidal_magnetic_flux_from_flux_loop",
                    "description": ("Poloidal magnetic flux measured by flux loop"),
                    "documentation": (
                        "Poloidal magnetic flux measured through a flux loop coil, "
                        "defined as $\\Phi_p = \\int \\mathbf{B}_p \\cdot d\\mathbf{A}$ "
                        "where the integration is over the loop area. "
                        "Sign convention: positive when the normal vector to the loop "
                        "points downward (negative Z direction). "
                        "By Faraday's law, the induced voltage is proportional to the "
                        "time derivative: $V_{induced} = -d\\Phi_p/dt$. "
                        "Used for equilibrium reconstruction and plasma current estimation."
                    ),
                    "note": (
                        "Description is short; documentation expands IMAS DD text "
                        "with LaTeX equations, context and usage"
                    ),
                },
                "example_without_explicit_convention": {
                    "imas_path": "magnetics/bpol_probe/field",
                    "imas_dd_text": (
                        "Magnetic field component in direction of sensor normal axis (n) "
                        "averaged over sensor volume"
                    ),
                    "standard_name": "poloidal_magnetic_field_from_poloidal_magnetic_field_probe",
                    "description": (
                        "Poloidal magnetic field component measured by probe"
                    ),
                    "documentation": (
                        "Poloidal magnetic field component measured by a probe coil, "
                        "averaged over the sensor volume. The measurement is taken along "
                        "the sensor normal axis direction (positive in direction of sensor "
                        "normal). Used for local magnetic field measurements and plasma "
                        "position control."
                    ),
                    "note": (
                        "Description is concise; documentation adds detail on sign convention, "
                        "averaging, and usage"
                    ),
                },
            },
            "examples": {
                "minimal_scalar": {
                    "name": "plasma_current",
                    "kind": "scalar",
                    "description": "Total toroidal plasma current.",
                    # Only name, kind, description are strictly required
                    # All other fields have defaults (see field_defaults below)
                },
                "diagnostic_measurement_scalar": {
                    "name": "electron_temperature_from_thomson_scattering",
                    "kind": "scalar",
                    "description": "Electron temperature measured by Thomson scattering diagnostic system.",
                    "unit": "eV",
                    "status": "active",
                    "tags": [
                        "thomson-scattering",
                        "measured",
                        "spatial-profile",
                        "calibrated",
                    ],
                    "validity_domain": "core_plasma",
                    "constraints": ["T_e >= 0"],
                    "documentation": (
                        "Electron temperature obtained from Thomson scattering diagnostic channels. "
                        "The measurement is based on spectral analysis of laser light scattered by plasma electrons. "
                        "Spatial resolution is determined by the laser beam geometry and collection optics. "
                        "Typical measurement uncertainty is 10-15% for temperatures above 100 eV. "
                        "Data quality depends on laser pulse energy and should be validated against "
                        "charge exchange spectroscopy or ECE measurements."
                    ),
                    "links": [
                        "https://doi.org/10.1088/example-thomson-diagnostic",
                        "https://imas.iter.org/ids/thomson_scattering",
                    ],
                },
                "hardware_property_scalar": {
                    "name": "area_of_poloidal_magnetic_field_probe",
                    "kind": "scalar",
                    "description": "Effective sensing area of a poloidal magnetic field probe coil.",
                    "unit": "m^2",
                    "status": "active",
                    "tags": ["magnetics", "calibrated"],
                    "constraints": ["area > 0"],
                    "documentation": (
                        "Cross-sectional area of each turn in the poloidal magnetic field probe sensor coil. "
                        "The effective sensing area is obtained by multiplying this value by the number of turns. "
                        "This parameter is essential for converting measured voltages to magnetic field values "
                        "via Faraday's law:\n\n"
                        "$$V = -N A \\frac{dB}{dt}$$\n\n"
                        "where $N$ is the number of turns, $A$ is this area, and $\\frac{dB}{dt}$ is the time "
                        "derivative of the magnetic field component perpendicular to the coil. "
                        "Calibration should account for geometric factors and coil positioning."
                    ),
                },
                "geometric_coordinate_scalar": {
                    "name": "radial_position_of_flux_loop",
                    "kind": "scalar",
                    "description": "Major radius (R coordinate) of a flux loop measurement point in cylindrical coordinates.",
                    "unit": "m",
                    "status": "active",
                    "tags": [
                        "magnetics",
                        "cylindrical-coordinates",
                        "local-measurement",
                    ],
                    "validity_domain": "whole_device",
                    "constraints": ["R > 0"],
                    "documentation": (
                        "Radial coordinate (major radius R) defining the spatial location of a flux loop measurement point. "
                        "Part of (R,Z,phi) triplet describing the loop geometry in cylindrical coordinates. "
                        "Multiple position points define the complete flux loop contour used for poloidal flux measurements. "
                        "Accurate positioning is critical for equilibrium reconstruction and MHD stability analysis."
                    ),
                },
                "derived_with_operator_provenance": {
                    "name": "gradient_of_electron_temperature",
                    "kind": "vector",
                    "description": "Spatial gradient of electron temperature forming a vector field.",
                    "unit": "eV.m^-1",
                    "status": "active",
                    "tags": ["transport", "derived", "spatial-profile"],
                    "provenance": {
                        "mode": "operator",
                        "operators": ["gradient"],
                        "base": "electron_temperature",
                        "operator_id": "gradient",
                    },
                    "documentation": (
                        "Vector field representing the spatial gradient of electron temperature $\\nabla T_e$. "
                        "Essential for analyzing heat transport and confinement properties via the heat flux relation:\n\n"
                        "$$\\mathbf{q} = -\\chi \\nabla T_e$$\n\n"
                        "where $\\chi$ is the thermal diffusivity. "
                        "Calculated from fitted temperature profiles using numerical differentiation. "
                        "Components should be expressed in the local coordinate system (radial, poloidal, toroidal). "
                        "Large gradients indicate strong transport barriers or edge pedestals."
                    ),
                },
                "derived_with_reduction_provenance": {
                    "name": "time_average_of_electron_density",
                    "kind": "scalar",
                    "description": "Time-averaged electron number density over a specified interval.",
                    "unit": "m^-3",
                    "status": "active",
                    "tags": ["fundamental", "derived", "steady-state"],
                    "provenance": {
                        "mode": "reduction",
                        "reduction": "mean",
                        "domain": "time",
                        "base": "electron_density",
                    },
                    "documentation": (
                        "Electron density averaged over a time interval, typically used for steady-state analysis. "
                        "The averaging interval should be chosen to smooth out fast fluctuations while preserving "
                        "slower transport dynamics. Common intervals: 10-100ms for ELM-free periods, longer for "
                        "equilibrium phases. Should specify averaging method (arithmetic mean) and time window width."
                    ),
                },
                "minimal_vector": {
                    "name": "magnetic_field",
                    "kind": "vector",
                    "description": "Magnetic field vector in plasma.",
                    "unit": "T",
                },
                "full_vector": {
                    "name": "plasma_velocity",
                    "kind": "vector",
                    "description": "Bulk plasma velocity vector field.",
                    "unit": "m.s^-1",
                    "status": "active",
                    "tags": ["transport", "spatial-profile", "momentum-balance"],
                    "validity_domain": "whole_plasma",
                    "documentation": (
                        "Three-dimensional plasma velocity field vector. "
                        "Components represent velocity in radial, poloidal, and toroidal directions. "
                        "Toroidal rotation is typically measured by charge exchange spectroscopy, "
                        "while poloidal and radial components are often inferred from modeling. "
                        "Important for momentum transport analysis and rotation-driven stabilization studies."
                    ),
                },
                "deprecated_entry": {
                    "name": "old_temperature_measurement",
                    "kind": "scalar",
                    "description": "Legacy temperature measurement (deprecated).",
                    "unit": "eV",
                    "status": "deprecated",
                    "superseded_by": "electron_temperature_from_thomson_scattering",
                    "documentation": (
                        "This entry has been deprecated in favor of more specific diagnostic-based naming. "
                        "Use electron_temperature_from_thomson_scattering for Thomson scattering data."
                    ),
                },
                "operator_provenance_with_base_matching": {
                    "name": "time_derivative_of_plasma_current",
                    "kind": "scalar",
                    "description": "Time rate of change of total toroidal plasma current.",
                    "unit": "A.s^-1",
                    "status": "draft",
                    "tags": ["fundamental", "derived", "time-dependent"],
                    "provenance": {
                        "mode": "operator",
                        "operators": ["time_derivative"],
                        "base": "plasma_current",
                        "operator_id": "time_derivative",
                    },
                    "documentation": (
                        "Time derivative of the total toroidal plasma current dI_p/dt. "
                        "Important: The provenance.base field must match the base segment extracted from the name. "
                        "For 'time_derivative_of_plasma_current', the base is 'plasma_current' (not a longer diagnostic-specific name). "
                        "This derivative is related to loop voltage and resistive diffusion time. "
                        "Rapid current changes indicate MHD events or disruptions."
                    ),
                },
                "batch_operation_example": {
                    "_tool": "create_standard_names",
                    "_description": "Use create_standard_names for batch creation of new entries",
                    "entries": [
                        {
                            "name": "plasma_current",
                            "kind": "scalar",
                            "description": "Total toroidal plasma current.",
                            "unit": "A",
                            "status": "draft",
                            "tags": ["fundamental", "global-quantity", "measured"],
                        },
                        {
                            "name": "time_derivative_of_plasma_current",
                            "kind": "scalar",
                            "description": "Time rate of change of plasma current.",
                            "unit": "A.s^-1",
                            "status": "draft",
                            "tags": ["fundamental", "derived", "time-dependent"],
                            "provenance": {
                                "mode": "operator",
                                "operators": ["time_derivative"],
                                "base": "plasma_current",
                            },
                        },
                        {
                            "name": "magnetic_field_probe_voltage",
                            "kind": "scalar",
                            "description": "Voltage induced in magnetic field probe coil.",
                            "unit": "V",
                            "status": "draft",
                            "tags": ["magnetics", "measured", "raw-data"],
                        },
                    ],
                    "mode": "continue",
                    "dry_run": False,
                    "_note": (
                        "create_standard_names batch operations support: (1) Automatic dependency ordering - entries are "
                        "topologically sorted based on provenance.base references, (2) mode='continue' "
                        "processes all entries and accumulates errors per-entry, (3) mode='atomic' "
                        "rolls back all changes if any entry fails, (4) dry_run=True validates "
                        "without adding to catalog. "
                        "Typical workflow: set dry_run=True first to validate, fix errors, then run with "
                        "dry_run=False. Use mode='continue' for bulk imports where partial success is "
                        "acceptable, mode='atomic' for related changes that must all succeed together. "
                        "After creation, use list_standard_names(scope='unsaved') to review, then "
                        "write_standard_names() to persist to disk."
                    ),
                },
            },
            "validation_rules": {
                "name": {
                    "pattern": "^[a-z][a-z0-9_]*$",
                    "description": "Must be snake_case; start with letter; no double underscores (__)",
                    "examples": [
                        "electron_temperature",
                        "radial_position_of_flux_loop",
                    ],
                },
                "unit": {
                    "format": "dot-exponent style with lexicographic token order",
                    "description": "Use '.' to join tokens; '^' for exponents; no '/' or '*'; empty for dimensionless",
                    "examples": ["eV", "m", "m.s^-1", "A.m^-2", "T", "Wb", ""],
                    "invalid": ["m/s", "kg*m", "m s^-2"],
                },
                "description": {
                    "max_length": 180,
                    "guidelines": "One concise sentence summarizing the quantity; avoid repetition of the name. Do not reference IMAS or the Data Dictionary (DD).",
                },
                "documentation": {
                    "guidelines": (
                        "Extended details about the quantity including: "
                        "physical interpretation, measurement method, typical values, "
                        "validation requirements, references. "
                        "Do not reference IMAS, the Data Dictionary (DD), or implementation-specific paths. "
                        "Use Markdown with LaTeX for all equations ($...$ inline, $$...$$ display). "
                        "Examples: Faraday $V = -\\frac{d\\Phi}{dt}$, Ampère $$\\nabla \\times \\mathbf{B} = \\mu_0 \\mathbf{J}$$, "
                        "transport $\\Gamma = -D \\nabla n + v n$. "
                        "Wrap text to ~80 characters per line. "
                        "Use YAML block scalar (|) syntax to preserve formatting."
                    ),
                },
                "status": {
                    "values": ["draft", "active", "deprecated", "superseded"],
                    "rules": {
                        "draft": "Initial creation; not yet validated",
                        "active": "Validated and approved for use",
                        "deprecated": "Must set superseded_by field",
                        "superseded": "Not currently used",
                    },
                },
                "kind": {
                    "values": ["scalar", "vector"],
                    "description": "Discriminator field determining entry type",
                },
                "provenance": {
                    "modes": ["operator", "reduction", "expression"],
                    "description": "Describes how derived quantities are computed from base quantities",
                    "operator_example": "gradient, divergence, curl, time_derivative",
                    "reduction_example": "mean, rms, integral over time/volume/surface",
                },
                "tags": {
                    "requirement": "Must contain exactly one primary tag; may contain zero or more secondary tags",
                    "primary_tags": {
                        "count": len(PRIMARY_TAGS),
                        "examples": list(PRIMARY_TAGS)[:12],
                        "note": "See tag_vocabulary for complete list with descriptions",
                    },
                    "secondary_tags": {
                        "count": len(SECONDARY_TAGS),
                        "examples": list(SECONDARY_TAGS)[:12],
                        "note": "See tag_vocabulary for complete list with descriptions",
                    },
                    "validation": (
                        "Pre-validation automatically ensures exactly one primary tag is present "
                        "and places it at position 0. Schema validation then enforces tags[0] is "
                        "from PRIMARY_TAGS vocabulary and tags[1:] are from SECONDARY_TAGS vocabulary."
                    ),
                    "correct_examples": [
                        ["magnetics", "measured", "cylindrical-coordinates"],
                        ["equilibrium", "reconstructed", "flux-surface-average"],
                        ["fundamental", "global-quantity"],
                    ],
                    "automatic_reordering": (
                        "If tags contain exactly one primary tag but it's not at position 0, "
                        "it will be automatically moved to the first position during validation. "
                        "Example: ['measured', 'magnetics'] → ['magnetics', 'measured']"
                    ),
                },
            },
            "common_patterns": {
                "diagnostic_measurements": "quantity_from_diagnostic_name (e.g., temperature_from_thomson_scattering)",
                "hardware_properties": "property_of_hardware (e.g., area_of_probe, turns_of_coil)",
                "geometric_positions": "coordinate_position_of_object (e.g., radial_position_of_flux_loop)",
                "derived_operators": "operator_of_base (e.g., gradient_of_temperature, divergence_of_flux)",
                "derived_reductions": "reduction_domain_of_base (e.g., time_average_of_density, volume_integral_of_power)",
                "field_components": "coordinate_component_of_vector (e.g., radial_component_of_magnetic_field)",
            },
            "best_practices": {
                "naming": [
                    "Use grammar vocabulary tokens for segments (get_grammar_and_vocabulary tool)",
                    "Follow segment order: [component/coordinate] [subject] base [object/source] [geometry/position] [process]",
                    "Use 'of_' for hardware properties: area_of_probe, length_of_coil",
                    "Use 'from_' for measurements: voltage_from_probe, flux_from_loop",
                    "For cylindrical coordinates: prefer radial_position, vertical_position (or height), toroidal_angle",
                    "Avoid physics-specific terms as base: use radial_position_of_{object} not major_radius_of_{object}",
                    "Use coordinate prefix for geometric positions: radial_position_of_flux_loop, height_of_probe",
                    "Use component prefix for field vectors: radial_component_of_magnetic_field",
                ],
                "units": [
                    "Prefer SI base units or eV for energy/temperature",
                    "Use lexicographically sorted tokens: 'A.m^-2' not 'm^-2.A'",
                    "Specify dimensionless as empty string, not '1' or 'dimensionless'",
                ],
                "documentation": [
                    "Do not reference IMAS, the Data Dictionary (DD), or implementation-specific paths",
                    "Include physical interpretation and context",
                    "Specify measurement method and typical uncertainty",
                    "Note validation requirements and cross-diagnostic checks",
                    "Provide references to relevant papers or documentation",
                    "Describe coordinate systems and normalization conventions",
                    "Use Markdown formatting for readability (bold, italics, lists, code blocks)",
                    "Use LaTeX for all equations and mathematical expressions",
                    "Inline math: $\\Phi = \\int \\mathbf{B} \\cdot d\\mathbf{A}$, $\\nabla T_e$, $\\frac{\\partial \\psi}{\\partial t}$",
                    "Display math: $$V = -N A \\frac{dB}{dt}$$, $$\\nabla \\times \\mathbf{B} = \\mu_0 \\mathbf{J}$$, $$Q = P \\cdot \\frac{dV}{dt}$$",
                    "Physics examples: Faraday induction $V = -\\frac{d\\Phi}{dt}$, transport flux $\\Gamma = -D \\nabla n + v n$, beta $\\beta = \\frac{2\\mu_0 p}{B^2}$",
                    "Vector operations: gradient $\\nabla \\psi$, divergence $\\nabla \\cdot \\mathbf{\\Gamma}$, curl $\\nabla \\times \\mathbf{E}$, Laplacian $\\nabla^2 \\psi$",
                    "Wrap text to ~80 characters per line for YAML readability",
                    "Use YAML block scalar (|) to preserve line breaks and formatting",
                ],
                "tags": [
                    "First tag (tags[0]) must be a primary tag from controlled vocabulary",
                    "Common primary tags: 'magnetics', 'fundamental', 'equilibrium', 'transport', 'core-physics', 'edge-physics'",
                    "Do not use secondary tags at position 0: 'cylindrical-coordinates', 'local-measurement', 'calibrated', etc.",
                    "Example correct: ['magnetics', 'measured', 'cylindrical-coordinates']",
                    "Example wrong: ['cylindrical-coordinates', 'magnetics'] - will fail validation",
                    "Secondary tags (tags[1:]) provide cross-cutting classification",
                    "Common secondary tags: measured, reconstructed, simulated, derived, validated, calibrated",
                    "Temporal: time-dependent, steady-state, transient, long-timescale",
                    "Spatial: spatial-profile, flux-surface-average, volume-average, line-integrated, local-measurement, global-quantity, cylindrical-coordinates",
                    "Physics domain: equilibrium-reconstruction, transport-modeling, mhd-stability-analysis, heating-deposition",
                    "Data quality: calibrated, raw-data, real-time, post-shot-analysis, benchmark-quantity",
                    "Use get_catalog_entry_schema tool to see complete tag vocabulary with descriptions",
                ],
                "metadata": [
                    "Set appropriate validity_domain: core_plasma, edge_plasma, vacuum, whole_plasma, whole_device",
                    "Add constraints for physical bounds: T >= 0, n_e >= 0, R > 0",
                    "Link to relevant documentation, papers, or specifications",
                    "Use provenance for derived quantities to track dependencies",
                ],
            },
            "tool_usage_workflow": [
                "1. Call get_grammar_and_vocabulary to understand naming rules and vocabulary",
                "2. Call get_catalog_entry_schema (this tool) to see entry structure and examples",
                "3. Create entry dict(s) following schema and examples - ENSURE tags[0] is a PRIMARY tag",
                "4. Call create_standard_names with entries=[...] to add new entries (staged in-memory)",
                "5. Call list_standard_names with scope='unsaved' to review unsaved changes",
                "6. Use fetch_standard_names to inspect full details of entries",
                "7. Use edit_standard_name to modify/rename/delete existing entries if needed",
                "8. Call write_standard_names(dry_run=true) to validate before persisting",
                "9. Call write_standard_names() to persist all changes to disk",
                "Note: If write fails, changes are automatically rolled back - catalog state is restored clean",
            ],
            "catalog_state": {
                "description": "The catalog maintains an in-memory working state separate from saved YAML files on disk.",
                "saved": "Standard names persisted in YAML files (imas_standard_names/resources/standard_names/).",
                "unsaved": "Changes (new, modified, renamed, deleted) held in-memory via create/edit operations.",
                "workflow": "All create/edit operations stage changes in-memory. Use list_standard_names to diff saved vs unsaved. Use write_standard_names to persist changes to disk.",
                "error_recovery": "If write_standard_names fails validation, all changes are automatically rolled back. The catalog returns to the last committed state. You can then fix the issues and retry create_standard_names with corrected entries.",
            },
            "catalog_version": package_version,
        }
