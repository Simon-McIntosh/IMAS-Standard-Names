"""Public grammar context API for external consumers.

Exposes comprehensive naming knowledge needed by LLM pipelines and
external tools such as imas-codex. The main entry point is
``get_grammar_context()``, which aggregates grammar mechanics, naming
conventions, and LLM orientation data into a single dictionary.
"""

import copy
import functools
import hashlib
import json
import os
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from imas_standard_names.grammar.constants import (
    APPLICABILITY_EXCLUDE,
    APPLICABILITY_INCLUDE,
    APPLICABILITY_RATIONALE,
    EXCLUSIVE_SEGMENT_PAIRS,
    SEGMENT_ORDER,
    SEGMENT_RULES,
    SEGMENT_TEMPLATES,
    SEGMENT_TOKEN_MAP,
)
from imas_standard_names.grammar.field_schemas import (
    DOCUMENTATION_GUIDANCE,
    FIELD_GUIDANCE,
    NAMING_GUIDANCE,
    TYPE_SPECIFIC_REQUIREMENTS,
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
        "component": (
            "Directional projection or direction-dependent quantity. "
            "radial is cylindrical R; "
            "flux_surface_normal is outward toward increasing flux label; "
            "perpendicular is magnetic-field-relative; local tangential "
            "directions are the e1/e2 tangents of the DD-defined object-local "
            "right-handed frame, with plasma-facing normal e3, positive-phi e1, "
            "and e2 = e3 x e1; e2 is not global vertical"
        ),
        "subject": "Particle species or plasma component (e.g., electron, ion, deuterium)",
        "object": "Physical object, diagnostic hardware, or equipment (e.g., flux_loop, bolometer)",
        "position": "Spatial location where field is evaluated (use with at_ template)",
        "geometry": "Intrinsic geometric property of the object (use with of_ template)",
        "path": "Path-like position a quantity varies along, e.g. a diagnostic chord (use with along_ template)",
        "process": "Physical process or mechanism (e.g., conduction, ohmic, radiation)",
        "zone": "Plasma-region / geometric sub-selector prefix (e.g., core, edge, inner, outer, upper, lower)",
        "channel": "Transport channel — WHAT is transported (heat, particle, energy, momentum)",
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
    """Build per-segment vocabulary sections with token lists and descriptions.

    Uses ``SEGMENT_TOKEN_MAP`` as the single source of truth for all segment
    tokens — this includes segments loaded from YAML vocabularies
    (physical_base, device, region, qualifier) as well as enum-backed segments.
    """
    sections: list[dict[str, Any]] = []

    # Iterate SEGMENT_ORDER first (preserves canonical display order),
    # then append any segments in TOKEN_MAP but not in ORDER (e.g. qualifier).
    seen: set[str] = set()
    ordered_segments = list(SEGMENT_ORDER)
    for seg_id in SEGMENT_TOKEN_MAP:
        if seg_id not in seen and seg_id not in SEGMENT_ORDER:
            ordered_segments.append(seg_id)
    for seg_id in ordered_segments:
        seen.add(seg_id)

    for seg_id in ordered_segments:
        tokens = sorted(SEGMENT_TOKEN_MAP.get(seg_id, ()))

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
            "mistake": "Using the retired long component form with physical_base",
            "correction": (
                "Use the short form <axis>_<physical_base>; "
                "the <axis>_component_of_<base> spelling does not parse"
            ),
            "example_wrong": "radial_component_of_magnetic_field",
            "example_right": "radial_magnetic_field",
        },
        {
            "mistake": "Including units in the name",
            "correction": "Use the unit field in the YAML entry (e.g. unit: eV)",
            "example_wrong": "temperature_in_eV",
            "example_right": "electron_temperature",
        },
        {
            "mistake": "Using camelCase or spaces",
            "correction": "Use snake_case for all names",
            "example_wrong": "electronTemperature",
            "example_right": "electron_temperature",
        },
        {
            "mistake": "Using the device prefix when authoring new instrument names",
            "correction": (
                "Attach the instrument as the of_<entity> postfix locus; "
                "the device-prefix form is retained for parse compatibility only"
            ),
            "example_wrong": "flux_loop_voltage",
            "example_right": "voltage_of_flux_loop",
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


def _build_quick_start_steps() -> dict[str, str]:
    """Ordered quick-start steps for composing names (single source).

    Consumed both by :func:`_build_quick_start` (the newline-joined string in
    the LLM context) and by the MCP grammar tool's overview payload, so the
    step text is authored exactly once.
    """
    return {
        "1_choose_base": (
            "Either physical_base (for physics quantities) OR geometric_base "
            "(for geometric/spatial quantities)"
        ),
        "2_add_modifiers": (
            "Add optional segments: component/coordinate (vectors), subject "
            "(species), object/device (equipment), position/geometry "
            "(location), process (mechanism)"
        ),
        "3_check_exclusivity": (
            "Critical: component with physical_base ONLY; coordinate with "
            "geometric_base ONLY; device for dynamic signals, object for "
            "static properties"
        ),
        "4_apply_templates": (
            "Templates transform tokens (see 'templates' field): radial + "
            "magnetic_field -> radial_magnetic_field"
        ),
        "5_compose": ("Use compose_standard_name tool to validate composition"),
    }


def _build_quick_start() -> str:
    """Build the quick-start guide for composing names."""
    steps = _build_quick_start_steps()
    return (
        f"1. Choose a base: {steps['1_choose_base']}.\n"
        f"2. Add optional modifiers: "
        f"{steps['2_add_modifiers'].split(': ', 1)[-1]}.\n"
        f"3. Check exclusivity: "
        f"{steps['3_check_exclusivity'].split(': ', 1)[-1]}.\n"
        "4. Apply templates: templates transform tokens "
        "(e.g., radial + magnetic_field -> radial_magnetic_field).\n"
        "5. Compose: use compose_standard_name tool to validate composition."
    )


def _build_common_patterns() -> list[dict[str, str]]:
    """Build common naming pattern examples.

    Each entry carries a ``description`` (a short mechanism gloss, empty when
    the formula speaks for itself). This is the single source consumed both by
    the LLM context and by the MCP grammar tool's overview payload.
    """
    return [
        {
            "pattern": "bare_quantity",
            "formula": "physical_base",
            "example": "safety_factor",
            "description": "simple unqualified quantity",
        },
        {
            "pattern": "vector_quantity",
            "formula": "physical_base",
            "example": "magnetic_field",
            "description": "vector without component decomposition",
        },
        {
            "pattern": "vector_component",
            "formula": "component + physical_base",
            "example": "radial_magnetic_field",
            "description": "",
        },
        {
            "pattern": "species_quantity",
            "formula": "subject + physical_base",
            "example": "electron_temperature",
            "description": "",
        },
        {
            "pattern": "species_vector",
            "formula": "component + subject + physical_base",
            "example": "radial_electron_heat_flux",
            "description": "",
        },
        {
            "pattern": "spatial_coordinate",
            "formula": "coordinate + geometric_base + object",
            "example": "radial_position_of_flux_loop",
            "description": "",
        },
        {
            "pattern": "device_signal",
            "formula": "physical_base + of_<entity> locus",
            "example": "voltage_of_flux_loop",
            "description": (
                "signal from instrument; the device-prefix form "
                "'flux_loop_voltage' is parse-compatible but not for authoring"
            ),
        },
        {
            "pattern": "object_property",
            "formula": "physical_base + object",
            "example": "area_of_flux_loop",
            "description": "static property OF object",
        },
        {
            "pattern": "field_at_location",
            "formula": "physical_base + position",
            "example": "electron_temperature_at_magnetic_axis",
            "description": "",
        },
        {
            "pattern": "property_of_geometry",
            "formula": "physical_base + geometry",
            "example": "elongation_of_plasma_boundary",
            "description": "",
        },
        {
            "pattern": "with_process",
            "formula": "physical_base + process",
            "example": "power_due_to_ohmic_heating",
            "description": "attributed to mechanism",
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
            "type": "Closed vocabulary",
            "guidance": (
                "Use ONLY tokens from the physical_bases registry. "
                "Unknown tokens are rejected in strict mode."
            ),
            "qualification": (
                "Typically qualified with subject (electron_temperature) "
                "rather than object"
            ),
            "vector_prefix": "Use component (not coordinate) for vector components",
            "units": "Must have standardizable physical units",
            "example": "radial_magnetic_field",
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
        "tensor": "Rank-2+ tensor quantities (metric tensor, stress tensor, conductivity tensor — full or component)",
        "complex": "Complex-valued quantities (real + imaginary parts, or magnitude + phase)",
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
# Cross-process payload cache
# ---------------------------------------------------------------------------

CACHE_ENABLE_ENV = "IMAS_STANDARD_NAMES_CONTEXT_CACHE"
CACHE_DIR_ENV = "IMAS_STANDARD_NAMES_CACHE_DIR"
_CACHE_SUBDIR = "grammar-context"
_CACHE_RETAIN = 8
_DISABLE_VALUES = frozenset({"0", "off", "no", "false"})

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_GRAMMAR_DIR = Path(__file__).resolve().parent


def _cache_enabled() -> bool:
    """Whether the on-disk payload cache may be read or written."""
    return os.environ.get(CACHE_ENABLE_ENV, "").strip().lower() not in _DISABLE_VALUES


def _cache_dir() -> Path:
    """Per-user cache directory holding serialised context payloads.

    Honours ``IMAS_STANDARD_NAMES_CACHE_DIR``, then ``platformdirs`` when it is
    importable, then ``XDG_CACHE_HOME``, then ``~/.cache``.
    """
    if override := os.environ.get(CACHE_DIR_ENV):
        return Path(override).expanduser() / _CACHE_SUBDIR
    try:
        from platformdirs import user_cache_dir

        base = Path(user_cache_dir("imas-standard-names"))
    except Exception:
        xdg = os.environ.get("XDG_CACHE_HOME")
        root = Path(xdg).expanduser() if xdg else Path.home() / ".cache"
        base = root / "imas-standard-names"
    return base / _CACHE_SUBDIR


def _distribution_version() -> str:
    """Installed distribution version, or an empty string when unavailable."""
    try:
        from importlib.metadata import version

        return version("imas-standard-names")
    except Exception:
        return ""


def _fingerprint_paths() -> list[Path]:
    """Every packaged file whose content shapes the payload.

    All Python modules of the package (the builders themselves, the
    code-generated segment constants, and the models the payload reflects) plus
    the grammar specification and every YAML vocabulary beside it.
    """
    paths = sorted(_PACKAGE_DIR.rglob("*.py"))
    paths += sorted(_GRAMMAR_DIR.rglob("*.yml"))
    paths += sorted(_GRAMMAR_DIR.rglob("*.yaml"))
    return paths


def _source_digest() -> str:
    """Digest the bytes of every packaged input plus the distribution version.

    Hashing content rather than tracking a version constant means an edited
    vocabulary token or an edited builder yields a different key on the next
    process, with nothing to remember to bump.
    """
    digest = hashlib.blake2b(digest_size=32)
    digest.update(_distribution_version().encode())
    for path in _fingerprint_paths():
        digest.update(path.relative_to(_PACKAGE_DIR).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _catalog_digest() -> str:
    """Digest the catalog entries that ``_build_vocabulary_usage_stats`` scans.

    Keyed on the resolved catalog location plus ``(relative path, size,
    mtime_ns)`` for each catalog YAML file — a size/mtime fingerprint rather
    than file content, because a production catalog holds thousands of entries
    and reading them all would cost as much as the scan the cache avoids. An
    edit that preserves both size and mtime_ns is therefore invisible; every
    ordinary write changes mtime_ns. Derived artifacts under dot-directories
    (the generated SQLite catalog, version control) are excluded so they cannot
    invalidate the key on their own.
    """
    digest = hashlib.blake2b(digest_size=32)
    try:
        from imas_standard_names.paths import get_default_catalog_path

        root = get_default_catalog_path()
    except Exception:
        root = None

    if root is None:
        digest.update(b"absent")
        return digest.hexdigest()

    root = Path(root)
    digest.update(str(root).encode())
    try:
        if root.is_file():
            entries = [root]
        else:
            entries = sorted(
                path
                for pattern in ("*.yml", "*.yaml")
                for path in root.rglob(pattern)
                if not any(
                    part.startswith(".") for part in path.relative_to(root).parts
                )
            )
        for path in entries:
            stat = path.stat()
            relative = path.name if path == root else path.relative_to(root).as_posix()
            digest.update(relative.encode())
            digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode())
    except OSError:
        # An unreadable catalog cannot be fingerprinted; a random key keeps the
        # process on the rebuild path instead of trusting an unrelated entry.
        digest.update(os.urandom(16))
    return digest.hexdigest()


def _cache_key() -> str:
    """Fingerprint of every input the payload is derived from."""
    combined = hashlib.blake2b(digest_size=16)
    combined.update(_source_digest().encode())
    combined.update(_catalog_digest().encode())
    return combined.hexdigest()


def _read_cache_entry(path: Path) -> dict[str, Any] | None:
    """Load a serialised payload, treating any defect as a cache miss."""
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_cache_entry(path: Path, payload: dict[str, Any]) -> None:
    """Serialise a payload so concurrent readers only ever see a whole file.

    The payload is written to a temporary file in the destination directory and
    moved into place with :func:`os.replace`, which is atomic within a
    filesystem. Any failure is silently dropped — the cache is an accelerator,
    never a dependency.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.stem}.",
            suffix=".tmp",
            delete=False,
        )
        try:
            with handle:
                json.dump(payload, handle)
            os.replace(handle.name, path)
        except BaseException:
            Path(handle.name).unlink(missing_ok=True)
            raise
    except OSError:
        return
    _prune_cache(path.parent)


def _prune_cache(directory: Path) -> None:
    """Keep the newest few entries so superseded fingerprints do not pile up."""
    try:
        entries = sorted(
            directory.glob("*.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True
        )
        for stale in entries[_CACHE_RETAIN:]:
            stale.unlink(missing_ok=True)
    except OSError:
        return


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_grammar_context() -> dict[str, Any]:
    """Return all naming knowledge needed by LLM pipelines.

    Aggregates grammar mechanics, naming conventions, and LLM orientation
    context into a single dictionary suitable for external consumers.
    Includes the 5-group IR context alongside the flat segment surface.

    The payload is derived from static vocabulary data plus a full catalog scan
    (usage statistics), which costs tens of seconds. It is memoised per process
    and persisted to a per-user cache directory keyed on a fingerprint of every
    input — package sources, grammar specification, YAML vocabularies, and the
    catalog files the scan reads — so a fresh process reloads it instead of
    rebuilding it, and any input change yields a different key.

    Set ``IMAS_STANDARD_NAMES_CONTEXT_CACHE=0`` to always rebuild, and
    ``IMAS_STANDARD_NAMES_CACHE_DIR`` to relocate the cache directory.

    Each call returns a deep copy, so callers may freely mutate their view.
    """
    return copy.deepcopy(_load_or_build_context())


@functools.lru_cache(maxsize=1)
def _load_or_build_context() -> dict[str, Any]:
    """Return the payload from the disk cache, building and storing it if absent."""
    if not _cache_enabled():
        return _build_full_context()

    path = _cache_dir() / f"{_cache_key()}.json"
    if (payload := _read_cache_entry(path)) is not None:
        return payload

    payload = _build_full_context()
    _write_cache_entry(path, payload)
    return payload


@functools.lru_cache(maxsize=1)
def _build_full_context() -> dict[str, Any]:
    from imas_standard_names.grammar.terms import standard_terms

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
        # Grammar 5-group IR context — the single ISN → codex contract point.
        "grammar": _build_grammar_context(),
        "standard_terms": [term.model_dump(mode="json") for term in standard_terms()],
    }


# ---------------------------------------------------------------------------
# Grammar 5-group IR context builder
# ---------------------------------------------------------------------------


def _build_grammar_context() -> dict[str, Any]:
    """Build a compact view of the grammar for external consumers.

    Returns a dict with keys: ``ir_groups`` (the 5 IR slots + mechanism),
    ``vocabularies`` (tokens per closed-vocab file), ``locus_relation_matrix``,
    ``canonical_templates``, and ``parse_api`` (callable names).

    Any loader failure yields an empty field but never raises — consumers
    must tolerate partially populated vocabularies.
    """

    from imas_standard_names.grammar import vocab_loaders
    from imas_standard_names.grammar.ir import (
        BINARY_SEPARATORS,
        LOCUS_RELATION_MATRIX,
    )

    def _safe(fn, default):  # type: ignore[no-untyped-def]
        try:
            return fn()
        except Exception:
            return default

    axes = _safe(vocab_loaders.load_coordinate_axes, None)
    loci = _safe(vocab_loaders.load_locus_registry, None)
    ops = _safe(vocab_loaders.load_operators, None)
    bases = _safe(vocab_loaders.load_physical_bases, None)
    carriers = _safe(vocab_loaders.load_geometry_carriers, None)
    qualifier_category_of = _safe(vocab_loaders.load_qualifier_categories, {})
    qualifier_categories: dict[str, list[str]] = {}
    for token, category in qualifier_category_of.items():
        qualifier_categories.setdefault(category, []).append(token)

    return {
        "ir_groups": [
            "operators",
            "projection",
            "qualifiers",
            "base",
            "locus",
            "mechanism",
        ],
        "vocabularies": {
            "coordinate_axes": sorted(axes.axes) if axes else [],
            "locus_registry": {
                token: {
                    "type": entry.type,
                    "allowed_relations": list(entry.allowed_relations),
                    "definition": entry.definition,
                    "abbreviations": list(entry.abbreviations),
                    "references": list(entry.references),
                }
                for token, entry in (loci.loci.items() if loci else ())
            },
            "operators": {
                token: {
                    "kind": entry.kind,
                    "precedence": entry.precedence,
                    "separator": entry.separator,
                    "indexed": entry.indexed,
                }
                for token, entry in (ops.operators.items() if ops else ())
            },
            "physical_bases": sorted(bases.bases) if bases else [],
            "geometry_carriers": sorted(carriers.carriers) if carriers else [],
            "qualifier_categories": qualifier_categories,
        },
        "locus_relation_matrix": {
            locus_type.value: sorted(r.value for r in relations)
            for locus_type, relations in LOCUS_RELATION_MATRIX.items()
        },
        "binary_separators": sorted(BINARY_SEPARATORS),
        "canonical_templates": {
            "unary_prefix": "<op>_of_<inner>",
            "unary_postfix": "<inner>_<op>",
            "binary": "<op>_of_<A>_<separator>_<B>",
            "projection_component": "<axis>_<base>",
            "projection_coordinate": "<axis>_<carrier>",
            "locus": "<core>_<relation>_<locus_token>",
            "mechanism": "<core>_due_to_<process>",
        },
        "parse_api": {
            "parse": "imas_standard_names:parse",
            "compose": "imas_standard_names:compose",
            "validate_round_trip": "imas_standard_names:validate_round_trip",
            "ir_model": "imas_standard_names:StandardNameIR",
            "operator_chain_order": "outermost_first",
        },
    }


__all__ = [
    "get_grammar_context",
    "_build_canonical_pattern",
    "_build_segment_order_constraint",
    "_get_segment_descriptions",
    "_get_vocabulary_description",
    "_build_template_application_rule",
]
