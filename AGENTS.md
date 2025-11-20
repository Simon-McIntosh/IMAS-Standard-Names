# Project Overview

IMAS Standard Names is a fusion energy research project that maintains a controlled vocabulary for standardizing data in the ITER Modelling and Analysis Suite (IMAS). The project manages grammar-validated names for physics and geometrical quantities, diagnostics, and spatial properties using Python + MCP (Model Context Protocol) tools.

**Domain**: Fusion energy data standardization  
**Tech Stack**: Python 3.12+, Pydantic, SQLite, YAML, MCP servers  
**Key Concept**: All standard names follow strict grammar rules for describing physics and geometrical quantities

## Development Environment Setup

Use `uv` for all development tasks:

```bash
# Set up environment
uv venv
uv sync

# Activate virtual environment (Windows)
.venv\Scripts\Activate.ps1

# Install dependencies
uv sync --all-extras
```

## Build and Test Commands

```bash
# Run tests (100% coverage required for new code)
uv run pytest --cov

# Lint and format code
uv run ruff check --fix
uv run ruff format

# Validate standard names catalog
uv run python -m imas_standard_names.validation.cli validate_catalog resources/standard_names

# Build SQLite catalog from YAML files
uv run python -m imas_standard_names.cli.build_catalog resources/standard_names

# Start MCP server
uv run standard-names-mcp

# Generate grammar types
uv run python -m imas_standard_names.grammar_codegen.generate
```

## Code Style Guidelines

- Use absolute imports: `from imas_standard_names.module import Class`
- Place all imports at the top of the file unless properly justified elsewhere
- All MCP tool methods must be `async`
- Return structured data via `.model_dump()` or error dictionaries with schema
- 100% test coverage required for all new/modified code
- Follow existing patterns in `tools/` directory for MCP tool development
- **Never use ALL CAPS for emphasis** in documentation, docstrings, or user-facing text
  - Use **bold**, _italic_, or `code` formatting instead
  - Exception: acronyms (e.g., IMAS, MCP, CF) and constants in code

### Path Resolution Best Practices

**Prefer importlib.resources over Path(**file**)** for resolving package paths:

```python
# ❌ Avoid: Path(__file__).resolve().parents[1] / "grammar"
# ✅ Preferred: importlib.resources.files("imas_standard_names.grammar")

import importlib.resources
from pathlib import Path

grammar_package_path = Path(importlib.resources.files("imas_standard_names.grammar"))
spec_path = grammar_package_path / "specification.yml"
```

**Why importlib.resources is preferred:**

- Works correctly with zip imports and frozen packages
- More robust in different installation contexts
- Future-proof against Python packaging changes
- Better performance in most scenarios

**Note on Code Generation:**
Generated files (model_types.py, constants.py, tag_types.py, field_schemas.py) are formatted by pre-commit hooks to ensure consistency with project formatting standards. The generate script produces code that follows ruff guidelines, but actual formatting is applied by the project's pre-commit configuration.

### MCP Tool Pattern

```python
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import BaseTool

class MyTool(BaseTool):
    @mcp_tool(description="Clear single sentence description of purpose for llm")
    async def tool_method(self, param: str, ctx: Context | None = None):
        try:
            # Implementation
            return result.model_dump()
        except Exception as e:
            return {
                "error": type(e).__name__,
                "message": str(e),
                "schema": input_schema(),
                "examples": example_inputs()
            }
```

## Standard Name Grammar Rules

Critical distinctions for naming:

- `component` + `physical_base`: `radial_component_of_magnetic_field`
- `coordinate` + `geometric_base`: `radial_position_of_flux_loop`
- `of_object` vs `from_source`: intrinsic properties vs measurements
- `at_position` vs `of_geometry`: evaluated at location vs property of object

### YAML Structure Requirements

```yaml
name: follows_grammar_precisely
kind: scalar
unit: SI_unit # Never include units in name
tags: [primary_tag, secondary_tags] # Order matters: primary first
status: draft
description: Starts with capital, under 120 chars
```

**Tag ordering is critical**: Primary tag must be `tags[0]`, secondary tags follow.

## Testing Instructions

- All tests in `/tests/` directory using pytest
- Use `uv run pytest --cov` to run with coverage
- New code requires 100% test coverage
- Tests must pass before commit
- Use descriptive test names: `test_<functionality>`

## Common Pitfalls to Avoid

1. **Grammar violations**: Names must follow canonical pattern exactly
2. **Wrong base combinations**: Never use `component` with `geometric_base`
3. **Incorrect tag order**: Primary tag must be first in list
4. **Units in names**: Use YAML `unit` field, not in name text
5. **Synchronous MCP tools**: All tool methods must be `async`
6. **Missing error schemas**: Always return structured errors with examples
7. **Direct YAML file editing**: Never edit standard name YAML files directly - always use MCP tools (`create_standard_names`, `edit_standard_names`, `write_standard_names`) to ensure validation and consistency

## Project Structure

```
imas_standard_names/
├── tools/           # MCP tool implementations
├── grammar/         # Grammar parsing and validation
├── catalog/         # SQLite catalog management
├── repository.py    # Main repository facade
├── models.py        # Pydantic data models
└── validation/      # Validation logic

resources/standard_names/  # Authoritative YAML files
docs/                     # User documentation
tests/                    # Test suite
```

## Fusion Physics and Geometry Context

**Essential concepts for agents working with standard names:**

- **Physics Quantities**: Plasma properties (temperature, density, pressure, magnetic field)
- **Geometrical Quantities**: Spatial positions, shapes, extents, and coordinate transformations
- **Coordinates**: Cylindrical (R,φ,Z), plus poloidal/toroidal directions
- **IMAS DD**: ITER Data Dictionary - authoritative source for physics and geometry definitions
- **Diagnostics**: Instruments that measure both plasma properties and geometric positions

## Security Considerations

- Never commit sensitive data to YAML files
- Validate all user inputs through Pydantic models
- Use `uv` virtual environment for all operations
- All file operations should use absolute paths

## Links to Documentation

- Grammar rules: `/docs/grammar-reference.md`
- Style guidelines: `/docs/development/style-guide.md`
- User guidelines: `/docs/guidelines.md`
- Contributing: `CONTRIBUTING.md`
