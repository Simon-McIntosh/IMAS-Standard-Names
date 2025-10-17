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
            "Unit in fused dot-exponent style (auto-corrected to lexicographic token order). "
            "Tokens: alphanumerics only; join with '.'; exponents use ^ (e.g. m.s^-2). "
            "No '/', '*', or whitespace. Empty string for dimensionless. "
            "Units are automatically reordered to canonical form (e.g., 's^-2.m' -> 'm.s^-2')."
        ),
        pattern=UNIT_PATTERN,
        examples=["eV", "m", "m.s^-1", "A.m^-2", "m^-3"],
    ),
]

# Tags: list[str] with controlled vocabulary validation
# First element (tags[0]) must be a primary tag (validated in models.py)
# Remaining elements (tags[1:]) are secondary tags (validated in models.py)
# See grammar/vocabularies/tags.yml for complete controlled vocabulary
Tags = Annotated[
    list[str],
    Field(
        description=(
            "Classification keywords from controlled vocabulary. "
            "First element (tags[0]) must be a primary tag defining catalog subdirectory. "
            "Remaining elements (tags[1:]) are secondary tags for cross-cutting classification. "
            "Validated against grammar/vocabularies/tags.yml."
        ),
        examples=[
            ["fundamental", "time-dependent", "measured"],
            ["equilibrium", "steady-state", "reconstructed"],
            ["core-physics", "spatial-profile"],
        ],
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
        description=(
            "One concise sentence summarizing the physical quantity. "
            "Keep under 120 characters for readability. "
            "Should be self-contained and understandable without external context. "
            "Avoid: repeating the name verbatim, referencing IMAS Data Dictionary (DD), "
            "COCOS conventions, or implementation-specific paths."
        ),
        max_length=180,
    ),
]

Documentation = Annotated[
    str,
    Field(
        description=(
            "Authoritative, self-contained documentation providing clear, comprehensive explanation of the physical quantity. "
            "This field must be fully standalone - a domain expert should understand the quantity completely without "
            "consulting external sources. "
            "\n\n"
            "MUST include: (1) Physical interpretation and governing physics, (2) Governing equations with full definitions, "
            "(3) Measurement or derivation methods, (4) Typical values and physical ranges, (5) Coordinate system definitions "
            "and sign conventions (if applicable), (6) Relationships to other quantities with explicit equations. "
            "\n\n"
            "Format requirements: Use Markdown for structure. Use LaTeX for ALL equations - inline $...$ or display $$...$$. "
            "Examples: Faraday's law $V = -N A \\frac{dB}{dt}$, flux $\\Phi = \\int \\mathbf{B} \\cdot d\\mathbf{A}$, "
            "Ampère's law $$\\nabla \\times \\mathbf{B} = \\mu_0 \\mathbf{J}$$. "
            "Wrap text to ~80 characters per line when used in YAML block scalars (|). "
            "\n\n"
            "AVOID: (1) References to IMAS Data Dictionary (DD) paths or structure, (2) References to COCOS conventions "
            "(define sign conventions explicitly instead), (3) Statements like 'see IMAS documentation' or 'refer to [external source]', "
            "(4) Implementation-specific details, (5) Vague terms without explicit definitions. "
            "\n\n"
            "When deriving from IMAS DD: extract and expand the physics content, making it standalone. Define all coordinate "
            "systems and sign conventions explicitly within the documentation text."
        ),
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
