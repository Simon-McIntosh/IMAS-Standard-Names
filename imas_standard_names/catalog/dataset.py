"""SPA dataset builder for the IMAS Standard Names catalog.

Converts a directory of per-domain YAML files (the published catalog
format) into a single JSON dataset consumed by the redesigned SPA. The
SPA loads:

* ``CATALOG_VERSION`` — human-readable catalog identifier
* ``CATEGORIES`` — list of ``{id, label, count}`` per physics_domain
* ``GRAMMAR_VOCAB`` — token lists per UI vocabulary section
* ``NAMES`` — flat array of records with the grammar-derived ``parse``
  decomposition pre-computed by the ISN Python parser (no JS
  heuristic).

The output is consumed by the SPA's read-only renderer. Each NAMES
record carries:

* identity: ``name``, ``category``, ``group``, ``parent``
* algebraic ``algebra`` (``scalar | vector | tensor | complex | metadata``)
  declared on the catalog entry
* physical metadata: ``unit``, ``tags``, ``axis``, ``locus``
* prose: ``short`` (description), ``long`` (documentation minus the
  ``Sign convention:`` paragraph), ``sign`` (the extracted paragraph)
* navigation: ``seeAlso`` (links normalised, ``name:`` prefix stripped),
  ``arguments`` (just the argument names), ``sources``
  (``{path, status}``), ``superseded_by`` (name of replacement or
  ``null``), ``deprecates`` (name being deprecated or ``null``)
* ``parse`` — a list of role/text/note segments (operators, qualifiers,
  axis, base, locus, process) for the UI to render as chips.

Status filtering
----------------
``build_site_dataset`` emits every entry whose normalised status is one
of the four canonical values: ``active``, ``draft``, ``deprecated``,
``superseded``.

Legacy status values are normalised before filtering:

* ``"drafted"``   → ``"draft"``
* ``"accepted"``  → ``"active"``
* ``"published"`` → ``"active"``

Unknown values are logged as warnings and the entry is dropped.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from imas_standard_names.grammar import Subject
from imas_standard_names.grammar.context import get_grammar_context
from imas_standard_names.grammar.parser import (
    ParseError,
    compose,
    load_default_vocabularies,
    parse,
)
from imas_standard_names.models import StandardNameCatalogManifest

_log = logging.getLogger(__name__)

__all__ = [
    "build_site_dataset",
    "write_site_dataset",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# Prefix operator tokens classified as "reductions" — used by the grammar
# vocab builder below (``_build_grammar_vocab``) to populate the
# ``"reduction"`` chip rail in the SPA.  NOT used for display_kind
# (which has been removed; only ``algebra`` is emitted on each record).
_REDUCTION_PREFIX_OPS: frozenset[str] = frozenset(
    {
        "maximum",
        "minimum",
        "maximum_over_flux_surface",
        "minimum_over_flux_surface",
        "volume_integrated",
        "surface_integrated",
        "line_integrated",
        "accumulated",
        "cumulative",
        "cumulative_inside_flux_surface",
        "time_average",
        "root_mean_square",
    }
)


_SUBJECT_TOKENS: frozenset[str] = frozenset(member.value for member in Subject)


# Coordinate-axis ordering for sort_axis_index emission.
# A vector or tensor component projected onto one of these axes sorts
# by this index within the component tier (tier 1). Names with no axis
# get index 99 so they sort after axis-bearing siblings (rare; only
# matters for tier 1).
_AXIS_ORDER: dict[str, int] = {
    "radial": 0,
    "toroidal": 1,
    "vertical": 2,
    "poloidal": 3,
    "parallel": 4,
    "perpendicular": 5,
}

# Operator tokens that signal a domain-wide aggregation (tier 3). The
# parser surfaces these as ``qualifier_tokens``; we recompute the
# "reduction qualifier" flag inline since :class:`_GrammarFacets` no
# longer caches it (was used by the retired display_kind heuristic).
_AGGREGATION_PREFIXES: frozenset[str] = frozenset(
    {
        "total",
        "minimum",
        "maximum",
        "effective",
    }
)


def _extract_subject(qualifier_tokens: tuple[str, ...]) -> str | None:
    """Return the first qualifier token matching the Subject enum, if any.

    Drives the SPA's subject filter so users can slice by species
    (``electron``, ``ion``, ``deuterium``, …) without resorting to
    free-text search.
    """
    for token in qualifier_tokens:
        if token in _SUBJECT_TOKENS:
            return token
    return None


# Match the ``Sign convention: Positive ...`` paragraph. We accept both
# real newline separators (``\n\n``) and literal backslash-n escapes
# (``\\n\\n``) — a handful of catalog entries were YAML-encoded with
# single quotes that left the escapes uninterpreted. The sentence runs
# until the next paragraph break (real ``\n\n`` or literal ``\\n\\n``)
# or the end of the documentation string.
_SIGN_CONVENTION_RE = re.compile(
    r"(?:^|\n\n|\\n\\n)"
    r"Sign convention:\s*Positive"
    r"(?:(?!\n\n|\\n\\n).)*"
    r"(?=$|\n\n|\\n\\n)",
    re.DOTALL,
)


_NAME_LINK_RE = re.compile(r"^name:([a-z0-9_]+)$")


# ---------------------------------------------------------------------------
# Helpers — humanisation
# ---------------------------------------------------------------------------


# Selected abbreviations matching the SPA prototype's compact labels.
_LABEL_ABBREVIATIONS: dict[str, str] = {
    "measurement": "Meas.",
    "electromagnetic": "EM",
}


def _humanise_domain(slug: str) -> str:
    """Convert a physics_domain slug into a human-readable label.

    Most slugs ``snake_case`` → ``Title Case`` ("auxiliary_heating" →
    "Auxiliary Heating"). Selected long words are abbreviated to match
    the SPA prototype's compact sidebar labels.
    """
    if not slug:
        return ""
    words: list[str] = []
    for token in slug.split("_"):
        if not token:
            continue
        abbreviated = _LABEL_ABBREVIATIONS.get(token)
        if abbreviated is not None:
            words.append(abbreviated)
        else:
            words.append(token.capitalize())
    return " ".join(words)


def _humanise(token: str) -> str:
    """Convert a snake_case token to space-separated lowercase words.

    Used for group titles ("magnetic_field" → "magnetic field") so the
    SPA can cluster sibling names without further string handling.
    """
    return token.replace("_", " ") if token else ""


# ---------------------------------------------------------------------------
# Helpers — sign convention / documentation
# ---------------------------------------------------------------------------


def _extract_sign(documentation: str) -> tuple[str, str | None]:
    """Strip the Sign convention paragraph and return (long, sign).

    The validator enforces ``Sign convention:`` as a standalone
    paragraph; we capture the entire sentence (which begins with
    ``Positive``) and remove it (and the leading blank line) from the
    main documentation text.
    """
    if not documentation:
        return documentation or "", None

    match = _SIGN_CONVENTION_RE.search(documentation)
    if match is None:
        return documentation, None

    # Strip leading separators (real ``\n\n`` or literal ``\\n\\n``) so
    # the captured sentence starts cleanly with "Sign convention:".
    sign_text = match.group(0)
    sign_text = re.sub(r"^(?:\\n\\n|\n\n)", "", sign_text).strip()
    # Strip the "Sign convention: " prefix so the SPA gets just the
    # human-readable rule. Keep the trailing period.
    sign_value = re.sub(
        r"^Sign convention:\s+", "", sign_text, count=1, flags=re.IGNORECASE
    ).strip()

    # Remove the matched span (including its leading separator) from
    # the documentation, then collapse any resulting triple newline.
    start, end = match.span()
    stripped = documentation[:start] + documentation[end:]
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()
    return stripped, sign_value or None


# ---------------------------------------------------------------------------
# Helpers — links / sources / arguments
# ---------------------------------------------------------------------------


def _normalise_see_also(links: list[str] | None) -> list[str]:
    """Filter ``links`` to internal ``name:foo`` refs (returned without prefix)."""
    if not links:
        return []
    result: list[str] = []
    for link in links:
        if not isinstance(link, str):
            continue
        match = _NAME_LINK_RE.match(link.strip())
        if match:
            result.append(match.group(1))
    return result


def _normalise_sources(sources: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Reduce source records to ``{path, status}`` pairs.

    ``path`` falls back to ``id`` (minus its ``dd:`` prefix) when the
    entry has no explicit ``dd_path``.
    """
    if not sources:
        return []
    normalised: list[dict[str, str]] = []
    for raw in sources:
        if not isinstance(raw, dict):
            continue
        path = raw.get("dd_path") or ""
        if not path:
            ident = raw.get("id") or ""
            if isinstance(ident, str) and ident.startswith("dd:"):
                path = ident[len("dd:") :]
        if not path:
            continue
        status = raw.get("status") or ""
        normalised.append({"path": str(path), "status": str(status)})
    return normalised


