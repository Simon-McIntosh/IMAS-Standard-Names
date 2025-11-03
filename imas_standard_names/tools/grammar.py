from collections import Counter
from importlib import resources

import yaml
from fastmcp import Context

import imas_standard_names.grammar.types as grammar_types
from imas_standard_names import __version__ as package_version
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.grammar.constants import (
    APPLICABILITY_EXCLUDE,
    APPLICABILITY_INCLUDE,
    APPLICABILITY_RATIONALE,
    EXCLUSIVE_SEGMENT_PAIRS,
    SEGMENT_ORDER,
    SEGMENT_RULES,
    SEGMENT_TEMPLATES,
)
from imas_standard_names.grammar.field_schemas import NAMING_GUIDANCE
from imas_standard_names.grammar.support import enum_values
from imas_standard_names.grammar_codegen.spec import IncludeLoader
from imas_standard_names.tools.base import Tool


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
            else:
                # For segments without templates (geometric_base, physical_base, subject)
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


def _build_template_mapping() -> dict[str, str]:
    """Build template mapping for all segments from SEGMENT_RULES.

    Returns template pattern for each segment. Segments without templates
    (template=None) return '{token}' to indicate the token is used as-is.
    """
    return {
        rule.identifier: rule.template if rule.template else "{token}"
        for rule in SEGMENT_RULES
    }


def _build_vocabulary_token_counts() -> dict[str, int]:
    """Build token counts for each segment vocabulary."""
    return {rule.identifier: len(rule.tokens) for rule in SEGMENT_RULES}


def _build_segment_usage_guidance() -> dict[str, str]:
    """Load abbreviated segment usage guidance from specification.

    Returns concise 1-2 sentence guidance for segments where the distinction
    is critical for correct composition (component vs coordinate, device vs object, etc.).
    """
    segment_descriptions = _get_segment_descriptions()

    # Extract first 1-2 sentences for critical segments
    guidance = {}
    for seg_id, full_desc in segment_descriptions.items():
        # Split on periods and take first sentence or two
        sentences = full_desc.split(".")
        if seg_id in [
            "component",
            "coordinate",
            "device",
            "object",
            "geometric_base",
            "physical_base",
        ]:
            # For critical segments, include more context (2 sentences)
            abbreviated = ". ".join(sentences[:2]).strip()
            if abbreviated and not abbreviated.endswith("."):
                abbreviated += "."
            guidance[seg_id] = abbreviated
        else:
            # For other segments, just use the description as-is
            guidance[seg_id] = full_desc.strip()

    return guidance


