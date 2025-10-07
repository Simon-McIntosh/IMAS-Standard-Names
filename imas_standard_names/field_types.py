"""Reusable Annotated field type aliases for standard name models.

This module isolates the simple field-level semantics (patterns, short
explanations, example values) from the structural Pydantic models defined in
`models.py`. Keeping these aliases here reduces cognitive load in `models.py`
and allows other tooling (CLI helpers, docs generators) to reuse the same
constraints without importing the full discriminated union types.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

# ---------------------------------------------------------------------------
# Patterns (kept simple; complex constraints handled by validators in models)
# ---------------------------------------------------------------------------
STANDARD_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
UNIT_PATTERN = r"^[A-Za-z0-9]+(\^[+-]?\d+)?(\.[A-Za-z0-9]+(\^[+-]?\d+)?)*$|^$"

# ---------------------------------------------------------------------------
# Annotated aliases
# ---------------------------------------------------------------------------
Name = Annotated[
    str,
    Field(
        description=(
            "Standard name token: snake_case (^[a-z][a-z0-9_]*$); starts with a letter; no double '__'."
        ),
        pattern=STANDARD_NAME_PATTERN,
        examples=[
            "electron_temperature",
            "gradient_of_electron_temperature",
            "toroidal_component_of_magnetic_field",
        ],
    ),
]

Unit = Annotated[
    str,
    Field(
        description=(
            "Unit in fused dot-exponent style (lexicographic token order). "
            "Tokens: alphanumerics only; join with '.'; exponents use ^ (e.g. m.s^-2). "
            "No '/', '*', or whitespace. Empty string for dimensionless."
        ),
        pattern=UNIT_PATTERN,
        examples=["eV", "m", "m.s^-1", "A.m^-2", "m^-3"],
    ),
]

Tags = Annotated[
    list[str],
    Field(
        description="Classification keywords (lowercase tokens).",
        examples=[["core", "temperature"], ["equilibrium"]],
    ),
]

Links = Annotated[
    list[str],
    Field(
        description="External reference links (URLs, issues, docs).",
        examples=[
            ["https://example.org/spec"],
            ["https://github.com/org/repo/issues/12"],
        ],
    ),
]

Constraints = Annotated[
    list[str],
    Field(
        description="Symbolic or textual constraints (e.g. 'T_i >= 0').",
        examples=[["T_i >= 0"]],
    ),
]

Description = Annotated[
    str,
    Field(
        description="One concise sentence (<=120 chars) summarizing the quantity.",
        max_length=180,
    ),
]

Documentation = Annotated[
    str,
    Field(
        description="Extended multi-line rationale / details (may be blank).",
    ),
]

Domain = Annotated[
    str,
    Field(
        description="Controlled vocabulary region of validity.",
        examples=[["core_plasma"], ["edge_plasma"], ["vacuum"], ["whole_plasma"]],
    ),
]

# ---------------------------------------------------------------------------
# Base token (root segment) used by grammar.StandardName.base
# ---------------------------------------------------------------------------
BaseToken = Annotated[
    str,
    Field(
        description=(
            "Base segment token (root of a standard name); snake_case token "
            "matching ^[a-z][a-z0-9_]*$. Examples: 'temperature', 'density', "
            "'magnetic_field', 'particle_flux'."
        ),
        pattern=STANDARD_NAME_PATTERN,
        examples=["temperature", "density", "magnetic_field", "particle_flux"],
    ),
]


__all__ = [
    "STANDARD_NAME_PATTERN",
    "UNIT_PATTERN",
    "Name",
    "Unit",
    "Tags",
    "Links",
    "Constraints",
    "Description",
    "Documentation",
    "Domain",
    "BaseToken",
]