def _normalise_arguments(arguments: list[dict[str, Any]] | None) -> list[str]:
    """Flatten ``ArgumentRef`` entries to their ``name`` strings."""
    if not arguments:
        return []
    flat: list[str] = []
    for arg in arguments:
        if isinstance(arg, dict):
            ref = arg.get("name")
            if isinstance(ref, str) and ref:
                flat.append(ref)
        elif isinstance(arg, str):
            flat.append(arg)
    return flat


# ---------------------------------------------------------------------------
# Helpers — grammar IR
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _GrammarFacets:
    """Facets derived from the grammar IR for a single name.

    These drive ``parent``, ``axis``, ``locus``, grammar-derived
    ``tags``, and ``parse`` segments. Holding them in a single dataclass
    keeps the helper logic testable and clear.
    """

    parsed: bool
    parse_segments: list[dict[str, str]]
    base_token: str | None
    axis: str | None
    locus_token: str | None
    has_projection: bool
    has_locus: bool
    qualifier_tokens: tuple[str, ...]
    operator_tokens: tuple[str, ...]
    has_mechanism: bool


def _derive_grammar_facets(name: str) -> _GrammarFacets:
    """Parse ``name`` and extract everything the SPA record needs.

    Falls back to an "unparseable" record so the dataset never crashes
    on a malformed entry. The single ``parse`` segment in that case
    lets the SPA still render a (visually distinct) chip.
    """
    try:
        ir = parse(name).ir
    except ParseError:
        return _GrammarFacets(
            parsed=False,
            parse_segments=[
                {
                    "role": "unparseable",
                    "text": name,
                    "note": "Parser could not decompose",
                }
            ],
            base_token=None,
            axis=None,
            locus_token=None,
            has_projection=False,
            has_locus=False,
            qualifier_tokens=(),
            operator_tokens=(),
            has_mechanism=False,
        )

    segments: list[dict[str, str]] = []

    # Prefix operators (outermost first). The IR stores operators in
    # outer-to-inner order, which is the order we want to render.
    operator_tokens: list[str] = []
    for op in ir.operators:
        operator_tokens.append(op.op)
        if op.kind.value == "unary_prefix":
            segments.append(
                {
                    "role": "operator",
                    "text": op.op,
                    "note": "Prefix operator",
                }
            )
        elif op.kind.value == "binary":
            segments.append(
                {
                    "role": "operator",
                    "text": op.op,
                    "note": "Binary operator",
                }
            )
        else:
            # postfix — keep in the operators bucket but render later
            # (after the base) so its position in the chip strip reflects
            # the canonical written form.
            pass

    # Axis projection (before qualifiers in canonical render).
    axis: str | None = None
    if ir.projection is not None:
        axis = ir.projection.axis
        shape = ir.projection.shape.value
        segments.append(
            {
                "role": "axis",
                "text": axis,
                "note": f"Axis {shape}",
            }
        )

    # Qualifiers (insertion order matches parse order).
    qualifier_tokens: list[str] = []
    for qualifier in ir.qualifiers:
        token = qualifier.token
        qualifier_tokens.append(token)
        segments.append(
            {
                "role": "qualifier",
                "text": token,
                "note": "Qualifier",
            }
        )

    # Base (always present).
    base_token = ir.base.token
    segments.append(
        {
            "role": "base",
            "text": base_token,
            "note": ir.base.kind.value,
        }
    )

    # Postfix operators render after the base in canonical form.
    for op in ir.operators:
        if op.kind.value == "unary_postfix":
            segments.append(
                {
                    "role": "operator",
                    "text": op.op,
                    "note": "Postfix operator",
                }
            )

    # Locus (trailing position).
    locus_token: str | None = None
    if ir.locus is not None:
        locus_token = ir.locus.token
        relation = ir.locus.relation.value
        segments.append(
            {
                "role": "locus",
                "text": f"{relation}_{ir.locus.token}",
                "note": ir.locus.type.value,
            }
        )

    # Mechanism (always last when present).
    has_mechanism = ir.mechanism is not None
    if has_mechanism:
        segments.append(
            {
                "role": "process",
                "text": f"due_to_{ir.mechanism.token}",
                "note": "Mechanism",
            }
        )

    return _GrammarFacets(
        parsed=True,
        parse_segments=segments,
        base_token=base_token,
        axis=axis,
        locus_token=locus_token,
        has_projection=ir.projection is not None,
        has_locus=ir.locus is not None,
        qualifier_tokens=tuple(qualifier_tokens),
        operator_tokens=tuple(operator_tokens),
        has_mechanism=has_mechanism,
    )


