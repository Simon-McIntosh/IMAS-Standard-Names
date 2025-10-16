# IMAS Standard Names

Welcome to the IMAS Standard Names documentation. This project defines a structured, machine-parseable naming convention for fusion data variables.

## Quick Links

- **[Grammar Reference](grammar-reference.md)** - Complete auto-generated grammar vocabulary and rules
- **[Guidelines](guidelines.md)** - Naming conventions and best practices
- **[Specification](specification.md)** - Formal grammar specification and validation rules
- **[Quick Start](quickstart.md)** - Step-by-step guide to adding new standard names
- **[Style Guide](style-guide.md)** - Detailed authoring guidelines
- **[IMAS Magnetics Example](magnetics-example.md)** - Worked example mapping IMAS paths to standard names

## Overview

The IMAS Standard Names system provides:

- **Deterministic parsing** of variable names into structured components
- **Controlled vocabularies** for segments (components, subjects, positions, processes, basis)
- **Validation rules** to ensure consistency and correctness
- **Single source of truth** in `grammar.yml` with auto-generated code and documentation

## Grammar Summary

The canonical naming pattern:

```text
[<component>_component_of]? [<subject>]? <base>
[of_<object> | from_<source>]?
[of_<geometry> | at_<position>]?
[due_to_<process>]?
```

**Key distinctions:**

- **`of_<object>`** — intrinsic property OF hardware/equipment (e.g., `area_of_flux_loop`)
- **`from_<source>`** — measurement/signal FROM device (e.g., `voltage_from_flux_loop`)
- **`of_<geometry>`** — geometric property OF a spatial object (e.g., `major_radius_of_plasma_boundary`)
- **`at_<position>`** — field quantity evaluated AT a location (e.g., `electron_temperature_at_magnetic_axis`)

### Current Vocabularies

{{ grammar_all_vocabularies() }}

See the [Grammar Reference](grammar-reference.md) for complete details on all vocabularies, segment rules, and examples.

## Getting Started

1. Review the [Grammar Reference](grammar-reference.md) to understand available vocabularies
2. Follow the [Quick Start](quickstart.md) guide to create your first standard name
3. Consult the [Guidelines](guidelines.md) for naming conventions
4. Use the [Style Guide](style-guide.md) for detailed authoring rules

## Standard Names Catalog

The current catalog of standard names is maintained in `imas_standard_names/resources/standard_names/` with individual YAML files organized by domain:

- **magnetic_field/** - Magnetic field vectors and components
- **plasma/** - Plasma parameters (temperature, density, etc.)
- **equilibrium/** - Equilibrium reconstruction quantities

For programmatic access to the catalog, use the Python API:

```python
from imas_standard_names.repository import StandardNameRepository

repo = StandardNameRepository()
name = repo.get("electron_temperature")
print(f"{name.unit}: {name.description}")
```

## Contributing

See [Contributing Guidelines](contributing.md) for information on proposing new standard names or modifications to the grammar.
