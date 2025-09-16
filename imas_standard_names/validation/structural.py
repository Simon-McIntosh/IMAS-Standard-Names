"""Structural validation checks.

These checks operate across multiple StandardName entries to ensure
relational consistency beyond individual model validation.
"""

from __future__ import annotations
from typing import Dict, List
from ..schema import StandardName

__all__ = ["run_structural_checks"]


def run_structural_checks(entries: Dict[str, StandardName]) -> List[str]:
    """Return a list of structural issues discovered.

    Current placeholder rules (expand later):
      * All magnitude names referenced actually exist
      * Component references exist & backlink parent_vector
    """
    issues: List[str] = []
    for name, entry in entries.items():
        data = entry.model_dump()
        # Magnitude reference existence
        mag = data.get("magnitude")
        if mag and mag not in entries:
            issues.append(f"{name}: magnitude '{mag}' not found")
        # Components existence + backlink
        components = data.get("components", {}) or {}
        for comp in components.values():
            if comp not in entries:
                issues.append(f"{name}: component '{comp}' file missing")
            else:
                comp_parent = getattr(entries[comp], "parent_vector", None)
                if comp_parent and comp_parent != name:
                    issues.append(
                        f"{name}: component '{comp}' parent_vector mismatch (has {comp_parent})"
                    )
    return issues
