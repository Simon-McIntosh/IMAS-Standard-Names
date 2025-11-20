"""Input and result models for vocabulary management operations.

This module defines discriminated union types for vocabulary operations,
following the same pattern as editing.edit_models.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


class AuditInput(BaseModel):
    """Audit catalog for missing vocabulary tokens."""

    action: Literal["audit"]
    vocabulary: (
        Literal[
            "components",
            "subjects",
            "geometric_bases",
            "objects",
            "positions",
            "processes",
        ]
        | None
    ) = None
    frequency_threshold: int = Field(default=3, ge=2)
    max_results: int | None = Field(default=20, ge=1)  # Limit results per vocabulary


class CheckInput(BaseModel):
    """Check if specific name would benefit from vocabulary update."""

    action: Literal["check"]
    name: str


class AddInput(BaseModel):
    """Add tokens to vocabulary."""

    action: Literal["add"]
    vocabulary: Literal[
        "components", "subjects", "geometric_bases", "objects", "positions", "processes"
    ]
    tokens: list[str]


class RemoveInput(BaseModel):
    """Remove tokens from vocabulary."""

    action: Literal["remove"]
    vocabulary: Literal[
        "components", "subjects", "geometric_bases", "objects", "positions", "processes"
    ]
    tokens: list[str]


VocabularyInput = Annotated[
    AuditInput | CheckInput | AddInput | RemoveInput,
    Field(discriminator="action"),
]

_VocabularyInputAdapter = TypeAdapter(VocabularyInput)


def parse_vocabulary_input(data: dict) -> VocabularyInput:
    """Parse raw dict into VocabularyInput."""
    return _VocabularyInputAdapter.validate_python(data)


def vocabulary_input_schema() -> dict:
    """Get JSON schema for VocabularyInput."""
    return _VocabularyInputAdapter.json_schema()


def example_vocabulary_inputs() -> list[dict]:
    """Example inputs for vocabulary operations."""
    return [
        {
            "action": "audit",
            "min_frequency": 3,
            "scope": "all",
        },
        {
            "action": "audit",
            "min_frequency": 5,
            "scope": "geometry",
        },
        {
            "action": "check",
            "name": "cross_sectional_area_of_flux_surface",
            "min_frequency": 3,
        },
        {
            "action": "add",
            "vocabulary": "geometry",
            "tokens": ["flux_surface"],
        },
        {
            "action": "remove",
            "vocabulary": "object",
            "tokens": ["deprecated_token"],
        },
    ]


# Result Models


class MissingToken(BaseModel):
    """Information about a missing vocabulary token."""

    token: str
    frequency: int
    addition_priority: Literal["high", "medium", "low", "weak"]
    affected_names: list[str]
    recommendation: str


class AuditResult(BaseModel):
    """Result of vocabulary audit operation."""

    action: Literal["audit"]
    summary: dict[
        str, int | dict[str, int]
    ]  # Missing token counts by vocabulary and priority
    recommendations: dict[
        str, list[MissingToken]
    ]  # Grouped by priority (high/medium/low)


class CheckResult(BaseModel):
    """Result of checking specific name."""

    action: Literal["check"]
    name: str
    current_parse: dict
    has_vocabulary_gap: bool
    gap_details: MissingToken | None = None


class AddResult(BaseModel):
    """Result of adding tokens."""

    action: Literal["add"]
    vocabulary: str
    added: list[str]
    already_present: list[str]
    status: Literal["success", "failed", "unchanged"]
    requires_restart: bool
    details: str | None = None


class RemoveResult(BaseModel):
    """Result of removing tokens."""

    action: Literal["remove"]
    vocabulary: str
    removed: list[str]
    not_found: list[str]
    status: Literal["success", "failed", "unchanged"]
    requires_restart: bool
    details: str | None = None


class ListResult(BaseModel):
    """Result of listing vocabulary tokens."""

    action: Literal["list"]
    vocabularies: dict  # Flexible structure from existing list_vocabulary


VocabularyResult = AuditResult | CheckResult | AddResult | RemoveResult | ListResult
