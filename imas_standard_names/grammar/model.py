"""Static StandardName model and friendly wrappers.

This module holds the hand-written Pydantic model and thin compose/parse
wrappers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from imas_standard_names.field_types import BaseToken
from imas_standard_names.grammar.constants import EXCLUSIVE_SEGMENT_PAIRS
from imas_standard_names.grammar.support import (
    TOKEN_PATTERN,
    compose_standard_name as _compose_from_parts,
    parse_standard_name as _parse_to_dict,
    value_of as _value_of,
)
from imas_standard_names.grammar.types import (
    Component,
    GeometricBase,
    Object,
    Position,
    Process,
    Source,
    Subject,
)


class StandardName(BaseModel):
    """Structured representation of a standard name."""

    model_config = ConfigDict(extra="forbid")

    component: Component | None = None
    coordinate: Component | None = None
    subject: Subject | None = None
    geometric_base: GeometricBase | None = None
    physical_base: BaseToken | None = None
    object: Object | None = None
    source: Source | None = None
    geometry: Position | None = None
    position: Position | None = None
    process: Process | None = None

    @field_validator("physical_base")
    @classmethod
    def _validate_physical_base(cls, value: str | None) -> str | None:
        if value is not None and not TOKEN_PATTERN.fullmatch(value):
            msg = "physical_base segment must match the canonical token pattern"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _check_exclusive(self) -> StandardName:
        for left, right in EXCLUSIVE_SEGMENT_PAIRS:
            if getattr(self, left, None) and getattr(self, right, None):
                msg = f"Segments '{left}' and '{right}' cannot both be set"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_base_required(self) -> StandardName:
        if self.geometric_base is None and self.physical_base is None:
            msg = "Either geometric_base or physical_base must be set"
            raise ValueError(msg)
        return self

    def compose(self) -> str:
        return _compose_from_parts(self.model_dump_compact())

    def model_dump_compact(self) -> dict[str, str]:
        return {
            key: _value_of(value)
            for key, value in self.model_dump().items()
            if value is not None
        }


def compose_standard_name(parts: Mapping[str, Any] | StandardName) -> str:
    if isinstance(parts, StandardName):
        payload = parts.model_dump_compact()
    else:
        payload = StandardName.model_validate(parts).model_dump_compact()
    return _compose_from_parts(payload)


def parse_standard_name(name: str) -> StandardName:
    values = _parse_to_dict(name)
    return StandardName.model_validate(values)


__all__ = [
    "StandardName",
    "compose_standard_name",
    "parse_standard_name",
]
