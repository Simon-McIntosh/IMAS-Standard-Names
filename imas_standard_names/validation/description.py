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

# Greek and Coptic (U+0370–U+03FF) plus Greek Extended (U+1F00–U+1FFF) blocks —
# Greek letters must be written as words (phi, theta, rho) in plain-text
# descriptions.
_GREEK = re.compile("[Ͱ-Ͽἀ-῿]")

# Descriptions are plain text; math notation belongs in the documentation field.
_NOTATION_SUGGESTION = (
    "Descriptions are plain text; LaTeX and math markup belong in the "
    "documentation field. Write Greek letters as words (phi, theta, rho) "
    "and coordinate frames as (R, phi, Z)."
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

    # Math-notation leakage: descriptions are plain text. LaTeX ($...$),
    # backslash commands (\phi), and Unicode Greek belong in documentation.
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

    greek_match = _GREEK.search(raw_description)
    if greek_match:
        character = greek_match.group()
        issues.append(
            {
                "severity": "warning",
                "field": "description",
                "message": f"Description contains a Unicode Greek character '{character}'",
                "suggestion": _NOTATION_SUGGESTION,
                "pattern": character,
            }
        )

    return issues


__all__ = ["validate_description"]
