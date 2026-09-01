"""Validation functions for standard name descriptions.

This module checks for metadata leakage where structural information
(data organization, dimensionality) appears in semantic descriptions
instead of being captured by structured metadata fields.
"""

from __future__ import annotations

import re
from typing import Any

# A LaTeX backslash command such as \phi, \nabla, or \mathbf.
_LATEX_COMMAND = re.compile(r"\\[a-zA-Z]+")

# Spelled-out Greek letter words that should be their Unicode symbols in
# descriptions (word-bounded so e.g. "Doppler" or "phi_tor" DD tokens in
# adjacent fields are untouched; descriptions carry prose only).
_GREEK_WORDS = {
    "phi": "φ",
    "theta": "θ",
    "rho": "ρ",
}
_GREEK_WORD = re.compile(r"\b(phi|theta|rho)\b")

# Descriptions are plain text with Unicode Greek symbols; LaTeX markup belongs
# in the documentation field.
_NOTATION_SUGGESTION = (
    "Descriptions are plain text; LaTeX and math markup belong in the "
    "documentation field. Write Greek letters as Unicode symbols (φ, θ, ρ) "
    "and coordinate frames as (R, φ, Z)."
)

# COCOS conventions are never named by number in human-readable text: sign and
# coordinate conventions must be stated explicitly in physical terms (e.g. "q is
# positive when the toroidal field and plasma current are parallel"). The COCOS
# integer belongs only in structured metadata, not in the description or
# documentation prose.
# Match the COCOS token whether or not a number is attached directly
# (``COCOS``, ``COCOS11``, ``cocos17``) as well as the separated forms
# (``COCOS 11``, ``COCOS-17``, ``COCOS=11``) where the trailing ``\d*`` matches
# nothing and the word boundary falls before the separator.
_COCOS_MENTION = re.compile(r"\bcocos\d*\b", re.IGNORECASE)
_COCOS_SUGGESTION = (
    "Do not name a COCOS number in prose; state the sign and coordinate "
    "conventions explicitly in physical terms. The COCOS integer belongs in "
    "structured metadata only."
)


