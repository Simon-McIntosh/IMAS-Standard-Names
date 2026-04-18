"""Public grammar context API for external consumers.

Exposes comprehensive naming knowledge needed by LLM pipelines and
external tools such as imas-codex. The main entry point is
``get_grammar_context()``, which aggregates grammar mechanics, naming
conventions, and LLM orientation data into a single dictionary.
"""

from importlib import resources
from typing import Any

import yaml

import imas_standard_names.grammar.model_types as grammar_types
from imas_standard_names.grammar.constants import (
    APPLICABILITY_EXCLUDE,
    APPLICABILITY_INCLUDE,
    APPLICABILITY_RATIONALE,
    EXCLUSIVE_SEGMENT_PAIRS,
    SEGMENT_ORDER,
    SEGMENT_RULES,
    SEGMENT_TEMPLATES,
)
from imas_standard_names.grammar.field_schemas import (
    DOCUMENTATION_GUIDANCE,
    FIELD_GUIDANCE,
    NAMING_GUIDANCE,
    TYPE_SPECIFIC_REQUIREMENTS,
)
from imas_standard_names.grammar.support import enum_values
from imas_standard_names.grammar.tag_types import (
    PRIMARY_TAG_DESCRIPTIONS,
    SECONDARY_TAG_DESCRIPTIONS,
)
from imas_standard_names.grammar_codegen.spec import IncludeLoader

# ---------------------------------------------------------------------------
# Private helpers (moved from tools/grammar.py)
# ---------------------------------------------------------------------------


def _build_canonical_pattern() -> str:
    """Build the canonical pattern string dynamically from SEGMENT_RULES.

    This ensures the pattern stays in sync with the grammar specification.
    """
    pattern_parts = []
    processed_exclusive: set[str] = set()

    for rule in SEGMENT_RULES:
        seg_id = rule.identifier

        if seg_id in processed_exclusive:
            continue

        exclusive_with = set(rule.exclusive_with)
        if exclusive_with:
            group_patterns = []

            if rule.template:
                template = rule.template.replace("{token}", f"<{seg_id}>")
                group_patterns.append(template)
            else:
                group_patterns.append(f"<{seg_id}>")

            for excl_rule in SEGMENT_RULES:
                excl_id = excl_rule.identifier
                if excl_id not in exclusive_with:
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
            if rule.template:
                template = rule.template.replace("{token}", f"<{seg_id}>")
                seg_pattern = f"[{template}]?" if rule.optional else template
            else:
                seg_pattern = f"[<{seg_id}>]?" if rule.optional else f"<{seg_id}>"

        pattern_parts.append(seg_pattern)

    return " ".join(pattern_parts)


def _build_segment_order_constraint() -> str:
    """Build the segment order constraint dynamically from SEGMENT_RULES."""
    parts = []
    processed_exclusive: set[str] = set()

    for rule in SEGMENT_RULES:
        seg_id = rule.identifier

        if seg_id in processed_exclusive:
            continue

        exclusive_with = set(rule.exclusive_with)
        if exclusive_with:
            ordered_ids = [seg_id] + [
                r.identifier for r in SEGMENT_RULES if r.identifier in exclusive_with
            ]
            group_label = "|".join(ordered_ids)
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

    descriptions: dict[str, str] = {}
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


# ---------------------------------------------------------------------------
# Vocabulary sections builder
# ---------------------------------------------------------------------------


def _build_vocabulary_sections() -> list[dict[str, Any]]:
    """Build per-segment vocabulary sections with token lists and descriptions."""
    sections: list[dict[str, Any]] = []

    segment_enum_map: dict[str, str] = {
        "component": "Component",
        "coordinate": "Component",
        "subject": "Subject",
        "object": "Object",
        "position": "Position",
        "geometry": "Position",
        "process": "Process",
        "geometric_base": "GeometricBase",
    }

    for seg_id in SEGMENT_ORDER:
        enum_name = segment_enum_map.get(seg_id)
        if enum_name and hasattr(grammar_types, enum_name):
            tokens = enum_values(getattr(grammar_types, enum_name))
        else:
            tokens = []

        section: dict[str, Any] = {
            "segment": seg_id,
            "template": SEGMENT_TEMPLATES.get(seg_id),
            "tokens": tokens,
            "description": _get_vocabulary_description(seg_id),
        }
        sections.append(section)

    return sections


# ---------------------------------------------------------------------------
# Anti-patterns
# ---------------------------------------------------------------------------