class NamingGrammarTool(Tool):
    """Tool providing IMAS Standard Names grammar rules and vocabulary.

    Use this tool to understand the naming grammar before composing names.
    Returns grammar structure, vocabulary tokens, naming rules, and composition examples.
    """

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "naming_grammar"

    @mcp_tool(
        description=(
            "Get IMAS Standard Names naming grammar - rules for composing valid names. Use this first before composing names. "
            "Call without section for comprehensive overview including templates, patterns, and critical distinctions. "
            "Available sections: 'segments' (detailed segment descriptions), 'vocabulary' (vocabulary overview), "
            "'rules' (naming rules and constraints), 'examples' (composition examples), 'statistics' (catalog stats), 'all' (complete output). "
            "For detailed vocabulary token lists, use get_vocabulary_tokens tool."
        )
    )
    async def get_naming_grammar(
        self, section: str | None = None, ctx: Context | None = None
    ):
        """Return naming grammar rules and vocabulary overview for IMAS Standard Names.

        This is the primary reference for understanding how to compose valid standard names.
        Includes grammar rules, templates, common patterns, and essential vocabulary context.
        """
        # Route to section-specific method if requested
        if section is None:
            return self._get_grammar_overview()
        elif section in ["segments", "vocabulary"]:
            return self._get_grammar_section_vocabulary(section)
        elif section in ["rules", "validation"]:
            return self._get_grammar_section_rules(section)
        elif section in ["composition", "examples"]:
            return self._get_grammar_section_examples(section)
        elif section == "statistics":
            return self._get_grammar_section_statistics()
        elif section != "all":
            return {
                "error": "Invalid section",
                "message": f"Unknown section: {section}",
                "available_sections": [
                    "segments",
                    "vocabulary",
                    "rules",
                    "validation",
                    "composition",
                    "examples",
                    "statistics",
                    "all",
                ],
            }

        # Full grammar for section='all' - build all data structures
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
                "tokens": enum_values(grammar_types.Component),
                "usage": "prefix",
                "description": "Spatial or field-aligned direction for physical vector quantities (magnetic_field, heat_flux, velocity, etc.). Use with fields/fluxes, not geometric positions.",
            }

        # Add coordinate vocabulary (shares tokens with component but different usage)
        if hasattr(grammar_types, "Component"):
            vocabulary["coordinate"] = {
                "segment_id": "coordinate",
                "template": SEGMENT_TEMPLATES.get("coordinate"),
                "tokens": enum_values(grammar_types.Component),
                "usage": "prefix",
                "description": "Coordinate axis for geometric/spatial vector decomposition (position, vertex, centroid, trajectory, displacement, offset). Use ONLY with geometric bases, NOT physical fields.",
            }

        # Add subject vocabulary if it exists
        if hasattr(grammar_types, "Subject"):
            vocabulary["subject"] = {
                "segment_id": "subject",
                "template": SEGMENT_TEMPLATES.get("subject"),
                "tokens": enum_values(grammar_types.Subject),
                "usage": "prefix",
                "description": _get_vocabulary_description("subject"),
            }

        # Add geometric_base vocabulary (CONTROLLED - required for geometric quantities)
        if hasattr(grammar_types, "GeometricBase"):
            vocabulary["geometric_base"] = {
                "segment_id": "geometric_base",
                "template": SEGMENT_TEMPLATES.get("geometric_base"),
                "tokens": enum_values(grammar_types.GeometricBase),
                "usage": "base",
                "description": (
                    "Controlled vocabulary for geometric/spatial base quantities describing "
                    "locations, shapes, orientations, and geometric properties. "
                    "REQUIRED: Must be qualified with object OR geometry segment. "
                    "Mutually exclusive with physical_base."
                ),
                "categories": {
                    "positions": {
                        "tokens": ["position"],
                        "description": "Location in space",
                        "requirement": "Must specify object: position_of_{object}",
                        "examples": [
                            "radial_position_of_flux_loop",
                            "vertical_position_of_magnetic_axis",
                            "toroidal_position_of_sensor",
                        ],
                    },
                    "vertices_centroids": {
                        "tokens": ["vertex", "centroid"],
                        "description": "Key points of geometric objects",
                        "requirement": "Must specify object: {base}_of_{object}",
                        "examples": [
                            "vertex_of_divertor_tile",
                            "centroid_of_plasma_cross_section",
                        ],
                    },
                    "boundaries_paths": {
                        "tokens": ["outline", "contour", "trajectory"],
                        "description": "Paths, boundaries, and motion traces",
                        "requirement": "Must specify object: {base}_of_{object}",
                        "examples": [
                            "outline_of_first_wall",
                            "contour_of_flux_surface",
                            "trajectory_of_neutral_beam",
                        ],
                    },
                    "displacements": {
                        "tokens": ["displacement", "offset"],
                        "description": "Relative positions and shifts",
                        "requirement": "Must specify object or reference",
                        "examples": [
                            "displacement_of_plasma_boundary",
                            "radial_offset_of_magnetic_axis",
                        ],
                    },
                    "dimensions": {
                        "tokens": ["extent"],
                        "description": "Size/span measurements",
                        "requirement": "Typically with component for direction",
                        "examples": [
                            "radial_extent_of_plasma",
                            "vertical_extent_of_antenna",
                        ],
                    },
                    "orientations": {
                        "tokens": ["surface_normal", "sensor_normal", "tangent_vector"],
                        "description": "Direction vectors for surfaces/sensors/paths",
                        "requirement": "MUST specify object",
                        "examples": [
                            "surface_normal_of_divertor_tile",
                            "sensor_normal_of_bolometer",
                            "tangent_vector_of_field_line",
                        ],
                    },
                },
            }

        # Add physical_base note (open vocabulary)
        vocabulary["physical_base"] = {
            "segment_id": "physical_base",
            "template": SEGMENT_TEMPLATES.get("physical_base"),
            "tokens": [],  # Open vocabulary - no controlled list
            "usage": "base",
            "description": (
                "Open vocabulary for physical quantity base names (temperature, density, "
                "pressure, energy, power, current, voltage, etc.). "
                "Not controlled - use standard physics terminology. "
                "Typically qualified with subject (electron, ion) rather than object. "
                "Mutually exclusive with geometric_base."
            ),
            "examples": [
                "electron_temperature",
                "ion_density",
                "magnetic_field",
                "toroidal_current",
                "plasma_energy",
                "ohmic_power",
            ],
            "guidance": {
                "subject_qualification": "Prefer subject (electron_temperature) over object qualification",
                "component_usage": "Use component segment for vector field directions (radial_component_of_magnetic_field)",
                "units": "Physical bases must have standardizable physical units",
            },
        }

        # Add object vocabulary if it exists
        if hasattr(grammar_types, "Object"):
            vocabulary["object"] = {
                "segment_id": "object",
                "template": SEGMENT_TEMPLATES.get("object"),
                "tokens": enum_values(grammar_types.Object),
                "usage": "suffix",
                "description": _get_vocabulary_description("object"),
            }

        # Add geometry and position vocabularies (share same tokens but different templates)
        if hasattr(grammar_types, "Position"):
            position_tokens = enum_values(grammar_types.Position)

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
                "tokens": enum_values(grammar_types.Process),
                "usage": "suffix",
                "description": _get_vocabulary_description("process"),
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
            "applicability": {
                "include": list(APPLICABILITY_INCLUDE),
                "exclude": list(APPLICABILITY_EXCLUDE),
                "rationale": APPLICABILITY_RATIONALE,
            },
            "grammar_structure": grammar_structure,
            "vocabulary": vocabulary,
            "validation_rules": validation_rules,
            "catalog_stats": {
                "total_standard_names": total,
                "standard_names_by_kind": standard_names_by_kind,
                "standard_names_by_status": standard_names_by_status,
                "standard_names_by_unit": standard_names_by_unit,
                "standard_names_by_tag": standard_names_by_tag,
            },
            "version": package_version,
        }

    def _get_grammar_overview(self) -> dict:
        """Return concise overview of grammar structure with critical semantic information."""
        template_mapping = _build_template_mapping()
        token_counts = _build_vocabulary_token_counts()
        segment_guidance = _build_segment_usage_guidance()

        return {
            "available_sections": [
                "segments",
                "vocabulary",
                "rules",
                "validation",
                "composition",
                "examples",
                "statistics",
                "all",
            ],
            "canonical_pattern": _build_canonical_pattern(),
            "segment_order": list(SEGMENT_ORDER),
            "templates": template_mapping,
            "exclusive_pairs": [
                {
                    "segments": list(pair),
                    "rule": f"{pair[0]} and {pair[1]} are mutually exclusive",
                }
                for pair in EXCLUSIVE_SEGMENT_PAIRS
            ],
            "segment_usage": {
                seg_id: {
                    "guidance": segment_guidance.get(seg_id, ""),
                    "template": template_mapping.get(seg_id),
                    "vocabulary_size": token_counts.get(seg_id, 0),
                }
                for seg_id in SEGMENT_ORDER
            },
            "base_requirements": {
                "geometric_base": {
                    "type": "Controlled vocabulary",
                    "qualification": "Must be qualified with object OR geometry segment",
                    "vector_prefix": "Use coordinate (not component) for vector components",
                    "categories": "position, vertex/centroid, outline/contour/trajectory, displacement/offset, extent, surface_normal/sensor_normal/tangent_vector",
                    "example": "radial_position_of_flux_loop",
                },
                "physical_base": {
                    "type": "Open vocabulary",
                    "guidance": "Use standard physics terminology (temperature, density, pressure, magnetic_field, etc.)",
                    "qualification": "Typically qualified with subject (electron_temperature) rather than object",
                    "vector_prefix": "Use component (not coordinate) for vector components",
                    "units": "Must have standardizable physical units",
                    "example": "radial_component_of_magnetic_field",
                },
                "choice": "Exactly one base (geometric_base OR physical_base) is required.",
            },
            "quick_start": {
                "1_choose_base": "Either physical_base (for physics quantities) OR geometric_base (for geometric/spatial quantities)",
                "2_add_modifiers": "Add optional segments: component/coordinate (vectors), subject (species), object/device (equipment), position/geometry (location), process (mechanism)",
                "3_check_exclusivity": "Critical: component with physical_base ONLY; coordinate with geometric_base ONLY; device for dynamic signals, object for static properties",
                "4_apply_templates": "Templates transform tokens (see 'templates' field): radial + component template -> radial_component_of",
                "5_compose": "Use compose_standard_name tool to validate composition",
            },
            "common_patterns": {
                "bare_quantity": "physical_base -> 'temperature' (simple unqualified quantity)",
                "vector_quantity": "physical_base -> 'magnetic_field' (vector without component decomposition)",
                "vector_component": "component + physical_base -> 'radial_component_of_magnetic_field'",
                "species_quantity": "subject + physical_base -> 'electron_temperature'",
                "species_vector": "component + subject + physical_base -> 'radial_component_of_electron_heat_flux'",
                "spatial_coordinate": "coordinate + geometric_base + object -> 'radial_position_of_flux_loop'",
                "device_signal": "device + physical_base -> 'flux_loop_voltage' (dynamic signal FROM device)",
                "object_property": "physical_base + object -> 'area_of_flux_loop' (static property OF object)",
                "field_at_location": "physical_base + position -> 'electron_temperature_at_magnetic_axis'",
                "property_of_geometry": "physical_base + geometry -> 'major_radius_of_plasma_boundary'",
                "with_process": "physical_base + process -> 'power_due_to_ohmic' (attributed to mechanism)",
            },
            "critical_distinctions": {
                "component_vs_coordinate": "component: vector components of PHYSICAL fields (magnetic_field, heat_flux); coordinate: spatial directions for GEOMETRIC quantities (position, vertex)",
                "device_vs_object": "device: dynamic signals FROM device (flux_loop_voltage); object: static properties OF object (area_of_flux_loop)",
                "geometry_vs_position": "geometry: intrinsic property OF location (radius_of_plasma_boundary); position: field evaluated AT location (temperature_at_magnetic_axis)",
            },
            "vocabulary_token_counts": token_counts,
            "common_naming_pitfalls": NAMING_GUIDANCE,
            "note": "For full segment descriptions, detailed examples, and complete token lists, use section='all'",
            "version": package_version,
        }

    def _get_grammar_section_vocabulary(self, section: str) -> dict:
        """Return vocabulary tokens for segments."""
        vocabulary = {}

        # Add all vocabularies dynamically
        if hasattr(grammar_types, "Component"):
            vocabulary["component"] = {
                "tokens": enum_values(grammar_types.Component),
                "template": SEGMENT_TEMPLATES.get("component"),
                "description": "Direction or component of a vector quantity",
            }

        if hasattr(grammar_types, "Subject"):
            vocabulary["subject"] = {
                "tokens": enum_values(grammar_types.Subject),
                "template": SEGMENT_TEMPLATES.get("subject"),
                "description": "Subject matter or physical entity being described",
            }

        if hasattr(grammar_types, "Object"):
            vocabulary["object"] = {
                "tokens": enum_values(grammar_types.Object),
                "template": SEGMENT_TEMPLATES.get("object"),
                "description": "Object or system that possesses the property",
            }

        if hasattr(grammar_types, "Process"):
            vocabulary["process"] = {
                "tokens": enum_values(grammar_types.Process),
                "template": SEGMENT_TEMPLATES.get("process"),
                "description": "Physical process or phenomenon",
            }

        if hasattr(grammar_types, "Position"):
            vocabulary["position"] = {
                "tokens": enum_values(grammar_types.Position),
                "template": SEGMENT_TEMPLATES.get("position"),
                "description": "Spatial location or region",
            }

        if hasattr(grammar_types, "GeometricBase"):
            vocabulary["geometric_base"] = {
                "tokens": enum_values(grammar_types.GeometricBase),
                "template": None,
                "description": "Geometric property or spatial characteristic",
            }

        # Physical base is open vocabulary
        vocabulary["physical_base"] = {
            "type": "open_vocabulary",
            "description": "Physics quantity name (open vocabulary, validated by community review)",
            "examples": [
                "temperature",
                "pressure",
                "density",
                "magnetic_field",
                "current",
            ],
            "validation": "Must follow snake_case pattern, use underscores for multi-word bases",
        }

        return {
            "section": section,
            "vocabulary": vocabulary,
            "usage": "Select tokens from controlled vocabularies (component, subject, etc.) or create physical_base following snake_case pattern",
        }

    def _get_grammar_section_rules(self, section: str) -> dict:
        """Return validation and composition rules."""
        return {
            "section": section,
            "validation_rules": {
                "base_pattern": "^[a-z][a-z0-9_]*$",
                "base_required": True,
                "exclusive_pairs": [
                    {
                        "segments": list(pair),
                        "rule": f"{pair[0]} and {pair[1]} cannot both be present",
                    }
                    for pair in EXCLUSIVE_SEGMENT_PAIRS
                ],
                "segment_order": list(SEGMENT_ORDER),
            },
            "composition_rules": {
                "template_application": "Segments use templates to transform tokens: component 'radial' -> 'radial_component'",
                "joining": "Segments joined with underscores, base last: '{segments}_{base}'",
                "optional_segments": [
                    rule.identifier for rule in SEGMENT_RULES if rule.optional
                ],
                "required_base": "Either physical_base or geometric_base must be present",
            },
            "critical_constraints": {
                "component_geometric_base": "component cannot be used with geometric_base (use coordinate instead)",
                "geometry_position": "geometry and position are mutually exclusive",
            },
        }

    def _get_grammar_section_examples(self, section: str) -> dict:
        """Return composition examples and patterns."""
        return {
            "section": section,
            "composition_examples": {
                "physics_quantity": {
                    "pattern": "physical_base",
                    "example": "temperature",
                    "description": "Simple physics quantity without modifiers",
                },
                "vector_component": {
                    "pattern": "component + physical_base",
                    "example": "radial_component_of_magnetic_field",
                    "description": "Component of a vector quantity",
                },
                "property_of_object": {
                    "pattern": "physical_base + object",
                    "example": "magnetic_flux_of_loop",
                    "description": "Property intrinsic to an object",
                },
                "field_at_location": {
                    "pattern": "physical_base + position",
                    "example": "electron_temperature_at_magnetic_axis",
                    "description": "Field evaluated at a spatial location",
                },
                "geometric_position": {
                    "pattern": "coordinate + geometric_base + object",
                    "example": "radial_position_of_flux_loop",
                    "description": "Spatial coordinate of an object",
                },
                "full_composition": {
                    "pattern": "component + subject + physical_base + geometry + process",
                    "example": "radial_component_of_electron_density_of_plasma_boundary_due_to_conduction",
                    "description": "Complete composition with all modifiers",
                },
            },
        }

    def _get_grammar_section_statistics(self) -> dict:
        """Return catalog statistics."""
        models = self.catalog.list()

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

        tag_counter = Counter(tag for m in models for tag in (m.tags or []))
        standard_names_by_tag = dict(sorted(tag_counter.items()))

        return {
            "section": "statistics",
            "total_standard_names": len(models),
            "standard_names_by_kind": standard_names_by_kind,
            "standard_names_by_status": standard_names_by_status,
            "standard_names_by_unit": standard_names_by_unit,
            "standard_names_by_tag": standard_names_by_tag,
            "version": package_version,
        }
