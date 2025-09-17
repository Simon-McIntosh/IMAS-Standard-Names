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

from typing import Dict, List, Literal, Iterable, Union, Annotated
from enum import Enum
import re
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
    ReductionProvenance,
)
from imas_standard_names.reductions import enforce_reduction_naming
from imas_standard_names.field_types import (
    Name,
    Unit,
    Tags,
    Links,
    Constraints,
    Description,
    Documentation,
    Domain,
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

    Pydantic discriminated union configured via 'kind'. Subclasses define
    literal kind values. All fields are explicitly annotated with concise
    descriptions for downstream documentation / tooling generation.
    """

    model_config = ConfigDict(extra="forbid")

    # Core identification & description
    name: Name
    description: Description
    documentation: Documentation = ""
    unit: Unit = ""
    status: Status = Field(
        "draft",
        description="Lifecycle state: draft | active | deprecated | superseded.",
    )

    # Governance / metadata
    validity_domain: Domain = ""
    constraints: Constraints = Field(default_factory=list)
    deprecates: Name | str = ""
    superseded_by: Name | str = ""
    tags: Tags = Field(default_factory=list)
    links: Links = Field(default_factory=list)

    # Supplemental validator for double underscore rule not expressible in pattern.
    @field_validator("name", "deprecates", "superseded_by")
    @classmethod
    def _no_double_underscore(cls, v: str) -> str:  # type: ignore[override]
        if v and "__" in v:
            raise ValueError("Name tokens must not contain double underscores")
        return v

    # Base validators
    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, v: str) -> str:
        # Dimensionless synonyms collapse to empty string.
        if v in ("", "1", "none", "dimensionless"):
            return ""
        if " " in v:
            raise ValueError("Unit must not contain whitespace")
        if "/" in v or "*" in v:
            raise ValueError(
                "Use dot-exponent style (e.g. m.s^-2); '/' and '*' are forbidden"
            )

        # Syntactic canonicalization performed without expanding symbols to their
        # long names (pint would expand 'm' -> 'meter', etc.), because we want
        # authors to write the concise symbols and we want to preserve those as
        # the canonical storage form. We still optionally validate that each
        # symbol is a known pint unit if pint is available, but we compare using
        # the author-supplied symbols.
        token_re = re.compile(r"^([A-Za-z0-9]+)(\^([+-]?\d+))?$")
        parts_raw = v.split(".")
        parsed: list[tuple[str, int]] = []
        for part in parts_raw:
            m = token_re.match(part)
            if not m:
                raise ValueError(f"Invalid unit token '{part}' in '{v}'")
            sym = m.group(1)
            exp = int(m.group(3) or 1)
            if exp == 0:
                # Zero exponents are meaningless – reject to avoid silent drops.
                raise ValueError(f"Zero exponent not allowed in unit token '{part}'")
            parsed.append((sym, exp))

        # Lexicographic ordering of symbols defines canonical order.
        canonical = ".".join(
            sym if exp == 1 else f"{sym}^{exp}"
            for sym, exp in sorted(parsed, key=lambda x: x[0])
        )
        if canonical != v:
            raise ValueError(f"Unit '{v}' not canonical; expected '{canonical}'")

        # Optional semantic validation via pint (best-effort). We allow tokens that
        # pint can resolve individually; we do not reconstruct expansion names.
        if pint:
            try:
                # Full parse ensures combined dimensional validity (e.g. catches typos).
                pint.Unit(v)
            except Exception as e:  # pragma: no cover - defensive
                raise ValueError(f"Invalid unit '{v}': {e}") from e
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
                # Plain style now uses pint's pretty (~P) for human readability
                # (may produce Unicode superscripts or ASCII fallbacks)
                s = f"{u:~P}"
                return s.replace("·", "/")  # preserve legacy visual slash style
            case "dotexp":
                # Canonical fused dot-exponent short-symbol format
                return f"{u:~F}"
            case "latex":
                return f"$`{u:L}`$"
            case _:
                raise ValueError(f"Unknown unit style: {style}")


class StandardNameScalar(StandardNameBase):
    kind: Literal["scalar"] = "scalar"


class StandardNameDerivedScalar(StandardNameBase):
    kind: Literal["derived_scalar"] = "derived_scalar"
    provenance: Provenance

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
        if isinstance(self.provenance, ReductionProvenance):
            enforce_reduction_naming(
                name=self.name,
                reduction=self.provenance.reduction,
                domain=self.provenance.domain,
                base=self.provenance.base,
            )
        return self


class StandardNameVector(StandardNameBase):
    kind: Literal["vector"] = "vector"
    frame: Frame = Field(..., description="Reference frame / coordinate system.")
    components: Dict[str, str] = Field(
        ..., description="Mapping axis -> component standard name."
    )

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
        return self

    @property
    def magnitude(self) -> str:
        """Derived magnitude standard name (not a stored field).

        Conventionally 'magnitude_of_<vector_name>'. Presence as an entry in
        the catalog is optional and validated elsewhere if defined.
        """
        return f"magnitude_of_{self.name}"


class StandardNameDerivedVector(StandardNameBase):
    kind: Literal["derived_vector"] = "derived_vector"
    frame: Frame = Field(..., description="Reference frame / coordinate system.")
    components: Dict[str, str] = Field(
        ..., description="Mapping axis -> component standard name."
    )
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
        if isinstance(self.provenance, ReductionProvenance):
            enforce_reduction_naming(
                name=self.name,
                reduction=self.provenance.reduction,
                domain=self.provenance.domain,
                base=self.provenance.base,
                vector_predicate=lambda b: b in self.components.values(),
            )
        return self

    @property
    def magnitude(self) -> str:
        return f"magnitude_of_{self.name}"


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
    """Validate data into a StandardName union instance via discriminator."""
    return _STANDARD_NAME_ADAPTER.validate_python(data)


__all__ = [
    "Kind",
    "Status",
    "Frame",
    "OperatorProvenance",
    "ExpressionProvenance",
    "StandardNameBase",
    "StandardNameScalar",
    "StandardNameDerivedScalar",
    "StandardNameVector",
    "StandardNameDerivedVector",
    "Name",  # token alias
    "StandardName",  # union
    "create_standard_name",
]
