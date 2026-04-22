"""Reduction (aggregation) naming patterns and enforcement.

DEPRECATED — plan 38 §A7 merged reduction patterns into operators.yml.
This stub preserves the ``enforce_reduction_naming`` import expected by
``models.py`` until W2c removes the reference.
"""

from __future__ import annotations


def enforce_reduction_naming(name: str, **kwargs) -> str:  # noqa: ARG001
    """No-op stub — reductions are now handled by the operator registry."""
    return name
