"""Unified schema module for IMAS Standard Names.

This module introduces a single, explicit data model for standard names.

Per-file YAML schema (example):
  name: ion_temperature
  kind: scalar
  status: active
  unit: eV
  description: Core ion temperature.
  tags: [core, temperature]
  constraints:
    - T_i >= 0
  validity_domain: core plasma

Vector (example):
  name: plasma_velocity
  kind: vector
  status: active
  unit: m/s
  frame: cylindrical_r_tor_z
  components:
    r: r_component_of_plasma_velocity
    tor: tor_component_of_plasma_velocity
    z: z_component_of_plasma_velocity
  magnitude: magnitude_of_plasma_velocity

Derived (operator) example:
    name: gradient_of_electron_temperature
    kind: derived_vector
    status: active
    unit: eV/m
    frame: cylindrical_r_tor_z
    components:
        r: r_component_of_gradient_of_electron_temperature
        tor: tor_component_of_gradient_of_electron_temperature
        z: z_component_of_gradient_of_electron_temperature
    provenance:
        mode: operator
        operators: [gradient]
        base: electron_temperature
        operator_id: gradient

"""

from pathlib import Path
from typing import Dict, List, Literal, Optional, Iterable, Union, Annotated
from enum import Enum
import re
import yaml
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    TypeAdapter,
)

from imas_standard_names import pint
from imas_standard_names.operators import (
    normalize_operator_chain as _normalize_operator_chain,
    enforce_operator_naming as _enforce_operator_naming,
)
from imas_standard_names.provenance import (
    OperatorProvenance,
    ExpressionProvenance,
    Provenance,
)


Kind = Literal["scalar", "derived_scalar", "vector", "derived_vector"]
Status = Literal["draft", "active", "deprecated", "superseded"]


class Frame(str, Enum):  # limited set – extend as needed
    cylindrical_r_tor_z = "cylindrical_r_tor_z"
    cartesian_x_y_z = "cartesian_x_y_z"
    spherical_r_theta_phi = "spherical_r_theta_phi"
    toroidal_R_phi_Z = "toroidal_R_phi_Z"
    flux_surface = "flux_surface"


class StandardNameBase(BaseModel):
    """Base standard name definition (fields common to all kinds).

    Pydantic discriminated union configured via 'kind'. Subclasses define literal kind values.
    """

    model_config = ConfigDict(extra="forbid")

    # core fields
    name: str
    description: str
    unit: str = ""
    status: Status = "draft"

    # Governance / metadata
    validity_domain: str = ""
    constraints: List[str] = Field(default_factory=list)
    deprecates: str = ""
    superseded_by: str = ""
    alias: str = ""
    tags: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)

    # Base validators
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("Invalid name token")
        if "__" in v:
            raise ValueError("Name must not contain double underscores")
        return v

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, v: str) -> str:
        if v in ("", "1", "none", "dimensionless"):
            return ""
        if " " in v:
            raise ValueError("Unit must not contain whitespace")
        return v

    @field_validator("tags", "links", "constraints")
    @classmethod
    def list_normalizer(cls, v: Iterable[str]) -> List[str]:  # type: ignore[override]
        if v is None:
            return []
        return [str(item).strip() for item in v if str(item).strip()]

    @model_validator(mode="after")
    def _governance_rules(self):  # type: ignore[override]
        if self.status == "deprecated" and not self.superseded_by:
            raise ValueError(
                "Deprecated entries must set superseded_by referencing an active name"
            )
        return self

    @property
    def is_dimensionless(self) -> bool:
        return self.unit == ""

    def formatted_unit(self, style: str = "plain") -> str:
        if self.is_dimensionless:
            return "1"
        if not pint:
            return self.unit
        u = pint.Unit(self.unit)
        match style:
            case "plain":
                return f"{u:~P}"
            case "pint":
                return f"{u:~F}"
            case "latex":
                return f"$`{u:L}`$"
            case _:
                raise ValueError(f"Unknown unit style: {style}")


class StandardNameScalar(StandardNameBase):
    kind: Literal["scalar"] = "scalar"
    axis: Optional[str] = None
    parent_vector: Optional[str] = None

    @model_validator(mode="after")
    def _component_rules(self):  # type: ignore[override]
        if self.axis or self.parent_vector:
            if not (self.axis and self.parent_vector):
                raise ValueError("Component scalar must define axis and parent_vector")
            expected_prefix = f"{self.axis}_component_of_"
            if not self.name.startswith(expected_prefix):
                raise ValueError(
                    f"Component scalar name must start with '{expected_prefix}'"
                )
        return self


