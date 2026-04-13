"""Runtime helpers and types for IMAS standard names.

This package hosts hand-written behavior separated from generated
vocabulary/metadata (grammar_models).
"""

from .model import (
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
from .context import get_grammar_context
from .support import TOKEN_PATTERN, coerce_enum, enum_values, value_of

try:
    from .tag_types import TAG_TO_PHYSICS_DOMAIN, PhysicsDomain
except ImportError:  # pragma: no cover - generated file absent during build
    pass

# Friendly aliases to match tests
compose_name = compose_standard_name
parse_name = parse_standard_name

__all__ = [
    "TOKEN_PATTERN",
    "compose_standard_name",
    "parse_standard_name",
    "compose_name",
    "parse_name",
    "get_grammar_context",
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
]