def _sort_tier(
    name: str,
    algebra: str,
    parent: str | None,
    facets: _GrammarFacets,
) -> int:
    """Compute the canonical sort tier for a name (0–7).

    Drives result-list ordering inside a cluster group, so the family
    reads top-to-bottom as base → components → magnitude → aggregation
    → operator-derived → locus-evaluated → metadata → variant.

    See Design Review §8 (catalog redesign) for the rule table. The
    classifier derives from grammar IR fields where available; tiers 2
    (magnitude / norm) and 4 (gradient / shear / etc.) use the
    parser's ``operator_tokens`` as the primary signal, with substring
    tests on the name string as a defensive fallback for unparseable
    names.
    """
    if algebra == "metadata":
        return 6
    if parent is None and algebra in {"vector", "tensor", "complex"}:
        return 0
    if facets.has_projection and algebra in {"vector", "tensor", "complex"}:
        return 1
    # Tier 2 — magnitude / norm. Driven by the parser's classified
    # postfix operator tokens, not by name-string regex.
    if any(op in {"magnitude", "norm"} for op in facets.operator_tokens):
        return 2
    # Regex fallback for unparseable names.
    if "_magnitude_" in f"_{name}_" or "_norm_" in f"_{name}_":
        return 2
    # Tier 3 — aggregation. Either a known reduction prefix (from the
    # ``_REDUCTION_PREFIX_OPS`` set already used by the vocab builder)
    # appears as a qualifier, or the name carries one of the
    # subject-style aggregation prefixes (total/minimum/maximum/…).
    if any(q in _REDUCTION_PREFIX_OPS for q in facets.qualifier_tokens):
        return 3
    if any(name.startswith(p + "_") for p in _AGGREGATION_PREFIXES):
        return 3
    # Tier 4 — operator-style derived. Primary: parser-classified
    # operator tokens. Fallback: substring tests for unparseable names.
    if any(
        op in {"gradient", "shear", "divergence", "curl", "density"}
        for op in facets.operator_tokens
    ):
        return 4
    for token in ("_gradient", "_shear", "_divergence", "_curl", "_density"):
        if token in f"_{name}_":
            return 4
    # Tier 5 — point evaluation at a locus.
    if facets.has_locus:
        return 5
    # Tier 7 — variant / unclassified scalars (base scalars, etc.).
    return 7