class StandardNameDerivedScalar(StandardNameBase):
    kind: Literal["derived_scalar"] = "derived_scalar"
    provenance: Provenance
    axis: Optional[str] = None
    parent_vector: Optional[str] = None

    @model_validator(mode="after")
    def _derived_rules(self):  # type: ignore[override]
        if isinstance(self.provenance, OperatorProvenance):
            self.provenance.operators = _normalize_operator_chain(
                self.provenance.operators
            )
            _enforce_operator_naming(
                name=self.name,
                operators=self.provenance.operators,
                base=self.provenance.base,
                operator_id=self.provenance.operator_id,
                kind=self.kind,
            )
        return self


class StandardNameVector(StandardNameBase):
    kind: Literal["vector"] = "vector"
    frame: Frame
    components: Dict[str, str]
    magnitude: Optional[str] = None

    @model_validator(mode="after")
    def _vector_rules(self):  # type: ignore[override]
        if len(self.components) < 2:
            raise ValueError("Vector requires >=2 components")
        for axis, comp in self.components.items():
            if not re.match(r"^[a-z][a-z0-9_]*$", axis):
                raise ValueError(f"Invalid axis token: {axis}")
            expected_prefix = f"{axis}_component_of_"
            if not comp.startswith(expected_prefix):
                raise ValueError(
                    f"Component '{comp}' must start with '{expected_prefix}'"
                )
        if self.magnitude:
            expected_mag = f"magnitude_of_{self.name}"
            if self.magnitude != expected_mag:
                raise ValueError(
                    f"Magnitude must be named '{expected_mag}', got '{self.magnitude}'"
                )
        return self


class StandardNameDerivedVector(StandardNameBase):
    kind: Literal["derived_vector"] = "derived_vector"
    frame: Frame
    components: Dict[str, str]
    magnitude: Optional[str] = None
    provenance: Provenance

    @model_validator(mode="after")
    def _derived_vector_rules(self):  # type: ignore[override]
        if len(self.components) < 2:
            raise ValueError("Vector requires >=2 components")
        for axis, comp in self.components.items():
            if not re.match(r"^[a-z][a-z0-9_]*$", axis):
                raise ValueError(f"Invalid axis token: {axis}")
            expected_prefix = f"{axis}_component_of_"
            if not comp.startswith(expected_prefix):
                raise ValueError(
                    f"Component '{comp}' must start with '{expected_prefix}'"
                )
        if self.magnitude:
            expected_mag = f"magnitude_of_{self.name}"
            if self.magnitude != expected_mag:
                raise ValueError(
                    f"Magnitude must be named '{expected_mag}', got '{self.magnitude}'"
                )
        if isinstance(self.provenance, OperatorProvenance):
            self.provenance.operators = _normalize_operator_chain(
                self.provenance.operators
            )
            _enforce_operator_naming(
                name=self.name,
                operators=self.provenance.operators,
                base=self.provenance.base,
                operator_id=self.provenance.operator_id,
                kind=self.kind,
            )
        return self


StandardName = Annotated[
    Union[
        StandardNameScalar,
        StandardNameDerivedScalar,
        StandardNameVector,
        StandardNameDerivedVector,
    ],
    Field(discriminator="kind"),
]

_STANDARD_NAME_ADAPTER = TypeAdapter(StandardName)


def create_standard_name(data: Dict) -> StandardName:
    """Validate data into the appropriate StandardName subclass via discriminator."""
    return _STANDARD_NAME_ADAPTER.validate_python(data)


# ----------------------------------------------------------------------------
# Catalog loader / persister
# ----------------------------------------------------------------------------


def load_standard_name_file(path: Path) -> StandardName:
    """Load a single per-file standard name YAML.

    Expected structure is a flat mapping with required 'name' key.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict) or "name" not in data:
        raise ValueError(
            f"File {path} must contain a flat mapping with a 'name' field (no aggregated legacy format)."
        )
    return create_standard_name(data)


def load_catalog(root: Path) -> Dict[str, StandardName]:
    entries: Dict[str, StandardName] = {}
    for file in sorted(root.rglob("*.yml")) + sorted(root.rglob("*.yaml")):
        if file.is_dir():
            continue
        entry = load_standard_name_file(file)
        if entry.name in entries:
            raise ValueError(f"Duplicate standard name '{entry.name}' in {file}")
        entries[entry.name] = entry
    return entries


def save_standard_name(entry: StandardNameBase, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{entry.name}.yml"
    data = {k: v for k, v in entry.model_dump().items() if v not in (None, [], "")}
    data["name"] = entry.name  # ensure name present
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return path


__all__ = [
    "Kind",
    "Status",
    "Frame",
    "OperatorProvenance",
    "ExpressionProvenance",
    "Provenance",
    "StandardNameBase",
    "StandardNameScalar",
    "StandardNameDerivedScalar",
    "StandardNameVector",
    "StandardNameDerivedVector",
    "StandardName",
    "StandardName",
    "create_standard_name",
    "load_standard_name_file",
    "load_catalog",
    "save_standard_name",
]
