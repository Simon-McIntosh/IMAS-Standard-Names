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
* structural ``kind`` (``base | component | at_point | global | location``)
  derived from the grammar IR
* physical metadata: ``unit``, ``tags``, ``axis``, ``locus``
* prose: ``short`` (description), ``long`` (documentation minus the
  ``Sign convention:`` paragraph), ``sign`` (the extracted paragraph)
* navigation: ``seeAlso`` (links normalised, ``name:`` prefix stripped),
  ``arguments`` (just the argument names), ``sources``
  (``{path, status}``)
* ``parse`` — a list of role/text/note segments (operators, qualifiers,
  axis, base, locus, process) for the UI to render as chips.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from imas_standard_names.grammar.context import get_grammar_context
from imas_standard_names.grammar.parser import (
    ParseError,
    load_default_vocabularies,
    parse,
)
from imas_standard_names.models import StandardNameCatalogManifest

__all__ = [
    "build_site_dataset",
    "write_site_dataset",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# Prefix operator tokens treated as "reductions": when present as the
# outermost qualifier on an otherwise base-style name (no projection, no
# locus, no _due_to_ tail), the result is a scalar summary (``global``).
# Operators like ``flux_surface_averaged`` and ``normalized`` do NOT
# reduce to a scalar — they remain field-like and so stay as ``base``.
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


# Subject-style qualifier tokens that indicate the name is a global
# scalar summary rather than a field. ``total_`` is the canonical prefix
# but a few enum subjects (``total_plasma``) carry the same meaning.
_GLOBAL_SUBJECT_QUALIFIERS: frozenset[str] = frozenset(
    {
        "total",
        "total_plasma",
        "plasma",
    }
)


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

    These drive the structural ``kind``, ``parent``, ``axis``, ``locus``,
    grammar-derived ``tags``, and ``parse`` segments. Holding them in a
    single dataclass keeps the helper logic testable and clear.
    """

    parsed: bool
    parse_segments: list[dict[str, str]]
    base_token: str | None
    axis: str | None
    locus_token: str | None
    has_projection: bool
    has_locus: bool
    has_reduction_qualifier: bool
    has_global_subject_qualifier: bool
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
            has_reduction_qualifier=False,
            has_global_subject_qualifier=False,
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
    has_reduction_qualifier = False
    has_global_subject_qualifier = False
    for qualifier in ir.qualifiers:
        token = qualifier.token
        qualifier_tokens.append(token)
        if token in _REDUCTION_PREFIX_OPS:
            has_reduction_qualifier = True
        if token in _GLOBAL_SUBJECT_QUALIFIERS or token.startswith("total_"):
            has_global_subject_qualifier = True
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
        has_reduction_qualifier=has_reduction_qualifier,
        has_global_subject_qualifier=has_global_subject_qualifier,
        qualifier_tokens=tuple(qualifier_tokens),
        operator_tokens=tuple(operator_tokens),
        has_mechanism=has_mechanism,
    )


# ---------------------------------------------------------------------------
# Helpers — structural kind / parent / group
# ---------------------------------------------------------------------------


def _structural_kind(
    name: str, pydantic_kind: str | None, facets: _GrammarFacets
) -> str:
    """Compute the SPA's structural kind from grammar + pydantic kind.

    Order of precedence:

    1. ``location`` for ``metadata`` pydantic entries
    2. ``at_point`` when the IR carries a locus suffix
    3. ``component`` when the IR carries an axis projection
    4. ``global`` for reductions / subject-scalars (``total_*``,
       ``minimum_*``, ``volume_integrated_*``, etc.)
    5. ``base`` otherwise (the default for a field-valued quantity)
    """
    if pydantic_kind == "metadata":
        return "location"
    if not facets.parsed:
        return "base"
    if facets.has_locus:
        return "at_point"
    if facets.has_projection:
        return "component"
    if name.startswith("total_"):
        return "global"
    if facets.has_reduction_qualifier:
        return "global"
    if facets.has_global_subject_qualifier:
        return "global"
    return "base"


def _parent_token(name: str, facets: _GrammarFacets) -> str | None:
    """Return the parent base token if the name decomposes onto a base.

    Heuristic per the SPA spec: when ``ir.base`` is set and the name
    string is not itself the bare base, the parent is the base token.
    Otherwise ``None``. We do not verify the parent exists in the
    catalog — the SPA tolerates dangling parents.
    """
    if not facets.parsed or facets.base_token is None:
        return None
    if facets.base_token == name:
        return None
    return facets.base_token


def _group_title(name: str, facets: _GrammarFacets) -> str:
    """Compute the locus-first group title for SPA list clustering.

    Priorities (mirrors :class:`CatalogRenderer._group_key`):

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
    structural_kind: str,
) -> list[str]:
    """Return the entry's explicit tags, falling back to grammar-derived ones.

    Many catalog entries omit the ``tags`` field. The SPA still wants
    something descriptive; we synthesise a small set of tags from the
    IR (e.g. ``component``, ``averaged``, ``magnitude``) to keep the
    sidebar useful when the catalog has not yet been hand-tagged.
    """
    if entry_tags:
        return [str(t) for t in entry_tags if isinstance(t, str)]

    derived: list[str] = []
    if structural_kind == "component":
        derived.append("component")
    if structural_kind == "at_point":
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


def _build_record(entry: dict[str, Any]) -> dict[str, Any]:
    """Build one NAMES record from a parsed YAML entry."""
    name = str(entry.get("name") or "")
    category = entry.get("physics_domain") or "uncategorized"
    facets = _derive_grammar_facets(name)
    pydantic_kind = entry.get("kind")

    structural_kind = _structural_kind(name, pydantic_kind, facets)
    parent = _parent_token(name, facets)
    group = _group_title(name, facets)
    tags = _derive_tags(entry.get("tags"), facets, structural_kind)

    short = entry.get("description") or ""
    long_text, sign = _extract_sign(entry.get("documentation") or "")
    see_also = _normalise_see_also(entry.get("links"))
    sources = _normalise_sources(entry.get("sources"))
    arguments = _normalise_arguments(entry.get("arguments"))

    record: dict[str, Any] = {
        "name": name,
        "category": str(category),
        "group": group,
        "parent": parent,
        "kind": structural_kind,
        "unit": entry.get("unit") or "",
        "tags": tags,
        "short": short,
        "long": long_text,
        "sign": sign,
        "seeAlso": see_also,
        "arguments": arguments,
        "sources": sources,
        "parse": facets.parse_segments,
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


def build_site_dataset(catalog_path: Path) -> dict[str, Any]:
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
    """
    catalog_path = Path(catalog_path)
    entries = _load_entries(catalog_path)
    names = [_build_record(entry) for entry in entries]

    manifest = _load_manifest(catalog_path)
    if manifest is not None:
        version = (
            f"{manifest.catalog_name} {manifest.grammar_version}"
            f" · {manifest.published_count} names"
        )
    else:
        version = f"{len(names)} names"

    return {
        "CATALOG_VERSION": version,
        "CATEGORIES": _build_categories(names),
        "GRAMMAR_VOCAB": _build_grammar_vocab(),
        "NAMES": names,
    }


def write_site_dataset(catalog_path: Path, out_path: Path) -> int:
    """Build and write the SPA dataset to ``out_path`` as JSON.

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
