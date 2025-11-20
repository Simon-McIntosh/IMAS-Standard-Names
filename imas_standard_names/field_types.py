"""Reusable Annotated field type aliases for standard name models.

This module isolates the simple field-level semantics (patterns, short
explanations, example values) from the structural Pydantic models defined in
`models.py`. Keeping these aliases here reduces cognitive load in `models.py`
and allows other tooling (CLI helpers, docs generators) to reuse the same
constraints without importing the full discriminated union types.

Field descriptions and constraints are generated from specification.yml
via grammar_codegen to ensure single source of truth.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from imas_standard_names.grammar.field_schemas import (
    FIELD_CONSTRAINTS,
    FIELD_DESCRIPTIONS,
)

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
        description=FIELD_DESCRIPTIONS["name"],
        pattern=STANDARD_NAME_PATTERN,
        examples=FIELD_CONSTRAINTS["name"]["examples"],
    ),
]

Unit = Annotated[
    str,
    Field(
        description=FIELD_DESCRIPTIONS["unit"],
        pattern=UNIT_PATTERN,
        examples=FIELD_CONSTRAINTS["unit"]["examples"],
    ),
]

# Tags: list[str] with controlled vocabulary validation
# First element (tags[0]) must be a primary tag (validated in models.py)
# Remaining elements (tags[1:]) are secondary tags (validated in models.py)
# See grammar/vocabularies/tags.yml for complete controlled vocabulary
Tags = Annotated[
    list[str],
    Field(
        description=FIELD_DESCRIPTIONS["tags"],
    ),
]

Links = Annotated[
    list[str],
    Field(
        description=FIELD_DESCRIPTIONS["links"],
    ),
]

Constraints = Annotated[
    list[str],
    Field(
        description=FIELD_DESCRIPTIONS["constraints"],
        examples=FIELD_CONSTRAINTS["constraints"]["examples"],
    ),
]

Description = Annotated[
    str,
    Field(
        description=FIELD_DESCRIPTIONS["description"],
        max_length=FIELD_CONSTRAINTS["description"]["max_length"],
    ),
]

Documentation = Annotated[
    str,
    Field(
        description=FIELD_DESCRIPTIONS["documentation"],
    ),
]

Domain = Annotated[
    str,
    Field(
        description=FIELD_DESCRIPTIONS["validity_domain"],
        examples=FIELD_CONSTRAINTS["validity_domain"]["examples"],
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
]
