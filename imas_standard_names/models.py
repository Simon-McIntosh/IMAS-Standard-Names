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

Example metadata entry:
  name: plasma_boundary
  kind: metadata
  status: draft
  description: Definition of plasma boundary.
  tags: [equilibrium, flux-coordinates]
  documentation: |
    Defines what constitutes the plasma boundary for different configurations.

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
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, get_args

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
    STANDARD_NAME_PATTERN,
    Constraints,
    Description,
    Documentation,
    Domain,
    Links,
    Name,
    Tags,
    Unit,
)
from imas_standard_names.grammar.field_schemas import FIELD_DESCRIPTIONS
from imas_standard_names.grammar.model_types import Component, Position, Process
from imas_standard_names.grammar.tag_types import (
    SECONDARY_TAGS,
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


def _check_grammar_vocabulary_consistency(name: str) -> list[str]:
    """Check if a standard name uses vocabulary tokens that don't exist in grammar.

    Only flags cases where clear template patterns indicate missing vocabulary tokens.
    Does NOT flag compound base names like 'electron_temperature' or 'plasma_velocity'.
    """
    errors = []

    # Only check for explicit template patterns with known vocabulary requirements
    # These patterns should always map to vocabulary tokens, not compound base names

    # Check 'component_of' pattern - should always map to Component vocabulary
    component_match = re.search(r"^([a-z_]+)_component_of_", name)
    if component_match:
        token = component_match.group(1)
        if token not in [c.value for c in Component]:
            errors.append(
                f"Token '{token}' used with 'component_of' template is missing from Component vocabulary"
            )

    # Check coordinate pattern - should always map to Component vocabulary (same tokens)
    coordinate_match = re.search(
        r"^([a-z_]+)_(?:position|vertex|centroid|outline|contour|displacement|offset|trajectory|extent|surface_normal|sensor_normal|tangent_vector)_",
        name,
    )
    if coordinate_match:
        token = coordinate_match.group(1)
        if token not in [c.value for c in Component]:
            errors.append(
                f"Token '{token}' used as coordinate prefix is missing from Component vocabulary"
            )

    # Check 'at_' pattern - should always map to Position vocabulary
    at_match = re.search(r"_at_([a-z_]+)(?:_|$)", name)
    if at_match:
        token = at_match.group(1)
        if token not in [p.value for p in Position]:
            errors.append(
                f"Token '{token}' used with 'at_' template is missing from Position vocabulary"
            )

    # Check 'due_to_' pattern - should always map to Process vocabulary
    due_to_match = re.search(r"_due_to_([a-z_]+)(?:_|$)", name)
    if due_to_match:
        token = due_to_match.group(1)
        if token not in [p.value for p in Process]:
            errors.append(
                f"Token '{token}' used with 'due_to_' template is missing from Process vocabulary"
            )

    # Skip 'of_' pattern validation entirely - it's used for both vocabulary tokens
    # AND valid compound base names like 'electron_temperature', 'plasma_velocity'

    return errors


class Kind(StrEnum):
    """Runtime enum for standard name kinds.

    Physical rank hierarchy:

    * ``scalar``  – rank-0, real-valued point quantity
      (e.g. ``electron_temperature``, ``safety_factor``).
    * ``vector``  – rank-1 quantity, including named single components.
      A field like ``magnetic_field_r`` carries an implicit radial
      covariant index and is therefore *vector*-natured even though
      only one component is stored.
    * ``tensor``  – rank-2 or higher quantity (stress tensor, metric
      tensor, conductivity tensor — full or individual component).
    * ``complex`` – complex-valued quantity (real + imaginary parts,
      or magnitude + phase).  Orthogonal to tensor rank in principle;
      kept as its own kind to preserve a flat discriminator.  Revisit
      if rank-aware complex names accumulate.
    * ``metadata`` – non-physical bookkeeping / annotation entries
      (e.g. ``plasma_boundary``, ``scrape_off_layer``).  No unit or
      provenance required.
    """

    scalar = "scalar"
    vector = "vector"
    tensor = "tensor"
    complex = "complex"
    metadata = "metadata"


class StandardNameBase(BaseModel):
    """Core identity + governance fields valid without documentation.

    This is the shared base for both full catalog entries (with description,
    documentation, tags, etc.) and lightweight name-only entries used during
    pipeline stages that generate names before descriptions exist. It defines
    only the fields and validators that are meaningful in both modes:

    - name, kind (set by subclass), status
    - deprecation/supersession governance
    - COCOS transformation type

    Subclasses either add full-entry documentation fields (see
    :class:`StandardNameEntryBase`) or remain minimal (name-only variants).
    """

    model_config = ConfigDict(extra="forbid")

    # Core identification
    name: Name
    status: Status = Field(
        "draft",
        description=FIELD_DESCRIPTIONS["status"],
    )

    # Governance
    deprecates: Name | None = None
    superseded_by: Name | None = None
    cocos_transformation_type: str | None = None

    # Supplemental validator for double underscore rule not expressible in pattern.
    @field_validator("name", "deprecates", "superseded_by")
    @classmethod
    def _no_double_underscore(cls, v: str | None) -> str | None:
        if v and "__" in v:
            raise ValueError("Name tokens must not contain double underscores")
        return v

    @field_validator("name")
    @classmethod
    def _check_grammar_vocabulary_consistency(cls, v: str) -> str:
        """Validate that template tokens in the name exist in the grammar vocabulary."""
        if not v:
            return v

        errors = _check_grammar_vocabulary_consistency(v)
        if errors:
            error_msg = "Grammar vocabulary consistency errors:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            raise ValueError(error_msg)
        return v

    @model_validator(mode="after")
    def _governance_rules(self):  # type: ignore[override]
        if self.status == "deprecated" and not self.superseded_by:
            raise ValueError(
                "Deprecated entries must set superseded_by referencing an active name"
            )
        return self

    # Base unit helpers (shared by scalar/vector subclasses, full and name-only).
    @staticmethod
    def _canonicalize_unit_order(v: str) -> str:
        """Auto-correct unit token order to canonical lexicographic form.

        This helps LLMs and human authors by accepting units in any order
        and automatically reordering to canonical form. For example:
        's^-2.m' -> 'm.s^-2'
        'keV.m^-1' -> 'keV.m^-1' (already canonical)

        Dimensionless quantities must use "1" as the canonical form.
        Empty strings and other invalid values will fail validation.
        """
        if v == "1":
            return "1"
        if v == "":
            raise ValueError(
                "Empty string not allowed for unit; use '1' for dimensionless quantities"
            )
        if " " in v:
            raise ValueError("Unit must not contain whitespace")
        if "/" in v or "*" in v:
            raise ValueError(
                "Use dot-exponent style (e.g. m.s^-2); '/' and '*' are forbidden"
            )

        # Parse tokens and reorder lexicographically
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
                raise ValueError(f"Zero exponent not allowed in unit token '{part}'")
            parsed.append((sym, exp))

        canonical = ".".join(
            sym if exp == 1 else f"{sym}^{exp}"
            for sym, exp in sorted(parsed, key=lambda x: x[0])
        )
        return canonical

    @staticmethod
    def _validate_unit_with_pint(v: str) -> str:
        """Validate unit semantics using pint (if available)."""
        if v == "1":
            return v
        if pint:
            try:
                pint.Unit(v)
            except Exception as e:  # pragma: no cover - defensive
                raise ValueError(f"Invalid unit '{v}': {e}") from e
        return v


class StandardNameEntryBase(StandardNameBase):
    """Full catalog entry definition (fields common to scalar and vector kinds).

    Extends :class:`StandardNameBase` with the documentation and metadata fields
    required of a published standard name: description, documentation, validity
    domain, constraints, tags, links. This remains the class used for the full
    catalog (serialization, JSON schema, rendering).
    """

    model_config = ConfigDict(extra="forbid")

    # Documentation & description
    description: Description
    documentation: Documentation  # Required: valuable standalone content

    # Governance / metadata (documentation-adjacent)
    validity_domain: Domain = ""
    constraints: Constraints = Field(default_factory=list)
    tags: Tags = Field(default_factory=list)  # Secondary classification tags
    links: Links = Field(default_factory=list)

    @field_validator("tags", "constraints")
    @classmethod
    def list_normalizer(cls, v: Iterable[str]) -> list[str]:  # type: ignore[override]
        if v is None:
            return []
        return [str(item).strip() for item in v if str(item).strip()]

    @field_validator("links")
    @classmethod
    def validate_links(cls, v: Iterable[str]) -> list[str]:  # type: ignore[override]
        """Validate links: normalize whitespace and validate format.

        Supports two formats:
        1. External URLs: must start with http:// or https://
        2. Internal standard name references: must start with 'name:' followed by valid name token
        """
        if v is None:
            return []

        result = []
        for item in v:
            link = str(item).strip()
            if not link:
                continue

            # Check if it's an internal name reference
            if link.startswith("name:"):
                # Extract the name part and validate it
                name_part = link[5:].strip()  # Remove 'name:' prefix
                if not name_part:
                    raise ValueError(
                        f"Invalid internal link '{link}': name cannot be empty after 'name:' prefix"
                    )
                # Validate name format
                if not re.match(STANDARD_NAME_PATTERN, name_part):
                    raise ValueError(
                        f"Invalid internal link '{link}': '{name_part}' is not a valid standard name token. "
                        f"Must match pattern {STANDARD_NAME_PATTERN}"
                    )
                result.append(link)
            # Check if it's an external URL
            elif link.startswith(("http://", "https://")):
                result.append(link)
            else:
                raise ValueError(
                    f"Invalid link '{link}': must be either an external URL (starting with http:// or https://) "
                    f"or an internal standard name reference (starting with 'name:')"
                )

        return result

    @field_validator("tags")
    @classmethod
    def validate_secondary_tags(cls, v: list[str]) -> list[str]:  # type: ignore[override]
        """Validate tags are all secondary tags from controlled vocabulary."""
        if not v:
            return v

        unknown_tags = [tag for tag in v if tag not in SECONDARY_TAGS]
        if unknown_tags:
            raise ValueError(
                f"Unknown secondary tag(s): {', '.join(unknown_tags)}. "
                f"Valid secondary tags are defined in grammar/vocabularies/tags.yml"
            )
        return v

    @field_validator("documentation")
    @classmethod
    def validate_sign_convention_format(cls, v: str) -> str:  # type: ignore[override]
        """Validate sign convention format if present in documentation.

        Enforces consistent formatting:
        - Must use 'Sign convention:' (not '**Sign convention:**' or variations)
        - Must start with 'Positive' followed by a qualifier:
          - 'Sign convention: Positive when <condition>.'
          - 'Sign convention: Positive <quantity-noun-phrase>.'
          - 'Sign convention: Positive for <subject>.'
        - Must follow the main documentation content (cannot be at start)
        - Must be a standalone paragraph (blank line before and after)
        """
        if not v:
            return v

        # Check if sign convention is mentioned
        if re.search(r"\bsign\s+convention\b", v, re.IGNORECASE):
            # Check for bold markdown formatting (not allowed) - check this FIRST
            # Match both **Sign convention:** and **Sign convention**
            if re.search(r"\*\*[Ss]ign\s+[Cc]onvention:?\*\*", v):
                raise ValueError(
                    "Sign convention must use plain text 'Sign convention:', not bold '**Sign convention:**'"
                )

            # Check for lowercase/uppercase issues
            if re.search(r"sign convention:", v):  # lowercase 'sign'
                raise ValueError(
                    "Sign convention format must use title case: 'Sign convention: Positive when [condition].' "
                    "(found lowercase 'sign convention:', should be 'Sign convention:')"
                )
            elif re.search(r"SIGN CONVENTION:", v):  # all caps
                raise ValueError(
                    "Sign convention format must use title case: 'Sign convention: Positive when [condition].' "
                    "(found all caps 'SIGN CONVENTION:', should be 'Sign convention:')"
                )

            # Check for exact format: "Sign convention:" (title case with colon)
            # Must be followed by "Positive" and then a qualifier word
            correct_format = re.search(r"Sign convention:\s+Positive\s+", v)

            if not correct_format:
                # Missing "Positive" keyword
                raise ValueError(
                    "Sign convention must use 'Sign convention: Positive ...' format. "
                    "Accepted forms: 'Positive when <condition>.', "
                    "'Positive <quantity-noun-phrase>.', "
                    "'Positive for <subject>.'."
                )

            # Check for standalone paragraph (must have \n\n before and after)
            # Sign convention must NOT be at document start - must follow main content
            # Find the actual "Sign convention:" text position
            sign_match = re.search(r"Sign convention:[^\n]+", v)
            if sign_match:
                start_pos = sign_match.start()
                end_pos = sign_match.end()

                # Must have content before sign convention (cannot be at document start)
                if start_pos < 2:
                    raise ValueError(
                        "Sign convention must follow the main documentation content. "
                        "It cannot be at the start of the documentation field."
                    )

                # Check if preceded by \n\n
                preceding_text = v[start_pos - 2 : start_pos]
                if preceding_text != "\n\n":
                    raise ValueError(
                        "Sign convention must be a standalone paragraph with a blank line before it. "
                        "Add '\\n\\n' before 'Sign convention:' to separate it from preceding text."
                    )

                # Check if followed by \n\n (or is at end of string)
                if end_pos < len(v):
                    # Look at the 2 characters after the sign convention sentence
                    following_text = v[end_pos : min(len(v), end_pos + 2)]
                    if not following_text.startswith("\n\n") and following_text.strip():
                        raise ValueError(
                            "Sign convention must be a standalone paragraph with a blank line after it. "
                            "Add '\\n\\n' after the sign convention sentence to separate it from following text."
                        )

        return v

    @model_validator(mode="after")
    def _entry_governance_rules(self):  # type: ignore[override]
        # Base class already runs deprecated/superseded_by check; kept for future doc-level rules.
        return self

    @property
    def is_dimensionless(self) -> bool:
        return self.unit == "1"

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
    unit: Unit  # Required for scalar (use "1" for dimensionless)
    provenance: Provenance | None = None

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        """Auto-correct unit token order to canonical lexicographic form."""
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        """Validate unit semantics using pint (if available)."""
        return cls._validate_unit_with_pint(v)

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
    unit: Unit  # Required for vector (use "1" for dimensionless)
    provenance: Provenance | None = None

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        """Auto-correct unit token order to canonical lexicographic form."""
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        """Validate unit semantics using pint (if available)."""
        return cls._validate_unit_with_pint(v)

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


class StandardNameTensorEntry(StandardNameEntryBase):
    """Tensor (rank-2+) standard name catalog entry.

    Used for quantities that represent tensor fields — metric tensors,
    stress tensors, conductivity tensors, etc.  Individual named
    components (e.g. ``g11_covariant_metric_tensor_component``) are
    also classified as *tensor* because they carry implicit index
    structure.
    """

    kind: Literal["tensor"] = "tensor"
    unit: Unit  # Required (use "1" for dimensionless)
    provenance: Provenance | None = None

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        """Auto-correct unit token order to canonical lexicographic form."""
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        """Validate unit semantics using pint (if available)."""
        return cls._validate_unit_with_pint(v)

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


class StandardNameComplexEntry(StandardNameEntryBase):
    """Complex-valued standard name catalog entry.

    Used for quantities that have real and imaginary parts (or
    equivalently, magnitude and phase).  Examples include perturbed
    MHD quantities, wave amplitudes, and impedance components.
    """

    kind: Literal["complex"] = "complex"
    unit: Unit  # Required (use "1" for dimensionless)
    provenance: Provenance | None = None

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        """Auto-correct unit token order to canonical lexicographic form."""
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        """Validate unit semantics using pint (if available)."""
        return cls._validate_unit_with_pint(v)

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


class StandardNameMetadataEntry(StandardNameEntryBase):
    """Metadata standard name catalog entry.

    Used for definitional entries that document concepts, boundaries,
    or reference anchors rather than measurable physical quantities.
    These entries provide documentation and cross-references but do not
    represent data that can be measured or calculated.

    Examples: plasma_boundary, scrape_off_layer, confined_region

    Metadata entries have relaxed validation:
    - No unit field required (these are definitional, not measurable)
    - No provenance required (these are definitional, not derived)
    - Focus on documentation and links fields
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["metadata"] = "metadata"
    # No unit field - metadata entries are definitional, not measurable

    def model_dump(self, **kwargs):
        """Override to ensure consistent serialization for metadata entries."""
        return super().model_dump(**kwargs)


StandardNameEntry = Annotated[
    StandardNameScalarEntry
    | StandardNameVectorEntry
    | StandardNameTensorEntry
    | StandardNameComplexEntry
    | StandardNameMetadataEntry,
    Field(discriminator="kind"),
]

_STANDARD_NAME_ENTRY_ADAPTER = TypeAdapter(StandardNameEntry)


# ---------------------------------------------------------------------------
# Name-only entry classes
# ---------------------------------------------------------------------------
# Support partial validation during LLM-driven generation where only the
# identity+unit portion of a standard name has been composed and the
# description/documentation are filled in by a later enrichment pass.
# These classes inherit governance + grammar + unit validation from
# ``StandardNameBase`` but deliberately omit the documentation fields.


class StandardNameScalarNameOnly(StandardNameBase):
    """Scalar standard name — name + unit only (no documentation)."""

    kind: Literal["scalar"] = "scalar"
    unit: Unit  # Required for scalar (use "1" for dimensionless)

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        return cls._validate_unit_with_pint(v)


class StandardNameVectorNameOnly(StandardNameBase):
    """Vector standard name — name + unit only (no documentation)."""

    kind: Literal["vector"] = "vector"
    unit: Unit  # Required for vector (use "1" for dimensionless)

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        return cls._validate_unit_with_pint(v)


class StandardNameTensorNameOnly(StandardNameBase):
    """Tensor standard name — name + unit only (no documentation)."""

    kind: Literal["tensor"] = "tensor"
    unit: Unit  # Required (use "1" for dimensionless)

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        return cls._validate_unit_with_pint(v)


class StandardNameComplexNameOnly(StandardNameBase):
    """Complex standard name — name + unit only (no documentation)."""

    kind: Literal["complex"] = "complex"
    unit: Unit  # Required (use "1" for dimensionless)

    @field_validator("unit", mode="before")
    @classmethod
    def canonicalize_unit_order(cls, v: str) -> str:
        return cls._canonicalize_unit_order(v)

    @field_validator("unit")
    @classmethod
    def validate_unit_with_pint(cls, v: str) -> str:
        return cls._validate_unit_with_pint(v)


class StandardNameMetadataNameOnly(StandardNameBase):
    """Metadata standard name — name only (no unit, no documentation)."""

    kind: Literal["metadata"] = "metadata"


StandardNameNameOnly = Annotated[
    StandardNameScalarNameOnly
    | StandardNameVectorNameOnly
    | StandardNameTensorNameOnly
    | StandardNameComplexNameOnly
    | StandardNameMetadataNameOnly,
    Field(discriminator="kind"),
]

_NAME_ONLY_ADAPTER = TypeAdapter(StandardNameNameOnly)


def _build_standard_name_models() -> dict[str, type[StandardNameEntry]]:
    """Build mapping of kind string to model class from StandardNameEntry union.

    Extracts model classes from the discriminated union and indexes them by
    their kind literal value. This provides O(1) lookup for loading entries.

    Returns:
        Dictionary mapping kind strings ('scalar', 'vector', 'metadata') to
        their corresponding model classes.
    """
    union_type = get_args(StandardNameEntry)[0]
    model_classes = get_args(union_type)
    return {
        model_class.model_fields["kind"].default: model_class
        for model_class in model_classes
    }


STANDARD_NAME_MODELS = _build_standard_name_models()


def create_standard_name_entry(
    data: dict, *, name_only: bool = False
) -> StandardNameEntry | StandardNameNameOnly:
    """Validate data into a StandardName entry instance.

    Args:
        data: Entry dictionary. Must include ``kind`` for discrimination.
        name_only: When ``True``, validate against the lightweight name-only
            union (identity + unit) that omits description/documentation/tags.
            Use this during early LLM generation passes. Defaults to ``False``
            for full catalog-entry validation.
    """
    if name_only:
        return _NAME_ONLY_ADAPTER.validate_python(data)
    return _STANDARD_NAME_ENTRY_ADAPTER.validate_python(data)


def load_standard_name_entry(data: dict) -> StandardNameEntry:
    """Load a StandardNameEntry instance without validation (bypasses validators)."""
    kind = data.get("kind")
    if not kind:
        raise ValueError("Missing required field 'kind' in data dictionary")

    kind_str = kind.value if isinstance(kind, Kind) else kind
    model_class = STANDARD_NAME_MODELS.get(kind_str)

    if not model_class:
        valid_kinds = ", ".join(STANDARD_NAME_MODELS.keys())
        raise ValueError(f"Unknown kind: {kind_str}. Valid kinds: {valid_kinds}")

    return model_class.model_construct(**data)


class StandardNameCatalogManifest(BaseModel):
    """Catalog-level manifest describing a published standard names catalog.

    Placed at the repository root (``catalog.yml``) and records run-level
    metadata about the export that produced the catalog. Individual entries
    carry only editorial fields; generation provenance lives here.
    """

    model_config = ConfigDict(extra="forbid")

    catalog_name: str
    cocos_convention: int
    grammar_version: str
    isn_model_version: str
    dd_version_lineage: list[str]
    generated_by: str
    generated_at: datetime
    min_score_applied: float | None = None
    min_description_score_applied: float | None = None
    include_unreviewed: bool = False
    candidate_count: int
    published_count: int
    excluded_below_score_count: int = 0
    excluded_unreviewed_count: int = 0
    source_repo: str | None = None
    source_commit_sha: str | None = None


__all__ = [
    "Kind",
    "Status",
    "OperatorProvenance",
    "ExpressionProvenance",
    "StandardNameBase",
    "StandardNameEntryBase",
    "StandardNameScalarEntry",
    "StandardNameVectorEntry",
    "StandardNameTensorEntry",
    "StandardNameComplexEntry",
    "StandardNameMetadataEntry",
    "StandardNameScalarNameOnly",
    "StandardNameVectorNameOnly",
    "StandardNameTensorNameOnly",
    "StandardNameComplexNameOnly",
    "StandardNameMetadataNameOnly",
    "StandardNameNameOnly",
    "Name",
    "StandardNameEntry",
    "StandardNameCatalogManifest",
    "STANDARD_NAME_MODELS",
    "create_standard_name_entry",
    "load_standard_name_entry",
]