def _build_anti_patterns() -> list[dict[str, str]]:
    """Derive common naming anti-patterns from validation knowledge."""
    return [
        {
            "mistake": "Using component with geometric_base",
            "correction": "Use coordinate with geometric_base instead",
            "example_wrong": "radial_component_of_position",
            "example_right": "radial_position_of_flux_loop",
        },
        {
            "mistake": "Using coordinate with physical_base",
            "correction": "Use component with physical_base instead",
            "example_wrong": "radial_magnetic_field",
            "example_right": "radial_component_of_magnetic_field",
        },
        {
            "mistake": "Including units in the name",
            "correction": "Use the unit field in the YAML entry",
            "example_wrong": "temperature_in_eV",
            "example_right": "electron_temperature (unit: eV)",
        },
        {
            "mistake": "Using camelCase or spaces",
            "correction": "Use snake_case for all names",
            "example_wrong": "electronTemperature",
            "example_right": "electron_temperature",
        },
        {
            "mistake": "Mixing device and object segments",
            "correction": "Use device for dynamic signals, object for static properties",
            "example_wrong": "area_of_flux_loop (with device segment)",
            "example_right": "flux_loop_voltage (device) vs area_of_flux_loop (object)",
        },
        {
            "mistake": "Mixing geometry and position segments",
            "correction": "Use geometry for intrinsic properties, position for field evaluation",
            "example_wrong": "temperature_of_magnetic_axis",
            "example_right": "electron_temperature_at_magnetic_axis",
        },
    ]


# ---------------------------------------------------------------------------
# Quick-start and common-patterns from grammar help
# ---------------------------------------------------------------------------


def _build_quick_start() -> str:
    """Build the quick-start guide for composing names."""
    return (
        "1. Choose a base: physical_base (for physics quantities) "
        "or geometric_base (for geometric/spatial quantities).\n"
        "2. Add optional modifiers: component/coordinate (vectors), "
        "subject (species), object/device (equipment), "
        "position/geometry (location), process (mechanism).\n"
        "3. Check exclusivity: component with physical_base only; "
        "coordinate with geometric_base only; "
        "device for dynamic signals, object for static properties.\n"
        "4. Apply templates: templates transform tokens "
        "(e.g., radial + component template -> radial_component_of).\n"
        "5. Compose: use compose_standard_name tool to validate composition."
    )


def _build_common_patterns() -> list[dict[str, str]]:
    """Build common naming pattern examples."""
    return [
        {
            "pattern": "bare_quantity",
            "formula": "physical_base",
            "example": "temperature",
        },
        {
            "pattern": "vector_quantity",
            "formula": "physical_base",
            "example": "magnetic_field",
        },
        {
            "pattern": "vector_component",
            "formula": "component + physical_base",
            "example": "radial_component_of_magnetic_field",
        },
        {
            "pattern": "species_quantity",
            "formula": "subject + physical_base",
            "example": "electron_temperature",
        },
        {
            "pattern": "species_vector",
            "formula": "component + subject + physical_base",
            "example": "radial_component_of_electron_heat_flux",
        },
        {
            "pattern": "spatial_coordinate",
            "formula": "coordinate + geometric_base + object",
            "example": "radial_position_of_flux_loop",
        },
        {
            "pattern": "device_signal",
            "formula": "device + physical_base",
            "example": "flux_loop_voltage",
        },
        {
            "pattern": "object_property",
            "formula": "physical_base + object",
            "example": "area_of_flux_loop",
        },
        {
            "pattern": "field_at_location",
            "formula": "physical_base + position",
            "example": "electron_temperature_at_magnetic_axis",
        },
        {
            "pattern": "property_of_geometry",
            "formula": "physical_base + geometry",
            "example": "major_radius_of_plasma_boundary",
        },
        {
            "pattern": "with_process",
            "formula": "physical_base + process",
            "example": "power_due_to_ohmic",
        },
    ]


def _build_critical_distinctions() -> list[dict[str, str]]:
    """Build the critical distinctions for name composition."""
    return [
        {
            "pair": "component vs coordinate",
            "rule": (
                "component: vector components of physical fields "
                "(magnetic_field, heat_flux); "
                "coordinate: spatial directions for geometric quantities "
                "(position, vertex)"
            ),
        },
        {
            "pair": "device vs object",
            "rule": (
                "device: dynamic signals from device (flux_loop_voltage); "
                "object: static properties of object (area_of_flux_loop)"
            ),
        },
        {
            "pair": "geometry vs position",
            "rule": (
                "geometry: intrinsic property of location "
                "(radius_of_plasma_boundary); "
                "position: field evaluated at location "
                "(temperature_at_magnetic_axis)"
            ),
        },
    ]


# ---------------------------------------------------------------------------
# Base requirements
# ---------------------------------------------------------------------------


def _build_base_requirements() -> dict[str, Any]:
    """Build base requirements for geometric and physical bases."""
    return {
        "geometric_base": {
            "type": "Controlled vocabulary",
            "qualification": "Must be qualified with object or geometry segment",
            "vector_prefix": "Use coordinate (not component) for vector components",
            "categories": (
                "position, vertex/centroid, outline/contour/trajectory, "
                "displacement/offset, extent, "
                "surface_normal/sensor_normal/tangent_vector"
            ),
            "example": "radial_position_of_flux_loop",
        },
        "physical_base": {
            "type": "Open vocabulary",
            "guidance": (
                "Use standard physics terminology "
                "(temperature, density, pressure, magnetic_field, etc.)"
            ),
            "qualification": (
                "Typically qualified with subject (electron_temperature) "
                "rather than object"
            ),
            "vector_prefix": "Use component (not coordinate) for vector components",
            "units": "Must have standardizable physical units",
            "example": "radial_component_of_magnetic_field",
        },
        "choice": "Exactly one base (geometric_base or physical_base) is required.",
    }


