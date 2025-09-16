"""Semantic validation checks for provenance/operator logic."""

from __future__ import annotations
from typing import Dict, List
from ..schema import StandardName
from ..provenance import OperatorProvenance

__all__ = ["run_semantic_checks"]


def run_semantic_checks(entries: Dict[str, StandardName]) -> List[str]:
    issues: List[str] = []
    for name, entry in entries.items():
        prov = getattr(entry, "provenance", None)
        if isinstance(prov, OperatorProvenance):
            # Example rule: if gradient operator present, unit should include division by length
            if "gradient" in [op for op in prov.operators]:
                unit = getattr(entry, "unit", "")
                if unit and "/" not in unit and ".m" not in unit and unit != "":
                    issues.append(
                        f"{name}: gradient operator present but unit '{unit}' does not look like derivative (heuristic)."
                    )
    return issues