def validate_description(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate description to detect structural metadata leakage.

    Checks if description contains phrases that describe data organization
    or dimensionality rather than semantic meaning. Returns warnings (not
    errors) to guide users toward better practices while allowing overrides.

    Args:
        entry: Standard name entry dict with 'description', etc.

    Returns:
        List of issue dicts with keys:
            - severity: 'warning' or 'info'
            - field: 'description'
            - message: Human-readable description of issue
            - suggestion: Recommended fix (optional)
            - pattern: Matched redundant pattern
    """
    issues: list[dict[str, Any]] = []

    raw_description = entry.get("description", "")
    description = raw_description.lower()

    # An empty description is valid; the description-specific checks below are
    # no-ops on empty text. The COCOS and unit-restatement checks near the end
    # inspect the documentation field too, so they must run even when the
    # description is absent (documentation-only entries).

    # General structural (not semantic) patterns
    structural_patterns = [
        ("stored on", "Data storage details belong in implementation, not description"),
        ("stored in", "Data storage details belong in implementation, not description"),
        (
            "calculated from",
            "Calculation method belongs in provenance field, not description",
        ),
        ("derived from", "Derivation belongs in provenance field, not description"),
        ("obtained from", "Source information belongs in metadata, not description"),
        ("1d", "Dimensionality is captured by data structure, not description"),
        ("2d", "Dimensionality is captured by data structure, not description"),
        ("3d", "Dimensionality is captured by data structure, not description"),
        (
            "one dimensional",
            "Dimensionality is captured by data structure, not description",
        ),
        (
            "two dimensional",
            "Dimensionality is captured by data structure, not description",
        ),
        (
            "three dimensional",
            "Dimensionality is captured by data structure, not description",
        ),
    ]

    for pattern, reason in structural_patterns:
        if pattern in description:
            issues.append(
                {
                    "severity": "info",
                    "field": "description",
                    "message": f"Description contains structural phrase '{pattern}'",
                    "suggestion": reason,
                    "pattern": pattern,
                }
            )

    # Math-notation leakage: descriptions are plain text with Unicode Greek
    # symbols. LaTeX ($...$) and backslash commands (\phi) belong in
    # documentation.
    if "$" in raw_description:
        issues.append(
            {
                "severity": "warning",
                "field": "description",
                "message": "Description contains a '$' math delimiter",
                "suggestion": _NOTATION_SUGGESTION,
                "pattern": "$",
            }
        )

    latex_match = _LATEX_COMMAND.search(raw_description)
    if latex_match:
        command = latex_match.group()
        issues.append(
            {
                "severity": "warning",
                "field": "description",
                "message": f"Description contains a LaTeX command '{command}'",
                "suggestion": _NOTATION_SUGGESTION,
                "pattern": command,
            }
        )

    word_match = _GREEK_WORD.search(description)
    if word_match:
        word = word_match.group()
        issues.append(
            {
                "severity": "info",
                "field": "description",
                "message": f"Description spells out the Greek letter '{word}'",
                "suggestion": f"Write the symbol '{_GREEK_WORDS[word]}' instead of the word '{word}'",
                "pattern": word,
            }
        )

    # COCOS conventions must be stated explicitly, never named by number.
    for field in ("description", "documentation"):
        text = entry.get(field, "") or ""
        if _COCOS_MENTION.search(text):
            issues.append(
                {
                    "severity": "error",
                    "field": field,
                    "message": f"{field.capitalize()} names a COCOS convention",
                    "suggestion": _COCOS_SUGGESTION,
                    "pattern": "cocos",
                }
            )

    issues.extend(_check_inline_unit_restatement(entry))

    return issues


# Regions of documentation where units MAY legitimately appear: display math
# ($$...$$) and inline math ($...$) — equation variable definitions and
# unit-conversion statements. Everything else is prose.
_DISPLAY_MATH = re.compile(r"\$\$.*?\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"\$.*?\$", re.DOTALL)

# Characters that can extend a unit token (SI symbols, exponents, signs).
# A unit match is only a restatement when NOT flanked by these — otherwise
# single-letter units (m, s, T, A) would match inside ordinary words
# ("m" in "magnetic") or inside larger compound units (m^-3 in kg.m^-3).
# The product separator `.` is special: it extends a unit token only when
# alphanumerics sit on its far side (kg.m^-3, m.s^-1); a `.` followed by
# whitespace or end-of-text is sentence punctuation.
_UNIT_BOUNDARY_CHAR = r"[A-Za-z0-9^+-]"


def _unit_restatement_pattern(unit: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<!{_UNIT_BOUNDARY_CHAR})(?<![A-Za-z0-9]\.)"
        rf"{re.escape(unit)}"
        rf"(?!{_UNIT_BOUNDARY_CHAR}|\.[A-Za-z0-9])"
    )


def _check_inline_unit_restatement(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Flag documentation prose that restates the entry's own canonical unit.

    Conservative guard for the "no-inline-units" rule (the unit belongs in the
    ``unit`` field; the SPA renders it in the unit pill). Only fires when the
    entry's EXACT canonical ``unit`` string (e.g. ``m^-3``, ``kg.m^-1.s^-2``)
    appears as a standalone token in the ``documentation`` OUTSIDE math
    regions — a clear restatement, low false-positive. Dimensionless (``1``)
    is ignored. Warning, not error.
    """
    unit = (entry.get("unit") or "").strip()
    documentation = entry.get("documentation", "") or ""
    if not unit or unit == "1" or not documentation:
        return []
    prose = _INLINE_MATH.sub(" ", _DISPLAY_MATH.sub(" ", documentation))
    if _unit_restatement_pattern(unit).search(prose):
        return [
            {
                "severity": "warning",
                "field": "documentation",
                "message": (
                    f"Documentation prose restates the unit '{unit}' outside a "
                    "math region"
                ),
                "suggestion": (
                    "Units live in the unit field (rendered by the unit pill); "
                    "do not restate them in prose except inside equation, "
                    "typical-value-range, or unit-conversion statements."
                ),
                "pattern": unit,
            }
        ]
    return []


__all__ = ["validate_description"]
