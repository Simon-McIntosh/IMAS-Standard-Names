"""Validation functions for standard name descriptions.

This module checks for metadata leakage where structural information
(data organization, dimensionality) appears in semantic descriptions
instead of being captured by structured metadata fields.
"""

from __future__ import annotations

from typing import Any


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

    description = entry.get("description", "").lower()

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

    return issues


__all__ = ["validate_description"]