def _sort_axis_index(facets: _GrammarFacets) -> int:
    """Return the axis index (0–5) for a projection name, 99 otherwise."""
    if facets.axis is None:
        return 99
    return _AXIS_ORDER.get(facets.axis, 99)


# ---------------------------------------------------------------------------
# Helpers — parent / group
# ---------------------------------------------------------------------------


def _parent_token(
    name: str, facets: _GrammarFacets, entry: dict[str, Any] | None = None
) -> str | None:
    """Return the structural parent name (one layer peeled), if any.

    Resolution order — preferring the canonical pipeline-derived parent
    over heuristic local reconstruction:

    1. **``arguments[0].name``** from the YAML entry, when present and
       not a self-loop. The catalog exporter emits ``arguments`` from
       the graph's outgoing ``COMPONENT_OF`` edges (one per name, for
       unary peels; per-role for binary), which is the canonical
       structural-parent signal. Using it here means imas-codex's
       single source of truth — the derivation module — governs what
       the SPA shows as parent.

    2. **One-layer IR peel** (operator → projection → qualifier →
       locus) when no ``arguments`` field is provided (standalone
       catalog use, or pre-pipeline entries). This mirrors the
       imas-codex derivation so the SPA stays self-consistent.

    3. **``None``** for true leaves and unparseable names.

    Historical note: the rc8 implementation shortcut to
    ``facets.base_token`` here, jumping past every structural layer
    in one go. That made `upper_elongation_of_plasma_boundary`
    report `elongation` as parent — collapsing two distinct boundary
    elongation variants into a flat-tree with unrelated flux-surface
    elongation. The new resolution peels exactly one layer; recursion
    is implicit because each parent recomputes its own one-layer peel.
    """
    # --- (1) Canonical pipeline-derived parent from YAML arguments ---
    if entry is not None:
        canonical = _arguments_parent(name, entry)
        if canonical is not None:
            return canonical

    # --- (2) Local IR peel — matches imas-codex/derivation.py ordering ---
    local = _local_ir_peel(name)
    if local is not None:
        return local

    # --- (3) Legacy fallback (preserved for unparseable names) ---
    if not facets.parsed or facets.base_token is None:
        return None
    if facets.base_token == name:
        return None
    return facets.base_token


