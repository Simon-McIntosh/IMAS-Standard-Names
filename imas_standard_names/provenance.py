"""Provenance models for IMAS Standard Names.

These models define how derived standard names record their origin either via an
operator chain or an expression.
"""

from __future__ import annotations

from typing import List, Optional, Union, Annotated, Literal
import re
from pydantic import BaseModel, Field, field_validator


class OperatorProvenance(BaseModel):
    """Provenance describing a chain of operators applied to a base quantity.

    Fields
    ------
    mode: Literal["operator"] discriminator.
    operators: Outermost-first sequence of primitive operator tokens, already
        normalized (composite operators expanded) by the schema validator.
    base: The underlying primitive standard name (scalar or vector) to which
        the operators are applied.
    operator_id: Optional composite operator identifier (e.g. 'laplacian',
        'second_time_derivative') if the user supplied one in the catalog. It
        is not required and may be omitted if only primitive operators were
        used. Validation does not derive this value; it simply preserves what
        was provided for round-tripping / governance checks.
    """

    mode: Literal["operator"] = "operator"
    operators: List[str] = Field(min_length=1)
    base: str
    operator_id: Optional[str] = None

    @field_validator("operators")
    @classmethod
    def validate_ops(cls, ops: List[str]) -> List[str]:
        for o in ops:
            if not re.match(r"^[a-z_][a-z0-9_]*$", o):
                raise ValueError(f"Invalid operator token: {o}")
        return ops

    @field_validator("base")
    @classmethod
    def validate_base(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"Invalid base token: {v}")
        return v


class ExpressionProvenance(BaseModel):
    """Provenance describing an algebraic expression of existing names.

    Fields
    ------
    mode: Literal["expression"] discriminator.
    expression: Free-form (but catalog-governed) expression string.
    dependencies: List of standard name identifiers referenced by the
        expression (used for dependency graph construction / validation).
    """

    mode: Literal["expression"] = "expression"
    expression: str
    dependencies: List[str] = Field(min_length=1)

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, deps: List[str]) -> List[str]:
        for d in deps:
            if not re.match(r"^[a-z][a-z0-9_]*$", d):
                raise ValueError(f"Invalid dependency token: {d}")
        return deps


class ReductionProvenance(BaseModel):
    """Provenance describing a standardized reduction / aggregation.

    Fields
    ------
    mode: Literal["reduction"] discriminator.
    reduction: canonical reduction id (mean, rms, integral, magnitude, ...)
    domain: contextual domain for the reduction (time, volume, flux_surface, none)
    base: underlying standard name being reduced.
    """

    mode: Literal["reduction"] = "reduction"
    reduction: str
    domain: str = "none"
    base: str

    @field_validator("base")
    @classmethod
    def validate_base(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"Invalid base token: {v}")
        return v


Provenance = Annotated[
    Union[OperatorProvenance, ExpressionProvenance, ReductionProvenance],
    Field(discriminator="mode"),
]

__all__ = [
    "OperatorProvenance",
    "ExpressionProvenance",
    "ReductionProvenance",
    "Provenance",
]
