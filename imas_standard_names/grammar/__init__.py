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
from .support import TOKEN_PATTERN, value_of
from .types import Component, Position, Process, Subject

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
    "Component",
    "Position",
    "Process",
    "Subject",
    "StandardName",
]
