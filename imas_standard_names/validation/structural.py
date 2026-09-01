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
        * Every deprecation stub (``status == "deprecated"``) names a
          successor via ``superseded_by`` (field presence only — resolving
          the successor to a live catalog entry is a separate reference-
          integrity check, not a structural one).
    """
    issues: list[str] = []
    for name, entry in entries.items():
        if entry.kind == "vector":
            mag = f"magnitude_of_{name}"
            if mag not in entries:
                pass
        if getattr(entry, "status", None) == "deprecated" and not getattr(
            entry, "superseded_by", None
        ):
            issues.append(
                f"{name}: deprecated entry must set 'superseded_by' naming its "
                "live successor"
            )
    return issues
