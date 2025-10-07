"""Reduction (aggregation) naming patterns and enforcement.

Defines grammar-driven prefix patterns like:
  time_average_of_<base>
  root_mean_square_of_<base>
  magnitude_of_<vector_base>
  volume_integral_of_<base>

Outermost-first pattern matching (longest prefix wins) provides deterministic
reconstruction of (reduction, domain, base). Validation is invoked from schema
model validators for ReductionProvenance entries.
"""

from __future__ import annotations

from pydantic import BaseModel


class ReductionPattern(BaseModel):
    prefix: str
    reduction: str
    domain: str = "none"  # e.g. time, volume, flux_surface, none
    requires_vector: bool = False
    description: str = ""


REDUCTION_PATTERNS: list[ReductionPattern] = [
    ReductionPattern(
        prefix="time_average_of_",
        reduction="mean",
        domain="time",
        description="Time average of a quantity (mean over time).",
    ),
    ReductionPattern(
        prefix="root_mean_square_of_",
        reduction="rms",
        domain="none",
        description="Root mean square of a scalar quantity.",
    ),
    ReductionPattern(
        prefix="volume_integral_of_",
        reduction="integral",
        domain="volume",
        description="Volume integral of a quantity.",
    ),
    ReductionPattern(
        prefix="magnitude_of_",
        reduction="magnitude",
        requires_vector=True,
        description="Magnitude (norm) of a vector quantity.",
    ),
]


def match_reduction_pattern(name: str) -> tuple[ReductionPattern, str] | None:
    for pat in sorted(REDUCTION_PATTERNS, key=lambda p: len(p.prefix), reverse=True):
        if name.startswith(pat.prefix):
            return pat, name[len(pat.prefix) :]
    return None


def enforce_reduction_naming(
    *, name: str, reduction: str, domain: str, base: str, vector_predicate=None
) -> None:
    """Validate that the reduction provenance matches the encoded name.

    vector_predicate: optional callable(base_name)->bool to assert vector-ness.
    """
    match = match_reduction_pattern(name)
    if not match:
        return  # Name does not encode a reduction prefix; allow
    pat, detected_base = match
    if pat.reduction != reduction:
        raise ValueError(
            f"Reduction mismatch: name implies '{pat.reduction}' but provenance specifies '{reduction}'"
        )
    if pat.domain != "none" and pat.domain != domain:
        raise ValueError(
            f"Domain mismatch: name implies '{pat.domain}' but provenance specifies '{domain}'"
        )
    if detected_base != base:
        raise ValueError(
            f"Base mismatch: name encodes '{detected_base}' but provenance specifies '{base}'"
        )
    if pat.requires_vector:
        if vector_predicate and not vector_predicate(base):
            raise ValueError(
                f"Reduction '{pat.reduction}' requires vector base; '{base}' is not a vector entry"
            )


__all__ = [
    "ReductionPattern",
    "REDUCTION_PATTERNS",
    "match_reduction_pattern",
    "enforce_reduction_naming",
]
