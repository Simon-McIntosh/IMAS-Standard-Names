"""Operator registry, parsing, normalization and naming enforcement.

This module defines operator patterns describing leading name prefixes for
derived standard names (e.g. gradient_of_, time_derivative_of_, etc.). It
supports reconstructing the primitive operator chain (outermost-first) from a
name and validating supplied provenance.

Composite operator ids (e.g. second_time_derivative) expand into primitive
chains (time_derivative, time_derivative). Provided provenance 'operators'
must always contain only primitive tokens.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OperatorPattern(BaseModel):
    operator_id: str  # canonical id (may be composite)
    primitive_chain: list[str] = Field(min_length=1)  # outermost-first
    result_kind: str | None = None  # scalar / vector or None
    operand_format: str = Field(default="{suffix}")  # build expected base token
    description: str = ""

    @property
    def prefix(self) -> str:
        return f"{self.operator_id}_of_"

    def expected_operand(self, suffix: str) -> str:
        return self.operand_format.format(suffix=suffix)


# Primitive tokens (extend as needed)
PRIMITIVE_OPERATORS = {"gradient", "time_derivative", "divergence", "curl", "laplacian"}

# Ordered patterns (specific first)
OPERATOR_PATTERNS: list[OperatorPattern] = [
    OperatorPattern(
        operator_id="second_time_derivative",
        primitive_chain=["time_derivative", "time_derivative"],
        result_kind=None,
        description="Second time derivative (two successive time derivatives).",
    ),
    OperatorPattern(
        operator_id="gradient",
        primitive_chain=["gradient"],
        result_kind="vector",
        description="Spatial gradient (vector result).",
    ),
    OperatorPattern(
        operator_id="time_derivative",
        primitive_chain=["time_derivative"],
        result_kind=None,
        description="First time derivative.",
    ),
    OperatorPattern(
        operator_id="divergence",
        primitive_chain=["divergence"],
        result_kind="scalar",
        description="Divergence (scalar result).",
    ),
    OperatorPattern(
        operator_id="curl",
        primitive_chain=["curl"],
        result_kind="vector",
        description="Curl (vector result).",
    ),
    OperatorPattern(
        operator_id="laplacian",
        primitive_chain=["laplacian"],
        result_kind="scalar",
        description="Laplacian (scalar result).",
    ),
]


def match_operator_pattern(name: str) -> tuple[OperatorPattern, str] | None:
    # Ensure longer prefixes (composite ids) match first
    for pattern in sorted(OPERATOR_PATTERNS, key=lambda p: len(p.prefix), reverse=True):
        pref = pattern.prefix
        if name.startswith(pref):
            return pattern, name[len(pref) :]
    return None


def parse_operator_chain(name: str) -> tuple[list[str], str, list[OperatorPattern]]:
    """Peel operator prefixes recursively.

    Returns (primitive_chain, base, patterns_encountered_outermost_first).
    """
    chain: list[str] = []
    patterns: list[OperatorPattern] = []
    remaining = name
    while True:
        m = match_operator_pattern(remaining)
        if not m:
            break
        pattern, suffix = m
        patterns.append(pattern)
        chain.extend(pattern.primitive_chain)
        remaining = suffix
    return chain, remaining, patterns


def normalize_operator_chain(operators: list[str]) -> list[str]:
    """Validate operators are primitive tokens and return them (outermost-first)."""
    for op in operators:
        if op not in PRIMITIVE_OPERATORS:
            raise ValueError(
                f"Operator '{op}' is not a primitive token; omit composite ids in operators list"
            )
    return operators


def enforce_operator_naming(
    *,
    name: str,
    operators: list[str],
    base: str,
    operator_id: str | None,
    kind: str,
) -> None:
    """Validate consistency of supplied operator provenance with name.

    - Reconstruct chain + base from name
    - Ensure primitive chain equality
    - Ensure base match
    - Ensure kind consistency (last non-null result_kind wins)
    - Ensure operator_id (if supplied) matches outermost pattern
    """
    chain, detected_base, patterns = parse_operator_chain(name)
    if not patterns:
        return  # Name does not encode a recognized operator prefix; allow
    if base != detected_base:
        raise ValueError(
            f"Provenance base mismatch: expected '{detected_base}' from name, got '{base}'"
        )
    if operators != chain:
        raise ValueError(
            f"Operator chain mismatch for '{name}': expected {chain}, got {operators}"
        )
    expected_kind = None
    for pat in patterns:
        if pat.result_kind:
            expected_kind = pat.result_kind
    if expected_kind and kind != expected_kind:
        raise ValueError(
            f"Kind mismatch: naming implies {expected_kind} but entry is {kind}"
        )
    if operator_id and operator_id != patterns[0].operator_id:
        raise ValueError(
            f"operator_id '{operator_id}' does not match outermost pattern '{patterns[0].operator_id}'"
        )


__all__ = [
    "OperatorPattern",
    "OPERATOR_PATTERNS",
    "match_operator_pattern",
    "parse_operator_chain",
    "normalize_operator_chain",
    "enforce_operator_naming",
]
