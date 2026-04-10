"""JSON schema contract for StandardNameEntry data models."""

from .generate import generate_entry_schema
from .validate import validate_against_schema

__all__ = [
    "generate_entry_schema",
    "validate_against_schema",
]
