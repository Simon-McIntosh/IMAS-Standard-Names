# IMAS Standard Names

MCP server and Python library for working with IMAS Standard Names — a controlled vocabulary for fusion data variables.

## About Standard Names

Standard names provide a controlled vocabulary for identifying physical quantities, diagnostic measurements, and geometric properties in fusion experiments. Each name includes:

- **Unique identifier** following grammar rules
- **Physical units** (SI-consistent)
- **Description** and detailed documentation
- **Category tags** for organization
- **Status** tracking (draft, active, deprecated)

## Standard Names Catalog

The catalog of standard names is maintained in a separate repository:

**[IMAS Standard Names Catalog](https://github.com/iterorganization/imas-standard-names-catalog)**

This separation allows:
- Independent versioning of catalog content
- Catalog updates without tooling releases
- Clear distinction between grammar rules and catalog entries

## Documentation

- **[Standard Names Catalog](catalog.md)** — Links to the catalog repository
- **[Grammar Reference](grammar-reference.md)** — Vocabulary and naming rules
- **[Guidelines](guidelines.md)** — Naming patterns and conventions
- **[Development Guides](development/quickstart.md)** — For contributors

## Quick Start

### MCP Server

```bash
# Install
pip install imas-standard-names[catalog]

# Run
standard-names-mcp
```

### Python Library

```python
from imas_standard_names import StandardNameCatalog

catalog = StandardNameCatalog()
entry = catalog.get("electron_temperature")
print(f"{entry.name}: {entry.unit} — {entry.description}")
```
