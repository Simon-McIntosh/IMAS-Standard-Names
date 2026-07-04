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

    if not description:
        return issues  # Empty description is valid

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

    return issues


__all__ = ["validate_description"]
