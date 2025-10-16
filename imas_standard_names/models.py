"""Pydantic models for IMAS Standard Names catalog entries.

This module defines the complete data model for standard name catalog entries,
including all metadata, provenance, governance, and validation rules.

The StandardNameEntry union type represents full catalog entries with:
- Core identification (name, kind, description)
- Physical properties (unit, constraints, validity domain)
- Governance (status, deprecation, supersession)
- Provenance (operators, reductions, expressions)
- Metadata (tags, links, documentation)

Example scalar entry:
  name: ion_temperature
  kind: scalar
  status: active
  unit: eV
  description: Core ion temperature.
  tags: [core, temperature]
  constraints:
    - T_i >= 0
  validity_domain: core plasma

Example vector entry:
  name: plasma_velocity
  kind: vector
  status: active
  unit: m/s
  description: Plasma velocity vector.

Example with operator provenance:
  name: gradient_of_electron_temperature
  kind: vector
  status: active
  unit: eV/m
  description: Spatial gradient of electron temperature.
  provenance:
    mode: operator
    operators: [gradient]
    base: electron_temperature
    operator_id: gradient

"""

import re
from collections.abc import Iterable
from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

from imas_standard_names import pint
from imas_standard_names.field_types import (
    Constraints,
    Description,
    Documentation,
    Domain,
    Links,
    Name,
    Tags,
    Unit,
)
from imas_standard_names.operators import (
    enforce_operator_naming as _enforce_operator_naming,
    normalize_operator_chain as _normalize_operator_chain,
)
from imas_standard_names.provenance import (
    ExpressionProvenance,
    OperatorProvenance,
    Provenance,
    ReductionProvenance,
)
from imas_standard_names.reductions import enforce_reduction_naming

Status = Literal["draft", "active", "deprecated", "superseded"]


class Kind(str, Enum):
    """Runtime enum for standard name kinds."""

    scalar = "scalar"
    vector = "vector"


class StandardNameEntryBase(BaseModel):
    """Base catalog entry definition (fields common to scalar and vector kinds).

    Represents a complete standard name catalog entry with all metadata,
    governance rules, and validation. This is a Pydantic discriminated union
    configured via 'kind'. Subclasses define literal kind values.
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
    provenance: Provenance | None = None

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
    def list_normalizer(cls, v: Iterable[str]) -> list[str]:  # type: ignore[override]
        if v is None:
            return []
        return [str(item).strip() for item in v if str(item).strip()]

    @field_validator("tags")
    @classmethod
    def validate_and_reorder_tags(cls, v: list[str]) -> list[str]:  # type: ignore[override]
        """Validate tags: ensure exactly one primary tag (auto-reorder to position 0) and validate vocabulary."""
        if not v or len(v) == 0:
            return v

        from imas_standard_names.grammar.tag_types import (
            PRIMARY_TAGS,
            SECONDARY_TAGS,
        )

        # Find all primary tags in the list
        primary_tags_found = [tag for tag in v if tag in PRIMARY_TAGS]
        unknown_tags = [
            tag for tag in v if tag not in PRIMARY_TAGS and tag not in SECONDARY_TAGS
        ]

        # Check for unknown tags first
        if unknown_tags:
            raise ValueError(
                f"Unknown tag(s): {', '.join(unknown_tags)}. "
                f"Valid tags are defined in grammar/vocabularies/tags.yml"
            )

        # Enforce exactly one primary tag
        if len(primary_tags_found) == 0:
            raise ValueError(
                f"Tags must contain exactly one primary tag. Found none. "
                f"Valid primary tags include: {', '.join(sorted(PRIMARY_TAGS)[:10])}... "
                f"(see grammar/vocabularies/tags.yml for complete list)"
            )
        elif len(primary_tags_found) > 1:
            raise ValueError(
                f"Tags must contain exactly one primary tag. Found {len(primary_tags_found)}: {', '.join(primary_tags_found)}. "
                f"Choose a single primary tag that best categorizes this entry."
            )

        # Auto-reorder: ensure the single primary tag is at position 0
        primary_tag = primary_tags_found[0]
        if v[0] != primary_tag:
            # Remove primary tag from its current position and place at start
            reordered = [primary_tag] + [tag for tag in v if tag != primary_tag]
            return reordered

        return v

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


class StandardNameScalarEntry(StandardNameEntryBase):
    """Scalar standard name catalog entry."""

    kind: Literal["scalar"] = "scalar"

    @model_validator(mode="after")
    def _provenance_rules(self):  # type: ignore[override]
        if self.provenance:
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


class StandardNameVectorEntry(StandardNameEntryBase):
    """Vector standard name catalog entry."""

    kind: Literal["vector"] = "vector"

    @model_validator(mode="after")
    def _provenance_rules(self):  # type: ignore[override]
        if self.provenance:
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

    @property
    def magnitude(self) -> str:
        """Derived magnitude standard name.

        Conventionally 'magnitude_of_<vector_name>'.
        """
        return f"magnitude_of_{self.name}"


StandardNameEntry = Annotated[
    StandardNameScalarEntry | StandardNameVectorEntry,
    Field(discriminator="kind"),
]

_STANDARD_NAME_ENTRY_ADAPTER = TypeAdapter(StandardNameEntry)


def create_standard_name_entry(data: dict) -> StandardNameEntry:
    """Validate data into a StandardNameEntry union instance via discriminator."""
    return _STANDARD_NAME_ENTRY_ADAPTER.validate_python(data)


__all__ = [
    "Kind",
    "Status",
    "OperatorProvenance",
    "ExpressionProvenance",
    "StandardNameEntryBase",
    "StandardNameScalarEntry",
    "StandardNameVectorEntry",
    "Name",
    "StandardNameEntry",
    "create_standard_name_entry",
]
