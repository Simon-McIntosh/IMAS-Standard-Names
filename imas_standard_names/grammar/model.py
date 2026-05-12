"""Static StandardName model and friendly wrappers.

This module holds the hand-written Pydantic model and thin compose/parse
wrappers that bridge the parser/renderer (IR-based) to the flat
StandardName model used by the rest of the codebase.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from imas_standard_names.grammar.constants import (
    BINARY_OPERATOR_CONNECTORS,
    EXCLUSIVE_SEGMENT_PAIRS,
    GENERIC_PHYSICAL_BASES,
)
from imas_standard_names.grammar.ir import (
    AxisProjection,
    BaseKind,
    LocusRef,
    LocusRelation,
    LocusType,
    OperatorApplication,
    OperatorKind,
    Process as IRProcess,
    ProjectionShape,
    Qualifier,
    QuantityOrCarrier,
    StandardNameIR,
)
from imas_standard_names.grammar.model_types import (
    BinaryOperator,
    Component,
    Decomposition,
    GeometricBase,
    Object,
    Position,
    Process,
    Region,
    Subject,
    Transformation,
)
from imas_standard_names.grammar.parser import ParseError, parse as _parse_ir
from imas_standard_names.grammar.render import compose as _compose_ir
from imas_standard_names.grammar.support import (
    TOKEN_PATTERN,
    value_of as _value_of,
)

# BaseToken: pattern for physical_base segment (closed vocabulary since rc56)
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

# ---------------------------------------------------------------------------
# Subject / Object value sets for qualifier classification
# ---------------------------------------------------------------------------
_SUBJECT_VALUES: frozenset[str] = frozenset(s.value for s in Subject)
_OBJECT_VALUES: frozenset[str] = frozenset(o.value for o in Object)
_POSITION_VALUES: frozenset[str] = frozenset(p.value for p in Position)
_REGION_VALUES: frozenset[str] = frozenset(r.value for r in Region)
_GEOMETRY_VALUES: frozenset[str] = frozenset(g.value for g in GeometricBase)

# Map from LocusType to model field name
_LOCUS_TYPE_TO_FIELD: dict[LocusType, str] = {
    LocusType.ENTITY: "object",
    LocusType.GEOMETRY: "geometry",
    LocusType.POSITION: "position",
    LocusType.REGION: "region",
}

# Map from model field name to (LocusRelation, LocusType)
_FIELD_TO_LOCUS: dict[str, tuple[LocusRelation, LocusType]] = {
    "object": (LocusRelation.OF, LocusType.ENTITY),
    "geometry": (LocusRelation.OF, LocusType.POSITION),
    "position": (LocusRelation.AT, LocusType.POSITION),
    "region": (LocusRelation.OVER, LocusType.REGION),
}

# Map between model BinaryOperator tokens (e.g. "ratio_of") and IR bare tokens
_BINARY_MODEL_TO_IR: dict[str, str] = {
    "product_of": "product",
    "ratio_of": "ratio",
    "difference_of": "difference",
}
_BINARY_IR_TO_MODEL: dict[str, str] = {v: k for k, v in _BINARY_MODEL_TO_IR.items()}

# Map from IR binary operator separator to connector (for lookups)
_BINARY_SEPARATOR_MAP: dict[str, str] = {}
for _model_tok, _connector in BINARY_OPERATOR_CONNECTORS.items():
    _ir_tok = _BINARY_MODEL_TO_IR.get(_model_tok)
    if _ir_tok:
        _BINARY_SEPARATOR_MAP[_ir_tok] = _connector

# ---------------------------------------------------------------------------
# Transformation form classification
# ---------------------------------------------------------------------------
# Transformation tokens that render as bare prefixes (<token>_<base>) rather
# than _of_ form (<token>_of_<base>).  The parser treats these as
# qualifiers (not operators) since they lack the _of_ joining marker.
# Determined by corpus analysis of canonical standard names.
_TRANSFORMATION_VALUES: frozenset[str] = frozenset(t.value for t in Transformation)
_BARE_PREFIX_TRANSFORMATIONS: frozenset[str] = frozenset(
    {
        "accumulated",
        "cumulative",
        "cumulative_inside_flux_surface",
        "flux_surface_averaged",
        "gyroaveraged",
        "line_averaged",
        "line_integrated",
        "maximum_over_flux_surface",
        "minimum_over_flux_surface",
        "normalized",
        "per_poloidal_mode",
        "per_toroidal_and_poloidal_mode_number",
        "per_toroidal_mode",
        "perturbed",
        "surface_integrated",
        "time_average",
        "volume_averaged",
        "volume_integrated",
    }
)


# ---------------------------------------------------------------------------
# IR ↔ Model adapters
# ---------------------------------------------------------------------------


def _ir_to_model_dict(ir: StandardNameIR) -> dict[str, str]:
    """Convert a parsed IR to the flat dict consumed by StandardName.model_validate."""
    d: dict[str, str] = {}

    # Check for binary operator (outermost operator with kind=BINARY)
    binary_op: OperatorApplication | None = None
    unary_ops: list[OperatorApplication] = []
    for op in ir.operators:
        if op.kind is OperatorKind.BINARY:
            binary_op = op
        else:
            unary_ops.append(op)

    if binary_op is not None:
        # Binary operator: extract operands from args
        model_op = _BINARY_IR_TO_MODEL.get(binary_op.op, f"{binary_op.op}_of")
        d["binary_operator"] = model_op

        # Render each operand back to its string form (physical_base, secondary_base)
        if len(binary_op.args) == 2:
            d["physical_base"] = _compose_ir(binary_op.args[0])
            d["secondary_base"] = _compose_ir(binary_op.args[1])
    else:
        # Unary operators
        for op in unary_ops:
            if op.kind is OperatorKind.UNARY_PREFIX:
                d["transformation"] = op.op
            elif op.kind is OperatorKind.UNARY_POSTFIX:
                d["decomposition"] = op.op

        # Projection → component or coordinate
        if ir.projection is not None:
            if ir.projection.shape is ProjectionShape.COMPONENT:
                d["component"] = ir.projection.axis
            elif ir.projection.shape is ProjectionShape.COORDINATE:
                d["coordinate"] = ir.projection.axis

        # Base + qualifiers → physical_base or geometric_base
        if ir.base.kind is BaseKind.GEOMETRY:
            d["geometric_base"] = ir.base.token
        else:
            # physical_base: fold uncategorized qualifiers back as prefix
            subject = None
            device = None
            transformation_token = None
            base_qualifiers: list[str] = []
            for q in ir.qualifiers:
                if q.token in _SUBJECT_VALUES:
                    subject = q.token
                elif q.token in _OBJECT_VALUES:
                    device = q.token
                elif (
                    q.token in _BARE_PREFIX_TRANSFORMATIONS
                    and transformation_token is None
                ):
                    transformation_token = q.token
                else:
                    base_qualifiers.append(q.token)
            if subject:
                d["subject"] = subject
            if device:
                d["device"] = device
            if transformation_token:
                d["transformation"] = transformation_token
            # Fold remaining qualifiers into physical_base as compound
            if base_qualifiers:
                d["physical_base"] = "_".join([*base_qualifiers, ir.base.token])
            else:
                d["physical_base"] = ir.base.token

    # Locus → object/geometry/position/region
    if ir.locus is not None:
        token = ir.locus.token
        if ir.locus.type == LocusType.POSITION:
            if ir.locus.relation == LocusRelation.OVER and token in _REGION_VALUES:
                d["region"] = token
            elif ir.locus.relation == LocusRelation.AT:
                if token in _POSITION_VALUES:
                    d["position"] = token
            else:
                if token in _POSITION_VALUES or token in _GEOMETRY_VALUES:
                    d["geometry"] = token
                # else: unregistered geometry token, skip
        elif ir.locus.type == LocusType.REGION:
            if token in _REGION_VALUES:
                d["region"] = token
        else:
            field_name = _LOCUS_TYPE_TO_FIELD.get(ir.locus.type)
            if field_name:
                d[field_name] = token

    # Mechanism → process
    if ir.mechanism is not None:
        d["process"] = ir.mechanism.token

    return d


def _model_to_ir(model: StandardName) -> StandardNameIR:
    """Convert a StandardName model to IR for rendering."""
    operators: list[OperatorApplication] = []
    projection: AxisProjection | None = None
    qualifiers: list[Qualifier] = []
    locus: LocusRef | None = None
    mechanism: IRProcess | None = None

    # Binary operator
    if model.binary_operator:
        op_model_value = _value_of(model.binary_operator)
        ir_op = _BINARY_MODEL_TO_IR.get(op_model_value, op_model_value)

        # Look up separator from BINARY_OPERATOR_CONNECTORS
        connector = BINARY_OPERATOR_CONNECTORS.get(op_model_value)
        if connector is None:
            raise ValueError(
                f"Unknown binary operator '{op_model_value}': "
                f"no connector defined in BINARY_OPERATOR_CONNECTORS"
            )

        # Build sub-IRs for each operand by re-parsing them
        a_str = model.physical_base or ""
        b_str = _value_of(model.secondary_base) if model.secondary_base else ""
        a_ir = _parse_simple_base(a_str)
        b_ir = _parse_simple_base(b_str)

        operators.append(
            OperatorApplication(
                kind=OperatorKind.BINARY,
                op=ir_op,
                separator=connector,
                args=[a_ir, b_ir],
            )
        )
        # Binary uses a placeholder base
        base = QuantityOrCarrier(token="placeholder", kind=BaseKind.QUANTITY)
    else:
        # Transformation (unary prefix)
        transformation_qualifier: Qualifier | None = None
        if model.transformation:
            tf_token = _value_of(model.transformation)
            if tf_token in _BARE_PREFIX_TRANSFORMATIONS:
                # Bare-prefix transformations render as qualifiers
                # (will be prepended to base by the renderer)
                transformation_qualifier = Qualifier(token=tf_token)
            else:
                operators.append(
                    OperatorApplication(
                        kind=OperatorKind.UNARY_PREFIX,
                        op=tf_token,
                    )
                )

        # Decomposition (unary postfix)
        if model.decomposition:
            operators.append(
                OperatorApplication(
                    kind=OperatorKind.UNARY_POSTFIX,
                    op=_value_of(model.decomposition),
                )
            )

        # Projection
        if model.component:
            projection = AxisProjection(
                axis=_value_of(model.component), shape=ProjectionShape.COMPONENT
            )
        elif model.coordinate:
            projection = AxisProjection(
                axis=_value_of(model.coordinate), shape=ProjectionShape.COORDINATE
            )

        # Base
        if model.geometric_base:
            base = QuantityOrCarrier(
                token=_value_of(model.geometric_base), kind=BaseKind.GEOMETRY
            )
        elif model.physical_base:
            # Re-parse the physical_base to decompose qualifiers + base
            base, qualifiers = _decompose_physical_base(
                model.physical_base, model.subject, model.device
            )
            # Insert bare-prefix transformation qualifier at the front
            # (transformation is outermost: <transform>_<subject>_<base>)
            if transformation_qualifier is not None:
                qualifiers.insert(0, transformation_qualifier)
        else:
            raise ValueError("Either geometric_base or physical_base must be set")

    # Locus — position field uses _at_, geometry field uses _of_ for
    # POSITION-type loci. Other fields use their fixed defaults.
    for field_name, (default_relation, locus_type) in _FIELD_TO_LOCUS.items():
        value = getattr(model, field_name, None)
        if value is not None:
            locus = LocusRef(
                relation=default_relation, token=_value_of(value), type=locus_type
            )
            break

    # Mechanism
    if model.process:
        mechanism = IRProcess(token=_value_of(model.process))

    return StandardNameIR(
        operators=operators,
        projection=projection,
        qualifiers=qualifiers,
        base=base,
        locus=locus,
        mechanism=mechanism,
    )


def _parse_simple_base(base_str: str) -> StandardNameIR:
    """Parse a simple base string (e.g. 'electron_temperature') into an IR.

    Used for binary operator operands. Falls back to treating the whole
    string as a literal physical_base if re-parsing fails.
    """
    try:
        result = _parse_ir(base_str)
        return result.ir
    except (ParseError, ValueError):
        # Fallback: treat as a literal physical_base
        return StandardNameIR(
            base=QuantityOrCarrier(token=base_str, kind=BaseKind.QUANTITY)
        )


def _decompose_physical_base(
    physical_base: str,
    subject: Subject | None,
    device: Object | None,
) -> tuple[QuantityOrCarrier, list[Qualifier]]:
    """Decompose a physical_base string into IR base + qualifiers.

    The physical_base may be a compound like 'magnetic_field' or
    'diamagnetic_drift_velocity'. We use the parser to decompose
    it correctly, then prepend subject/device as qualifiers.
    """
    qualifiers: list[Qualifier] = []

    # Add subject and device as qualifiers (in model order: subject before device)
    if subject:
        qualifiers.append(Qualifier(token=_value_of(subject)))
    if device:
        qualifiers.append(Qualifier(token=_value_of(device)))

    # Try to parse the physical_base to extract any embedded qualifiers
    try:
        result = _parse_ir(physical_base)
        # Successfully parsed: merge the parsed qualifiers
        qualifiers.extend(result.ir.qualifiers)
        return result.ir.base, qualifiers
    except (ParseError, ValueError):
        # Can't decompose: use the whole string as base
        return QuantityOrCarrier(
            token=physical_base, kind=BaseKind.QUANTITY
        ), qualifiers


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
    region: Region | None = None
    process: Process | None = None
    transformation: Transformation | None = None
    decomposition: Decomposition | None = None
    binary_operator: BinaryOperator | None = None
    secondary_base: BaseToken | None = None

    @field_validator("physical_base")
    @classmethod
    def _validate_physical_base(cls, value: str | None) -> str | None:
        if value is not None and not TOKEN_PATTERN.fullmatch(value):
            msg = "physical_base segment must match the canonical token pattern"
            raise ValueError(msg)
        return value

    @field_validator("secondary_base")
    @classmethod
    def _validate_secondary_base(cls, value: str | None) -> str | None:
        if value is not None and not TOKEN_PATTERN.fullmatch(value):
            msg = "secondary_base segment must match the canonical token pattern"
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
    def _check_transformation_exclusivity(self) -> StandardName:
        """Transformation is exclusive with component, coordinate, and geometric_base."""
        if self.transformation:
            if self.component:
                msg = "Segments 'transformation' and 'component' cannot both be set"
                raise ValueError(msg)
            if self.coordinate:
                msg = "Segments 'transformation' and 'coordinate' cannot both be set"
                raise ValueError(msg)
            if self.geometric_base:
                msg = (
                    "Segments 'transformation' and 'geometric_base' cannot both be set"
                )
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_decomposition_exclusivity(self) -> StandardName:
        """Decomposition is exclusive with transformation and geometric_base.

        Spec reference: plan 29 / ADR-4 grammar findings F3.
        Decomposition wraps physical_base only; stacking with transformation
        would produce names like ``square_of_fourier_coefficient_of_...`` that
        are not useful enough to justify the parsing ambiguity.
        """
        if self.decomposition:
            if self.transformation:
                msg = "Segments 'decomposition' and 'transformation' cannot both be set"
                raise ValueError(msg)
            if self.geometric_base:
                msg = "Segments 'decomposition' and 'geometric_base' cannot both be set"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_binary_operator_exclusivity(self) -> StandardName:
        """Binary operator is exclusive with component, transformation,
        decomposition, coordinate, subject, device, and geometric_base.
        """
        if self.binary_operator:
            exclusive_fields = {
                "component": self.component,
                "transformation": self.transformation,
                "decomposition": self.decomposition,
                "coordinate": self.coordinate,
                "subject": self.subject,
                "device": self.device,
                "geometric_base": self.geometric_base,
            }
            for field_name, field_value in exclusive_fields.items():
                if field_value:
                    msg = (
                        f"Segments 'binary_operator' and '{field_name}' "
                        f"cannot both be set"
                    )
                    raise ValueError(msg)
            if not self.secondary_base:
                msg = "binary_operator requires secondary_base"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_secondary_base_requires_binary(self) -> StandardName:
        """secondary_base can only be set with binary_operator."""
        if self.secondary_base and not self.binary_operator:
            msg = "secondary_base can only be set when binary_operator is set"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_binary_operator_connector_safety(self) -> StandardName:
        """Validate that binary operator operands don't contain the connector word."""
        if self.binary_operator and self.physical_base and self.secondary_base:
            connector = BINARY_OPERATOR_CONNECTORS.get(self.binary_operator.value, "")
            connector_sep = f"_{connector}_"
            if connector_sep in f"_{self.physical_base}_":
                msg = (
                    f"physical_base '{self.physical_base}' contains reserved "
                    f"connector word '{connector}'"
                )
                raise ValueError(msg)
            if connector_sep in f"_{self.secondary_base}_":
                msg = (
                    f"secondary_base '{self.secondary_base}' contains reserved "
                    f"connector word '{connector}'"
                )
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
            - power_due_to_viscous_heat_flux (process qualifier)
        """
        if self.physical_base and self.physical_base in GENERIC_PHYSICAL_BASES:
            # Check if ANY qualifying segment is present
            # Transformations, binary operators, and processes also qualify generic bases
            has_qualification = any(
                [
                    self.subject,
                    self.device,
                    self.object,
                    self.position,
                    self.geometry,
                    self.region,
                    self.process,
                    self.transformation,
                    self.decomposition,
                    self.binary_operator,
                ]
            )

            if not has_qualification:
                msg = (
                    f"Generic physical_base '{self.physical_base}' requires qualification. "
                    f"Generic terms like '{self.physical_base}' are ambiguous without context. "
                    f"Add a qualifying segment: subject (e.g., electron_), device (e.g., flux_loop_), "
                    f"object (e.g., of_flux_loop), position (e.g., at_magnetic_axis), "
                    f"geometry (e.g., of_plasma_boundary), or region (e.g., over_halo_region)."
                )
                raise ValueError(msg)

        return self

    def compose(self) -> str:
        ir = _model_to_ir(self)
        return _compose_ir(ir)

    def model_dump_compact(self) -> dict[str, str]:
        return {
            key: _value_of(value)
            for key, value in self.model_dump().items()
            if value is not None
        }


def compose_standard_name(parts: Mapping[str, Any] | StandardName) -> str:
    if isinstance(parts, StandardName):
        model = parts
    else:
        model = StandardName.model_validate(parts)
    ir = _model_to_ir(model)
    return _compose_ir(ir)


def parse_standard_name(name: str) -> StandardName:
    try:
        result = _parse_ir(name)
    except ParseError as exc:
        if exc.residue:
            from imas_standard_names.grammar.parser import (  # noqa: PLC0415
                load_default_vocabularies as _load_vocabs,
            )
            from imas_standard_names.grammar.support import (  # noqa: PLC0415
                UnknownBaseTokenError,
            )

            vocabs = _load_vocabs()
            known = tuple(sorted(vocabs.bases | vocabs.carriers))
            raise UnknownBaseTokenError(exc.residue, known) from exc
        raise
    return StandardName.model_validate(_ir_to_model_dict(result.ir))


__all__ = [
    "StandardName",
    "compose_standard_name",
    "parse_standard_name",
]
