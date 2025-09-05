"""Unified Pydantic models for the standard name catalog schema.

Schema Overview (per file):

Common Fields:
  name: str
  kind: scalar | derived_scalar | vector | derived_vector
  unit: str (SI unit or blank for dimensionless)
  status: draft | active | deprecated | superseded
  description: str
  tags: list[str] (optional)
  links: list[str] (optional)

Vector / Derived Vector Fields:
  frame: str (required)
  components: dict[axis -> component_name]  (>=2 for vector kinds)
  magnitude: str (optional scalar standard name)
  parent_operation: {operator: str, operand_vector: str} (derived vectors)

Component Scalars (both base & derived) may include:
  axis: str (required if this scalar is a component of a vector)
  parent_vector: str (required if axis present)

Derived Scalars:
  parent_operation: {operator: str, operand_vector: str} (if produced by operator)
  derivation: {expression: str, dependencies: list[str]} (if expression defined)

Validation enforces structural consistency but defers deep operator chain
semantics to the external validator script for now.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, model_validator, field_validator
import yaml
import re


Kind = Literal["scalar", "derived_scalar", "vector", "derived_vector"]
Status = Literal["draft", "active", "deprecated", "superseded"]


class ParentOperation(BaseModel):
    operator: str
    operand_vector: str

    @field_validator("operator")
    @classmethod
    def operator_token(cls, v: str) -> str:
        """Validate operator token structure (lowercase identifier)."""
        if not re.match(r"^[a-z_][a-z0-9_]*$", v):
            raise ValueError(f"Invalid operator token: {v}")
        return v


class Derivation(BaseModel):
    expression: str
    dependencies: List[str] = Field(default_factory=list)

    @field_validator("dependencies")
    @classmethod
    def non_empty_names(cls, v: List[str]) -> List[str]:
        """Ensure each dependency name matches the required token pattern."""
        for name in v:
            if not re.match(r"^[a-z][a-z0-9_]*$", name):
                raise ValueError(f"Invalid dependency name: {name}")
        return v


class BaseEntry(BaseModel):
    name: str
    kind: Kind
    unit: str
    status: Status = "draft"
    description: str
    tags: List[str] | None = None
    links: List[str] | None = None

    # Component / relationship fields (subset used depending on kind)
    frame: Optional[str] = None
    components: Optional[Dict[str, str]] = None
    magnitude: Optional[str] = None
    parent_operation: Optional[ParentOperation] = None
    axis: Optional[str] = None
    parent_vector: Optional[str] = None
    derivation: Optional[Derivation] = None

    class Config:
        allow_population_by_field_name = True
        extra = "forbid"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate standard name token rules."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "Name must be lowercase, start with letter, contain only a-z0-9_."
            )
        if "__" in v:
            raise ValueError("Name must not contain double underscores.")
        return v

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        """Basic unit string sanity (blank, '1', or compact SI-like tokens)."""
        if v == "" or v == "1":
            return v
        if " " in v:
            raise ValueError(
                "Unit must not contain whitespace; use '.' for multiplication."
            )
        return v

    @model_validator(mode="after")
    def structural_rules(self):  # type: ignore[override]
        # Vector-specific checks
        if self.kind in {"vector", "derived_vector"}:
            if not self.frame:
                raise ValueError("Vector kinds require 'frame'.")
            if not self.components or len(self.components) < 2:
                raise ValueError("Vector kinds require >=2 components.")
            # Component name pattern sanity
            for axis, comp in self.components.items():
                if not re.match(r"^[a-z][a-z0-9_]*$", axis):
                    raise ValueError(f"Invalid axis token: {axis}")
                expected_prefix = f"{axis}_component_of_"
                if not comp.startswith(expected_prefix):
                    raise ValueError(
                        f"Component '{comp}' must start with '{expected_prefix}'."
                    )
            if self.magnitude:
                expected_mag = f"magnitude_of_{self.name}"
                if self.magnitude != expected_mag:
                    raise ValueError(
                        f"Vector '{self.name}': magnitude must be named '{expected_mag}', got '{self.magnitude}'."
                    )
            if self.kind == "derived_vector" and not self.parent_operation:
                raise ValueError(
                    "Derived vector requires 'parent_operation' (operator + operand_vector)."
                )

        # Component scalar checks
        if self.axis or self.parent_vector:
            if not (self.axis and self.parent_vector):
                raise ValueError(
                    "Component scalar must specify both 'axis' and 'parent_vector'."
                )
            if self.kind not in {"scalar", "derived_scalar"}:
                raise ValueError("Only scalar kinds may be vector components.")
            # Pattern confirm
            expected = f"{self.axis}_component_of_"
            if not self.name.startswith(expected):
                raise ValueError(
                    f"Component name '{self.name}' must start with '{expected}'."
                )

        # Derived scalar/vector provenance: always require derivation or parent_operation (no suffix-based exceptions)
        if self.kind.startswith("derived_") and not (
            self.derivation or self.parent_operation
        ):
            raise ValueError(
                "Derived kinds must define 'derivation' or 'parent_operation'."
            )

        # Enforce new magnitude naming for derived scalar magnitudes
        if (
            self.kind == "derived_scalar"
            and self.parent_vector
            and self.name.startswith("magnitude_of_")
        ):
            expected_mag_scalar = f"magnitude_of_{self.parent_vector}"
            if self.name != expected_mag_scalar:
                raise ValueError(
                    f"Magnitude scalar name mismatch: expected '{expected_mag_scalar}', got '{self.name}'."
                )
        # Hard cut: reject legacy suffix names
        if self.name.endswith("_magnitude") and not self.name.startswith(
            "magnitude_of_"
        ):
            raise ValueError(
                f"Deprecated magnitude naming '{self.name}'. Use 'magnitude_of_<vector>'."
            )

        # Derivation consistency
        if self.derivation:
            if not self.derivation.dependencies:
                raise ValueError("Derivation must list dependencies.")
        return self


CatalogEntry = BaseEntry  # Alias for clarity


def load_entry(path: Path) -> CatalogEntry:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Expect flat key map
    return CatalogEntry(**data)


def load_catalog(root: Path) -> Dict[str, CatalogEntry]:
    """Load all YAML entries under a directory tree.

    Expects files matching `**/*.yml` or `**/*.yaml` under `root`.
    Skips empty files. Deduplicates by `name`.
    """
    entries: Dict[str, CatalogEntry] = {}
    for path in list(root.rglob("*.yml")) + list(root.rglob("*.yaml")):
        if path.is_dir():
            continue
        try:
            entry = load_entry(path)
        except Exception as e:  # pragma: no cover (defensive)
            raise RuntimeError(f"Failed to load {path}: {e}") from e
        if entry.name in entries:
            raise ValueError(
                f"Duplicate standard name '{entry.name}' defined in {path} and {entries[entry.name]}"
            )
        entries[entry.name] = entry
    return entries


__all__ = [
    "CatalogEntry",
    "BaseEntry",
    "ParentOperation",
    "Derivation",
    "load_entry",
    "load_catalog",
]
