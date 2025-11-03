"""Static StandardName model and friendly wrappers.

This module holds the hand-written Pydantic model and thin compose/parse
wrappers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from imas_standard_names.grammar.constants import (
    EXCLUSIVE_SEGMENT_PAIRS,
    GENERIC_PHYSICAL_BASES,
)
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
    Subject,
)

# BaseToken: pattern for physical_base segment (open vocabulary)
TOKEN_PATTERN_STR = r"^[a-z][a-z0-9_]*$"
BaseToken = Annotated[
    str,
    Field(
        description=(
            "Base segment token (root of a standard name); snake_case token "
            "matching ^[a-z][a-z0-9_]*$. Examples: 'temperature', 'density', "
            "'magnetic_field', 'particle_flux'."
        ),
        pattern=TOKEN_PATTERN_STR,
        examples=["temperature", "density", "magnetic_field", "particle_flux"],
    ),
]


class StandardName(BaseModel):
    """Structured representation of a standard name."""

    model_config = ConfigDict(extra="forbid")

    component: Component | None = None
    coordinate: Component | None = None
    subject: Subject | None = None
    device: Object | None = None
    geometric_base: GeometricBase | None = None
    physical_base: BaseToken | None = None
    object: Object | None = None
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

    @model_validator(mode="after")
    def _check_generic_physical_base(self) -> StandardName:
        """Validate that generic physical bases have required qualification.

        Generic physical bases (area, current, power, temperature, voltage, etc.)
        are too generic to stand alone and must be qualified with subject, device,
        object, position, or geometry context.

        Examples of invalid names:
            - current (too generic)
            - temperature (too generic)
            - voltage (too generic)

        Examples of valid names:
            - plasma_current (implicit object context)
            - electron_temperature (subject qualifier)
            - poloidal_field_coil_current (device qualifier)
            - poloidal_magnetic_field_probe_voltage (device qualifier)
            - area_of_flux_loop (object qualifier)
            - pressure_at_magnetic_axis (position qualifier)
        """
        if self.physical_base and self.physical_base in GENERIC_PHYSICAL_BASES:
            # Check if ANY qualifying segment is present
            has_qualification = any(
                [
                    self.subject,
                    self.device,
                    self.object,
                    self.position,
                    self.geometry,
                ]
            )

            if not has_qualification:
                msg = (
                    f"Generic physical_base '{self.physical_base}' requires qualification. "
                    f"Generic terms like '{self.physical_base}' are ambiguous without context. "
                    f"Add a qualifying segment: subject (e.g., electron_), device (e.g., flux_loop_), "
                    f"object (e.g., of_flux_loop), position (e.g., at_magnetic_axis), "
                    f"or geometry (e.g., of_plasma_boundary)."
                )
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
