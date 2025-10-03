# IMAS Standard Names

Welcome to the IMAS Standard Names documentation. This project defines a structured, machine-parseable naming convention for fusion data variables.

## Quick Links

- **[Grammar Reference](grammar-reference.md)** - Complete auto-generated grammar vocabulary and rules
- **[Guidelines](guidelines.md)** - Naming conventions and best practices
- **[Specification](specification.md)** - Formal grammar specification and validation rules
- **[Quick Start](quickstart.md)** - Step-by-step guide to adding new standard names
- **[Style Guide](style-guide.md)** - Detailed authoring guidelines

## Overview

The IMAS Standard Names system provides:

- **Deterministic parsing** of variable names into structured components
- **Controlled vocabularies** for segments (components, subjects, positions, processes, basis)
- **Validation rules** to ensure consistency and correctness
- **Single source of truth** in `grammar.yml` with auto-generated code and documentation

## Grammar Summary

The canonical naming pattern:

```text
[component_] [subject_] base [in_<basis>_basis] [of_<target> | at_<position>] [due_to_<process>]
```

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

See [Contributing Guidelines](../CONTRIBUTING.md) for information on proposing new standard names or modifications to the grammar.