def _arguments_parent(name: str, entry: dict[str, Any]) -> str | None:
    """Extract the first non-self argument target from the YAML entry."""
    args = entry.get("arguments")
    if not isinstance(args, list):
        return None
    for arg in args:
        if not isinstance(arg, dict):
            continue
        target = arg.get("name")
        if isinstance(target, str) and target and target != name:
            return target
    return None


def _local_ir_peel(name: str) -> str | None:
    """Peel ONE structural layer from *name* using the ISN IR parser.

    Mirrors imas-codex/imas_codex/standard_names/derivation.py logic
    so that catalogs built outside the imas-codex pipeline still
    surface accurate parents in the SPA.

    Returns ``None`` when the name is a leaf, unparseable, or when
    the peeled inner name fails to round-trip.
    """
    try:
        result = parse(name)
    except Exception:
        return None

    ir = result.ir
    stripped = None
    if ir.operators:
        # Outermost operator: drop the head of ir.operators
        stripped = ir.model_copy(update={"operators": ir.operators[1:]})
    elif ir.projection is not None:
        stripped = ir.model_copy(update={"projection": None})
    elif ir.qualifiers:
        # Outermost qualifier — covers upper/lower/inner/outer/electron/ion/…
        stripped = ir.model_copy(update={"qualifiers": ir.qualifiers[1:]})
    elif ir.locus is not None:
        stripped = ir.model_copy(update={"locus": None})
    else:
        return None  # leaf

    try:
        inner = compose(stripped)
    except Exception:
        return None

    if not inner or inner == name:
        return None
    return inner


def _group_title(name: str, facets: _GrammarFacets) -> str:
    """Compute the locus-first group title for SPA list clustering.

    Priority order:

    1. Locus token — siblings clustered by structural locality
    2. Base token — siblings clustered by physical quantity
    3. Falls back to ``"other quantities"`` for unparseable names.

    The returned string is humanised (snake_case → space-separated
    lowercase) so the SPA can render it directly without further string
    handling.
    """
    if facets.parsed:
        if facets.locus_token is not None:
            return _humanise(facets.locus_token)
        if facets.base_token is not None:
            return _humanise(facets.base_token)
    return "other quantities"


# ---------------------------------------------------------------------------
# Helpers — tag derivation
# ---------------------------------------------------------------------------


def _derive_tags(
    entry_tags: list[str] | None,
    facets: _GrammarFacets,
) -> list[str]:
    """Return the entry's explicit tags, falling back to grammar-derived ones.

    Many catalog entries omit the ``tags`` field. The SPA still wants
    something descriptive; we synthesise a small set of tags from the
    IR (e.g. ``component``, ``locus``, ``averaged``, ``magnitude``) to
    keep the sidebar useful when the catalog has not yet been hand-tagged.
    """
    if entry_tags:
        return [str(t) for t in entry_tags if isinstance(t, str)]

    derived: list[str] = []
    if facets.has_projection:
        derived.append("component")
    if facets.has_locus:
        derived.append("locus")
    if "magnitude" in facets.operator_tokens:
        derived.append("magnitude")
    if any(q.endswith("averaged") for q in facets.qualifier_tokens):
        derived.append("averaged")
    if any(q.endswith("integrated") for q in facets.qualifier_tokens):
        derived.append("integrated")
    if facets.has_mechanism:
        derived.append("mechanism")
    return derived


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------


