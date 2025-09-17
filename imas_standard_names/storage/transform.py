"""Transformation helpers for schema models."""

from __future__ import annotations
from typing import Dict, Any
from ..schema import StandardNameBase

__all__ = ["model_to_minimal_dict"]


def model_to_minimal_dict(entry: StandardNameBase) -> Dict[str, Any]:
    """Return a minimal serialized representation (dimensionless normalized)."""
    data = entry.model_dump(exclude_none=True, exclude_unset=True)
    if data.get("unit", "") == "":
        data["unit"] = "1"  # explicit for external consumers
    return data
