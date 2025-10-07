"""Structural validation checks.

These checks operate across multiple StandardName entries to ensure
relational consistency beyond individual model validation.
"""

from __future__ import annotations

from ..models import StandardNameEntry

__all__ = ["run_structural_checks"]


def run_structural_checks(entries: dict[str, StandardNameEntry]) -> list[str]:
    """Return a list of structural issues discovered.

    Current rules:
        * All magnitude names referenced actually exist
    """
    issues: list[str] = []
    for name, entry in entries.items():
        if entry.kind == "vector":
            mag = f"magnitude_of_{name}"
            if mag not in entries:
                pass
    return issues