def _normalise_status(raw: str | None) -> str | None:
    """Map legacy status values to the canonical set; return None to drop.

    Canonical values (pass through unchanged):
        ``"draft"``, ``"active"``, ``"deprecated"``, ``"superseded"``

    Legacy mappings:
        ``"drafted"``   → ``"draft"``
        ``"accepted"``  → ``"active"``
        ``"published"`` → ``"active"``

    Unknown values are logged as warnings and ``None`` is returned so
    the entry is silently dropped from the emitted dataset.
    """
    if not raw:
        return "draft"
    _LEGACY: dict[str, str] = {
        "drafted": "draft",
        "accepted": "active",
        "published": "active",
    }
    _CANONICAL: frozenset[str] = frozenset(
        {"draft", "active", "deprecated", "superseded"}
    )
    if raw in _CANONICAL:
        return raw
    mapped = _LEGACY.get(raw)
    if mapped is not None:
        return mapped
    _log.warning("unknown status %r — entry will be dropped", raw)
    return None


def _build_record(entry: dict[str, Any]) -> dict[str, Any]:
    """Build one NAMES record from a parsed YAML entry.

    Emits ``algebra`` (scalar / vector / tensor / complex / metadata)
    from the catalog entry's ``kind`` field.  The synthetic
    ``display_kind`` / ``kind`` fields are no longer emitted; the SPA
    reads only ``algebra`` for kind-based filtering and badging.

    The ``status`` field on the entry is expected to have already been
    normalised by ``_normalise_status`` before this function is called.
    """
    name = str(entry.get("name") or "")
    category = entry.get("physics_domain") or "uncategorized"
    facets = _derive_grammar_facets(name)
    algebra = entry.get("kind") or "scalar"
    # Vector components inherit vector algebra from their projection axis.
    # A name like radial_magnetic_field carries axis="radial" — the
    # coefficient B_R of a vector B = B_R r̂ + B_φ φ̂ + B_Z ẑ is not
    # rotation-invariant and therefore must not be classified as scalar.
    # Same parallel-construction reasoning as the schema's treatment of
    # tensor components.
    if algebra == "scalar" and facets.has_projection:
        algebra = "vector"

    parent = _parent_token(name, facets, entry)
    sort_tier = _sort_tier(name, str(algebra), parent, facets)
    sort_axis_index = _sort_axis_index(facets)
    group = _group_title(name, facets)
    tags = _derive_tags(entry.get("tags"), facets)

    # Status has already been normalised by build_site_dataset.
    status = entry.get("status") or "draft"
    # Subject — first qualifier token matching the closed Subject enum
    # (electron, ion, deuterium, …). Drives the SPA's subject filter so
    # users can slice by species without text-search.
    subject = _extract_subject(facets.qualifier_tokens)

    short = entry.get("description") or ""
    long_text, sign = _extract_sign(entry.get("documentation") or "")
    see_also = _normalise_see_also(entry.get("links"))
    sources = _normalise_sources(entry.get("sources"))
    arguments = _normalise_arguments(entry.get("arguments"))
    superseded_by = entry.get("superseded_by") or None
    deprecates = entry.get("deprecates") or None

    record: dict[str, Any] = {
        "name": name,
        "category": str(category),
        "group": group,
        "parent": parent,
        "algebra": str(algebra),
        "status": str(status),
        "subject": str(subject) if subject else None,
        "unit": entry.get("unit") or "",
        "tags": tags,
        "short": short,
        "long": long_text,
        "sign": sign,
        "seeAlso": see_also,
        "arguments": arguments,
        "sources": sources,
        "superseded_by": superseded_by,
        "deprecates": deprecates,
        "parse": facets.parse_segments,
        "sort_tier": sort_tier,
        "sort_axis_index": sort_axis_index,
    }
    if facets.axis is not None:
        record["axis"] = facets.axis
    if facets.locus_token is not None:
        record["locus"] = facets.locus_token
    return record


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _load_entries(catalog_path: Path) -> list[dict[str, Any]]:
    """Load every standard name YAML file under ``catalog_path``.

    Accepts the published per-domain list-of-entries layout. Returns
    a flat list ordered by file name then in-file order.
    """
    entries: list[dict[str, Any]] = []
    if not catalog_path.exists():
        return entries
    yaml_files = sorted(
        list(catalog_path.rglob("*.yml")) + list(catalog_path.rglob("*.yaml"))
    )
    for yaml_file in yaml_files:
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    entries.append(item)
        elif isinstance(data, dict) and "name" in data:
            entries.append(data)
    return entries


