"""Validation functions for standard name descriptions.

This module checks for metadata leakage where structural information
(data organization, dimensionality) appears in semantic descriptions
instead of being captured by tags and other metadata fields.
"""

from __future__ import annotations

from typing import Any


def validate_description(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate description against tags to detect metadata leakage.

    Checks if description contains phrases that are redundant with existing
    tags or other structured metadata fields. Returns warnings (not errors)
    to guide users toward better practices while allowing overrides.

    Args:
        entry: Standard name entry dict with 'description', 'tags', etc.

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
    tags = entry.get("tags", [])

    if not description:
        return issues  # Empty description is valid

    # Tag-specific redundancy patterns
    tag_patterns = {
        "spatial-profile": [
            "radial profile of",
            "profile of",
            "as function of radial",
            "as function of radius",
            "radial variation of",
            "radial dependence of",
        ],
        "time-dependent": [
            "time series of",
            "time evolution of",
            "temporal evolution",
            "history of",
            "time history",
        ],
        "flux-surface-average": [
            "flux surface averaged",
            "averaged over flux surface",
            "flux surface average of",
        ],
        "volume-average": [
            "volume averaged",
            "averaged over volume",
            "volume average of",
        ],
        "line-integrated": [
            "line integrated",
            "integrated along line",
            "line integral of",
        ],
    }

    # Check for tag-redundant patterns
    for tag, patterns in tag_patterns.items():
        if tag in tags:
            for pattern in patterns:
                if pattern in description:
                    # Exception: gm* transport quantities (geometric moments) are allowed
                    # to include "flux surface averaged" as it's part of their definition
                    if (
                        tag == "flux-surface-average"
                        and pattern == "flux surface averaged"
                    ):
                        name = entry.get("name", "")
                        # Check if this is a standard transport quantity (gm* parameter)
                        gm_patterns = [
                            "inverse_major_radius",
                            "major_radius",
                            "magnetic_field_strength",
                            "squared_magnetic_field_strength",
                            "inverse_squared_magnetic_field_strength",
                            "toroidal_flux_coordinate_gradient",
                            "toroidal_current_density",
                            "parallel_current_density",
                            "bootstrap",
                            "ohmic",
                            "diamagnetic",
                        ]
                        is_gm_transport = any(
                            gm_name in name for gm_name in gm_patterns
                        )
                        if is_gm_transport:
                            continue  # Skip warning for gm* transport quantities

                    issues.append(
                        {
                            "severity": "warning",
                            "field": "description",
                            "message": f"Description contains '{pattern}' but entry has '{tag}' tag",
                            "suggestion": f"Remove '{pattern}' - the {tag} tag already conveys this information",
                            "pattern": pattern,
                            "redundant_with": tag,
                        }
                    )

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