# ---------------------------------------------------------------------------
# Kind definitions
# ---------------------------------------------------------------------------


def _build_kind_definitions() -> dict[str, str]:
    """Derive kind definitions from the Kind enum in models.py."""
    # Avoid importing models at module level to prevent circular imports
    from imas_standard_names.models import Kind

    return {member.value: member.value for member in Kind} | {
        "scalar": "Physical quantities with single value at each point",
        "vector": "Vector field quantities with directional components",
        "metadata": "Definitional entries (boundaries, regions, concepts) — no unit or provenance required",
    }


# ---------------------------------------------------------------------------
# Vocabulary usage statistics
# ---------------------------------------------------------------------------


def _build_vocabulary_usage_stats() -> dict[str, Any]:
    """Count per-segment token frequency across published standard names.

    Gracefully returns an empty dict when no catalog is available.
    """
    try:
        from imas_standard_names.grammar.model import parse_standard_name
        from imas_standard_names.repository import StandardNameCatalog

        catalog = StandardNameCatalog()
        entries = catalog.list()
    except Exception:
        return {}

    if not entries:
        return {}

    segment_counts: dict[str, dict[str, int]] = {seg: {} for seg in SEGMENT_ORDER}

    for entry in entries:
        try:
            parsed = parse_standard_name(entry.name)
        except Exception:
            continue

        for seg_id in SEGMENT_ORDER:
            value = getattr(parsed, seg_id, None)
            if value is None:
                continue
            token = value.value if hasattr(value, "value") else str(value)
            segment_counts[seg_id][token] = segment_counts[seg_id].get(token, 0) + 1

    # Aggregate top-10 across all segments
    all_tokens: list[tuple[str, str, int]] = []
    for seg, tokens in segment_counts.items():
        for tok, count in tokens.items():
            all_tokens.append((seg, tok, count))
    all_tokens.sort(key=lambda x: x[2], reverse=True)

    # Unused tokens (controlled vocabulary tokens with zero occurrences)
    unused: list[dict[str, str]] = []
    for seg_id in SEGMENT_ORDER:
        rule = next((r for r in SEGMENT_RULES if r.identifier == seg_id), None)
        if rule is None:
            continue
        for tok in rule.tokens:
            if tok not in segment_counts.get(seg_id, {}):
                unused.append({"segment": seg_id, "token": tok})

    return {
        "per_segment": segment_counts,
        "most_common": [
            {"segment": s, "token": t, "count": c} for s, t, c in all_tokens[:10]
        ],
        "unused": unused,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_grammar_context() -> dict[str, Any]:
    """Return all naming knowledge needed by LLM pipelines.

    Aggregates grammar mechanics, naming conventions, and LLM orientation
    context into a single dictionary suitable for external consumers.
    """
    return {
        # Grammar mechanics
        "canonical_pattern": _build_canonical_pattern(),
        "segment_order": _build_segment_order_constraint(),
        "template_rules": _build_template_application_rule(),
        "exclusive_pairs": [list(pair) for pair in EXCLUSIVE_SEGMENT_PAIRS],
        "vocabulary_sections": _build_vocabulary_sections(),
        "segment_descriptions": _get_segment_descriptions(),
        # Naming conventions
        "naming_guidance": NAMING_GUIDANCE,
        "documentation_guidance": DOCUMENTATION_GUIDANCE,
        "kind_definitions": _build_kind_definitions(),
        "anti_patterns": _build_anti_patterns(),
        "tag_descriptions": {
            "primary": PRIMARY_TAG_DESCRIPTIONS,
            "secondary": SECONDARY_TAG_DESCRIPTIONS,
        },
        "applicability": {
            "include": list(APPLICABILITY_INCLUDE),
            "exclude": list(APPLICABILITY_EXCLUDE),
            "rationale": APPLICABILITY_RATIONALE,
        },
        "field_guidance": FIELD_GUIDANCE,
        "type_specific_requirements": TYPE_SPECIFIC_REQUIREMENTS,
        # LLM orientation context
        "quick_start": _build_quick_start(),
        "common_patterns": _build_common_patterns(),
        "critical_distinctions": _build_critical_distinctions(),
        "base_requirements": _build_base_requirements(),
        # Vocabulary usage statistics
        "vocabulary_usage_stats": _build_vocabulary_usage_stats(),
    }


__all__ = [
    "get_grammar_context",
    "_build_canonical_pattern",
    "_build_segment_order_constraint",
    "_get_segment_descriptions",
    "_get_vocabulary_description",
    "_build_template_application_rule",
]