def _load_manifest(catalog_path: Path) -> StandardNameCatalogManifest | None:
    """Load ``catalog.yml`` if present alongside (or in) the catalog dir.

    Looks first at ``catalog_path.parent/catalog.yml`` (the standard
    layout — manifest at repo root, entries under ``standard_names/``)
    then at ``catalog_path/catalog.yml`` (entries under repo root).
    Returns ``None`` when the manifest is missing or invalid; the
    dataset builder still works without it.
    """
    candidates = [
        catalog_path.parent / "catalog.yml",
        catalog_path / "catalog.yml",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        try:
            return StandardNameCatalogManifest(**data)
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Categories / grammar vocab
# ---------------------------------------------------------------------------


def _build_categories(names: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate NAMES into ``[{id, label, count}]`` sorted by count desc.

    Ties break alphabetically on the slug for determinism.
    """
    counts: Counter[str] = Counter(record.get("category", "") for record in names)
    rows: list[tuple[str, int]] = sorted(
        counts.items(), key=lambda pair: (-pair[1], pair[0])
    )
    return [
        {
            "id": slug,
            "label": _humanise_domain(slug),
            "count": count,
        }
        for slug, count in rows
        if slug
    ]


def _build_grammar_vocab() -> dict[str, list[str]]:
    """Build the SPA's GRAMMAR_VOCAB sections from the ISN grammar context.

    The SPA uses a small subset of the full grammar context, organised
    by UI role (reduction / axis / modifier / operator_suffix / base /
    preposition / locus / subject). We populate each role from the
    canonical vocabularies so the SPA's chip styling lines up with the
    parser's tokens.
    """
    try:
        vocabs = load_default_vocabularies()
    except Exception:
        return {}

    try:
        grammar = get_grammar_context().get("grammar", {})
    except Exception:
        grammar = {}

    operators = grammar.get("vocabularies", {}).get("operators", {}) or {}

    reduction_tokens = sorted(
        token
        for token, meta in operators.items()
        if meta.get("kind") == "unary_prefix"
        and token
        in _REDUCTION_PREFIX_OPS
        | {"flux_surface_averaged", "volume_averaged", "line_averaged"}
    )
    modifier_tokens = sorted(
        token
        for token, meta in operators.items()
        if meta.get("kind") == "unary_prefix"
        and token not in _REDUCTION_PREFIX_OPS
        and token not in {"flux_surface_averaged", "volume_averaged", "line_averaged"}
    )
    operator_suffix_tokens = sorted(
        token
        for token, meta in operators.items()
        if meta.get("kind") == "unary_postfix"
    )

    return {
        "reduction": reduction_tokens,
        "axis": sorted(vocabs.axes),
        "modifier": modifier_tokens,
        "operator_suffix": operator_suffix_tokens,
        "base": sorted(vocabs.bases),
        "preposition": sorted(["of", "at", "over"]),
        "locus": sorted(vocabs.loci),
        "subject": sorted(vocabs.qualifiers - vocabs.axes - set(operators.keys())),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _enrich_with_reverse_links(
    records: list[dict[str, Any]],
    entries: list[dict[str, Any]],
) -> None:
    """Add ``components``, ``magnitude``, and ``children`` reverse-edges.

    Each record gets:

    - ``components`` (list of ``{name, axis}``): for ``algebra='vector'``
      entries only — the axis-projection children that point at this
      vector via ``arguments[*].operator_kind='projection'``. Empty if
      no components are present in this catalog snapshot.
    - ``magnitude`` (str | None): for ``algebra='vector'`` entries only
      — the corresponding ``magnitude_of_<name>`` SN if it exists in
      this catalog. Captures the algebraic vector ⇄ magnitude link
      without requiring graph access (source-driven; only fires when
      the magnitude SN was already composed from DD).
    - ``children`` (list of ``{name, operator_kind}``): all direct
      children regardless of algebra — anything whose first argument
      points at this entry. Used by the SPA's detail panel.

    Mutates *records* in place.
    """
    # Index records by name for fast lookups.
    by_name: dict[str, dict[str, Any]] = {r["name"]: r for r in records}

    # Build a child-by-parent index from the raw YAML entries (we want
    # the operator_kind / axis on each edge, which the normalised
    # ``arguments`` field on records flattens to just names).
    child_index: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        child_name = str(entry.get("name") or "")
        if not child_name:
            continue
        for arg in entry.get("arguments") or []:
            if not isinstance(arg, dict):
                continue
            parent_name = arg.get("name")
            if not isinstance(parent_name, str) or not parent_name:
                continue
            child_index.setdefault(parent_name, []).append(
                {
                    "name": child_name,
                    "operator_kind": arg.get("operator_kind"),
                    "axis": arg.get("axis"),
                }
            )

    for record in records:
        name = record["name"]
        children = sorted(
            child_index.get(name, []),
            key=lambda c: c["name"],
        )
        record["children"] = [
            {
                "name": c["name"],
                "operator_kind": c.get("operator_kind"),
            }
            for c in children
        ]

        if record.get("algebra") == "vector":
            # Components: projection children with axis.
            record["components"] = [
                {"name": c["name"], "axis": c.get("axis")}
                for c in children
                if c.get("operator_kind") == "projection" and c.get("axis")
            ]
            # Magnitude: the magnitude_of_<name> SN if it exists.
            magnitude_id = f"magnitude_of_{name}"
            record["magnitude"] = magnitude_id if magnitude_id in by_name else None
        else:
            # Mirror the vector branch with empty values so the SPA can
            # rely on the keys being present without per-kind branching.
            record["components"] = []
            record["magnitude"] = None


def build_site_dataset(
    catalog_path: Path,
) -> dict[str, Any]:
    """Build the SPA dataset from a directory of standard-name YAMLs.

    Parameters
    ----------
    catalog_path : Path
        Directory containing one YAML file per physics_domain. The
        catalog manifest is read from ``catalog_path.parent/catalog.yml``
        when present (the published layout); a missing manifest is not
        an error.

    Returns
    -------
    dict
        Keys: ``CATALOG_VERSION`` (str), ``CATEGORIES`` (list),
        ``GRAMMAR_VOCAB`` (dict), ``NAMES`` (list of records).

    Notes
    -----
    All entries whose normalised status is one of the four canonical
    values (``active``, ``draft``, ``deprecated``, ``superseded``) are
    emitted.  Entries with unknown status values are logged and dropped.
    """
    catalog_path = Path(catalog_path)
    raw_entries = _load_entries(catalog_path)

    # Normalise status — emit every entry with a known canonical status.
    entries: list[dict[str, Any]] = []
    for raw in raw_entries:
        entry = dict(raw)
        normalised = _normalise_status(entry.get("status"))
        if normalised is None:
            # Unknown status — already logged; drop silently.
            continue
        entry["status"] = normalised
        entries.append(entry)

    names = [_build_record(entry) for entry in entries]

    # Post-pass: enrich each record with reverse-edge lookups. Vectors
    # get their ``components`` and ``magnitude``; every entry gets
    # ``children`` for the detail panel.
    _enrich_with_reverse_links(names, entries)

    manifest = _load_manifest(catalog_path)
    if manifest is not None:
        # Use the ACTUAL number of records emitted, not the manifest's
        # ``published_count`` — manifest counts can lag if the export
        # filter excluded entries after the manifest was written.
        version = (
            f"{manifest.catalog_name} {manifest.grammar_version} · {len(names)} names"
        )
    else:
        version = f"{len(names)} names"

    return {
        "CATALOG_VERSION": version,
        "CATEGORIES": _build_categories(names),
        "GRAMMAR_VOCAB": _build_grammar_vocab(),
        "NAMES": names,
    }


def write_site_dataset(
    catalog_path: Path,
    out_path: Path,
) -> int:
    """Build and write the SPA dataset to ``out_path`` as JSON.

    Parameters
    ----------
    catalog_path : Path
        Directory of per-domain YAML files.
    out_path : Path
        Destination JSON file.

    Returns the number of NAMES records emitted.
    """
    catalog_path = Path(catalog_path)
    out_path = Path(out_path)
    dataset = build_site_dataset(catalog_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return len(dataset.get("NAMES", []))
