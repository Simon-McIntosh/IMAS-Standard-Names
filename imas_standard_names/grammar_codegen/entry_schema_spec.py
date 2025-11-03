"""Load and normalize the entry schema specification.

Similar to spec.py but specialized for entry_schema section in specification.yml.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Import IncludeLoader from spec.py to handle !include directives
from imas_standard_names.grammar_codegen.spec import IncludeLoader

# Path to specification.yml
_GRAMMAR_PACKAGE_DIR = Path(__file__).parent.parent / "grammar"
_SPECIFICATION_FILENAME = "specification.yml"


@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single catalog entry field."""

    name: str
    required: bool
    field_type: str
    description: str
    pattern: str | None = None
    max_length: int | None = None
    examples: tuple[str | dict | list, ...] = ()
    guidance: dict[str, Any] | None = None

    def __post_init__(self):
        # Ensure guidance is a dict
        if self.guidance is None:
            object.__setattr__(self, "guidance", {})


@dataclass(frozen=True)
class EntrySchemaSpec:
    """Specification for catalog entry schema from specification.yml."""

    fields: tuple[FieldSpec, ...]
    type_specific: dict[str, dict[str, Any]]
    provenance_modes_info: dict[str, Any] | None = None

    @property
    def field_map(self) -> dict[str, FieldSpec]:
        """Return field specifications indexed by field name."""
        return {field.name: field for field in self.fields}

    @classmethod
    def load(cls) -> EntrySchemaSpec:
        """Load entry schema specification from specification.yml."""
        spec_path = _GRAMMAR_PACKAGE_DIR / _SPECIFICATION_FILENAME
        with open(spec_path, encoding="utf-8") as handle:
            data = yaml.load(handle, Loader=IncludeLoader) or {}

        entry_schema_raw = data.get("entry_schema", {})
        fields_raw = entry_schema_raw.get("fields", {})
        type_specific_raw = entry_schema_raw.get("type_specific", {})

        # Parse field specifications
        fields: list[FieldSpec] = []
        for field_name, field_data in fields_raw.items():
            if not isinstance(field_data, dict):
                continue

            # Extract examples (can be list of strings, dicts, or lists)
            examples_raw = field_data.get("examples", [])
            examples: list[str | dict | list] = []
            if isinstance(examples_raw, list):
                for ex in examples_raw:
                    if isinstance(ex, (str, dict, list)):
                        examples.append(ex)

            # Extract guidance section
            guidance = field_data.get("guidance", {})
            if not isinstance(guidance, dict):
                guidance = {}

            fields.append(
                FieldSpec(
                    name=field_name,
                    required=bool(field_data.get("required", False)),
                    field_type=str(field_data.get("type", "string")),
                    description=str(field_data.get("description", "")),
                    pattern=field_data.get("pattern"),
                    max_length=field_data.get("max_length"),
                    examples=tuple(examples),
                    guidance=guidance,
                )
            )

        # Extract type-specific requirements (scalar/vector/metadata)
        type_specific: dict[str, dict[str, Any]] = {}
        if isinstance(type_specific_raw, dict):
            type_specific = {
                kind: (spec if isinstance(spec, dict) else {})
                for kind, spec in type_specific_raw.items()
            }

        # Extract provenance modes info from provenance field
        provenance_modes_info: dict[str, Any] | None = None
        provenance_field = fields_raw.get("provenance", {})
        if isinstance(provenance_field, dict) and "modes" in provenance_field:
            provenance_modes_info = {
                "description": provenance_field.get("description", ""),
                "applicable_to": provenance_field.get("applicable_to", []),
                "note": provenance_field.get("note", ""),
                "modes": provenance_field.get("modes", {}),
            }

        return cls(
            fields=tuple(fields),
            type_specific=type_specific,
            provenance_modes_info=provenance_modes_info,
        )


__all__ = ["EntrySchemaSpec", "FieldSpec"]
