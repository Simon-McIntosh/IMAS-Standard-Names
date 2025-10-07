"""Demonstrate using the StandardName model.

Run with the project venv activated:
    python examples/standard_name_usage.py
"""

from __future__ import annotations

from imas_standard_names.grammar.model import (
    StandardName,
    compose_standard_name,
    parse_standard_name,
)
from imas_standard_names.grammar.types import (
    Component,
    Position,
    Process,
    Subject,
)


def examples() -> None:
    # Create from parts (using enums for clarity)
    sn = StandardName(
        component=Component.POLOIDAL,
        subject=Subject.ELECTRON,
        base="temperature",
        position=Position.CORE_REGION,
        process=Process.RADIATION,
    )
    print("Model:", sn)
    print("Composed name:", sn.compose())

    # Validate dict and compose directly
    name = compose_standard_name(
        {
            "component": Component.TOROIDAL,
            "subject": Subject.ION,
            "base": "velocity",
            "geometry": Position.MAGNETIC_AXIS,
        }
    )
    print("Composed (dict):", name)

    # Parse from string to model
    parsed = parse_standard_name(
        "poloidal_electron_temperature_at_core_region_due_to_radiation"
    )
    print("Parsed model:", parsed)

    # Compact dump (only set fields) useful for storage/LLMs
    print("Compact dump:", parsed.model_dump_compact())

    # JSON Schema (for LLM/tooling)
    print("JSON Schema title:", StandardName.model_json_schema().get("title"))


if __name__ == "__main__":
    examples()
