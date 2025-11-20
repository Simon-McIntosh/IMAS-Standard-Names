"""Runtime helpers and types for IMAS standard names.

This package hosts hand-written behavior separated from generated
vocabulary/metadata (grammar_models).
"""

from __future__ import annotations

from .model import (
    StandardName,
    compose_standard_name,
    parse_standard_name,
)
from .model_types import Component, Position, Process, Subject
from .support import TOKEN_PATTERN, coerce_enum, enum_values, value_of

# Friendly aliases to match tests
compose_name = compose_standard_name
parse_name = parse_standard_name

__all__ = [
    "TOKEN_PATTERN",
    "compose_standard_name",
    "parse_standard_name",
    "compose_name",
    "parse_name",
    "value_of",
    "enum_values",
    "coerce_enum",
    "Component",
    "Position",
    "Process",
    "Subject",
    "StandardName",
]
