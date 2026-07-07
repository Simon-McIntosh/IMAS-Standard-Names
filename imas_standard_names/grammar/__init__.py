"""Runtime helpers and types for IMAS standard names.

This package hosts hand-written behavior separated from generated
vocabulary/metadata (grammar_models).
"""

from .model import (
    NonCanonicalNameError,
    StandardName,
    compose_standard_name,
    parse_standard_name,
)
from .model_types import (
    BinaryOperator,
    Component,
    GenericPhysicalBase,
    GeometricBase,
    Object,
    Position,
    Process,
    Subject,
    Transformation,
)
from .support import (
    TOKEN_PATTERN,
    UnknownBaseTokenError,
    coerce_enum,
    enum_values,
    normalize_standard_name,
    validate_forbidden_patterns,
    value_of,
)

from .ir import StandardNameIR
from .parser import (
    Diagnostic,
    ParseError,
    ParseResult,
    Vocabularies,
    load_default_vocabularies,
    parse,
    validate_round_trip,
)
from .render import RenderError, compose

try:
    from .context import get_grammar_context
except ImportError:  # pragma: no cover - generated file absent during build
    pass

try:
    from .tag_types import TAG_TO_PHYSICS_DOMAIN, PhysicsDomain
except ImportError:  # pragma: no cover - generated file absent during build
    pass

# Friendly aliases to match tests
compose_name = compose_standard_name
parse_name = parse_standard_name

__all__ = [
    "NonCanonicalNameError",
    "TOKEN_PATTERN",
    "UnknownBaseTokenError",
    "compose_standard_name",
    "parse_standard_name",
    "compose_name",
    "parse_name",
    "get_grammar_context",
    "normalize_standard_name",
    "validate_forbidden_patterns",
    "value_of",
    "enum_values",
    "coerce_enum",
    "BinaryOperator",
    "Component",
    "GenericPhysicalBase",
    "GeometricBase",
    "Object",
    "PhysicsDomain",
    "Position",
    "Process",
    "Subject",
    "StandardName",
    "TAG_TO_PHYSICS_DOMAIN",
    "Transformation",
    # Grammar API
    "Diagnostic",
    "ParseError",
    "ParseResult",
    "RenderError",
    "StandardNameIR",
    "Vocabularies",
    "compose",
    "load_default_vocabularies",
    "parse",
    "validate_round_trip",
]
