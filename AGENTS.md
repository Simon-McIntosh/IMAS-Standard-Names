# Project Overview

IMAS Standard Names maintains a controlled vocabulary for standardizing data in the ITER Modelling and Analysis Suite (IMAS). The project manages grammar-validated names for physics and geometrical quantities, diagnostics, and spatial properties using Python + MCP (Model Context Protocol) tools.

**Domain**: Fusion energy data standardization  
**Tech Stack**: Python 3.12+, Pydantic, SQLite, YAML, MCP servers  
**Key Concept**: All standard names follow strict grammar rules for describing physics and geometrical quantities

## Fusion Physics and Geometry Context

**Essential concepts for agents working with standard names:**

- **Physics Quantities**: Plasma properties (temperature, density, pressure, magnetic field)
- **Geometrical Quantities**: Spatial positions, shapes, extents, and coordinate transformations
- **Coordinates**: Cylindrical (R,φ,Z), plus poloidal/toroidal directions
- **IMAS DD**: ITER Data Dictionary - authoritative source for physics and geometry definitions
- **Diagnostics**: Instruments that measure both plasma properties and geometric positions

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
physics_domain: core_plasma_physics # Required: PhysicsDomain enum value
tags: [measured] # Optional: secondary cross-cutting classification
status: draft
description: Starts with capital, under 120 chars
```

**`physics_domain` is required**: Must be a valid `PhysicsDomain` enum value (32 values). `tags` is optional, used only for secondary cross-cutting classification (e.g., "measured", "cylindrical_coordinates").

## Common Pitfalls to Avoid

1. **Grammar violations**: Names must follow canonical pattern exactly
2. **Wrong base combinations**: Never use `component` with `geometric_base`
3. **Missing physics_domain**: Must be a valid `PhysicsDomain` value, not a tag
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

docs/                # User documentation
tests/               # Test suite
```

**Catalog data** is maintained in a separate repository:
[imas-standard-names-catalog](https://github.com/iterorganization/imas-standard-names-catalog)

**Organization principles**:
- Mirror test structure to source structure
- Group related functionality in focused modules
- Keep modules cohesive and loosely coupled

## Project Setup

### Terminal Usage

**Python execution**: Use `uv run` for all Python commands to ensure virtual environment is activated automatically.

```bash
# Run Python scripts
uv run python script.py

# Run modules
uv run python -m imas_standard_names.cli

# Run pytest
uv run pytest

# Wrong: Don't use system Python or manual activation
python script.py                    # May use wrong Python
source .venv/bin/activate && python # Unnecessary
```

**Working directory**: Commands assume you're in the project root (`/home/ITER/mcintos/Code/imas-standard-names`). Do NOT prefix with `cd /path/to/project &&`.

```bash
# ✅ Correct
uv run pytest

# ❌ Wrong - unnecessary cd
cd /home/ITER/mcintos/Code/imas-standard-names && uv run pytest
```

### Package Management
- **Package manager**: `uv`
- **Add dependencies**: `uv add <package>`
- **Add dev dependencies**: `uv add --dev <package>`
- **Sync and lock**: `uv sync`

### CLI Tools
- **Framework**: Use `click` for all CLI tools
- **Progress display**: Use `rich` for progress bars and formatted output
- **Entry points**: Configure in `[project.scripts]` section of `pyproject.toml`

### Code Quality
- **Pre-commit hooks**: Enabled for all commits
- **Linting & formatting**: `ruff` (configuration in `pyproject.toml`)

### Security
- **Never expose `.env` file contents**: Do not read, display, or include `.env` in any output
- `.env` contains sensitive credentials and is gitignored
- Never commit sensitive data to YAML files
- Validate all user inputs through Pydantic models
- All file operations should use absolute paths

### Version Control
- **Branch naming**: Use `main` as default branch
- **GitHub CLI**: `gh` is installed in `~/.local/bin` and available in PATH
- **Authentication**: SSH
- **Remotes**: `origin` is the user's fork, `upstream` is `iterorganization/IMAS-Standard-Names`
- **Versioning**: Derived from git tags via `hatch-vcs` — no version numbers in source files

**Conventional commits** — use `type: description` format. Signal breaking changes with `BREAKING CHANGE:` in the commit body, not with `!` suffix (shell history expansion breaks it).

```
feat: add physics_domain field to standard name entries
fix: correct validation of secondary tags
docs: update grammar reference for geometric bases
refactor: simplify catalog renderer grouping logic
test: add parameterized tests for provenance validation
chore: update ruff configuration
```

For breaking changes:
```
feat: replace tags with physics_domain field

BREAKING CHANGE: tags[0] replaced by dedicated physics_domain field.
```

**Git workflow**:
```bash
git status                      # Check current state
git add -A                      # Stage all changes
git commit -m 'message'         # Use single quotes (avoids bash ! expansion)
git push origin main            # Push to fork
git pull origin main            # Pull latest changes
```

**Common gh commands**:
```bash
gh pr create --title "..." --body "..."             # Create pull request
gh issue create --title "..." --body "..."          # Create issue
gh repo view --web                                  # Open repo in browser
```

### Release Workflow

Releases use a two-state workflow (Stable ↔ RC) managed by the `standard-names release` CLI. Versioning is entirely tag-driven — the project tag is the version. Never put version numbers in source files.

**How it works**: The CLI creates an annotated git tag and pushes it to `upstream`, which triggers the GitHub Actions publish workflow to build and upload to PyPI.

```bash
# Check current release state and available commands
uv run standard-names release status

# Start a new RC series (e.g., v0.6.0 → v0.7.0rc1)
uv run standard-names release --bump minor -m 'Add physics_domain field'

# Increment RC (e.g., v0.7.0rc1 → v0.7.0rc2)
uv run standard-names release -m 'Fix validation edge case'

# Finalize RC to stable (e.g., v0.7.0rc2 → v0.7.0)
uv run standard-names release --final -m 'Production release'

# Direct patch release, skip RC (e.g., v0.7.0 → v0.7.1)
uv run standard-names release --bump patch --final -m 'Hotfix'

# Dry run — validate without tagging
uv run standard-names release --bump minor --dry-run -m 'Test'
```

**Pre-flight checks** (automatic): The release CLI verifies you are on `main`, the working tree is clean, local is synced with `upstream/main`, and CI checks have passed for HEAD. It will refuse to tag if any check fails (unless `--dry-run`).

**Release procedure**:
1. Ensure all changes are committed and pushed to `upstream/main`
2. Run `uv run standard-names release status` to see current state
3. Run the appropriate release command with `-m 'description'`
4. Monitor the publish workflow: https://github.com/iterorganization/IMAS-Standard-Names/actions
5. Verify the package appears on PyPI after the workflow completes

## Development Workflow

### Environment Setup

Use `uv` for all development tasks:

```bash
# Set up environment
uv venv
uv sync

# Install dependencies
uv sync --all-extras

# Install pre-commit hooks (required for contributors)
uv run pre-commit install
```

### Build and Test Commands

```bash
# Run tests (100% coverage required for new code)
uv run pytest --cov

# Lint and format code
uv run ruff check --fix
uv run ruff format

# Validate standard names catalog (requires catalog to be configured)
uv run validate_catalog $STANDARD_NAMES_CATALOG_ROOT

# Start MCP server
uv run standard-names-mcp

# Generate grammar types
uv run python -m imas_standard_names.grammar_codegen.generate
```

### Testing Standards

- All tests in `/tests/` directory using pytest
- Use `uv run pytest --cov` to run with coverage
- New code requires 100% test coverage
- Tests must pass before commit
- Use descriptive test names: `test_<functionality>`

**Test philosophy**:
- **Test behavior, not implementation**: Focus on what the code does, not how it does it
- **Test public interfaces**: Avoid testing private methods or internal state
- **Keep tests flexible**: Early-stage tests should allow implementation changes without breaking
- **Use black-box testing**: Test inputs and outputs without depending on internal structure

**Best practices**:
- Prefer integration tests over unit tests where practical
- Mock external dependencies (databases, file system, network) but avoid excessive mocking
- Test edge cases and error conditions
- Use parameterized tests for multiple input scenarios
- Keep test names descriptive: `test_extract_features_raises_error_for_empty_data`

```python
# Good: Tests behavior through public interface
async def test_search_returns_relevant_results():
    results = await search("magnetic_field")
    assert len(results) > 0
    assert results[0].name.startswith("magnetic_")

# Avoid: Tests implementation details
async def test_search_uses_correct_index():
    # Don't test internal implementation
    ...
```

## Python Style Guide

### Version & Modern Practices
- **Python version**: 3.12+ (3.13 recommended)
- Follow modern Python standards and relevant PEPs
- No `from __future__ import` statements
- No `from typing import` or `if TYPE_CHECKING` guards

### Import Style
```python
# All imports at top of file, ordered:
# 1. Standard library
# 2. Third-party packages
# 3. Local imports

import os
import sys

import anyio
import pydantic

from imas_standard_names.models import StandardName
```

### Type Annotations
- Type all functions and classes
- Use modern type syntax (e.g., `list[str]` not `List[str]`)

```python
def process_features(items: list[str], threshold: float = 0.5) -> dict[str, int]:
    """Process items and return counts."""
    ...
```

### Data Structures
- **Schemas**: Use `pydantic` models
- **Data classes**: Use `dataclasses` for non-schema classes
- **Avoid**: Bare `class` definitions where dataclasses/pydantic apply

```python
from dataclasses import dataclass

import pydantic


class FeatureSchema(pydantic.BaseModel):
    """Feature data schema."""
    name: str
    description: str
    embedding: list[float]


@dataclass
class Config:
    """Application configuration."""
    timeout: float
    retries: int
```

### Asynchronous Programming
- **Library**: Use `anyio` for async operations
- **When to use async**: All separable I/O-bound processes
  - Data retrieval
  - Network requests
  - File I/O operations
  - Database queries
  - MCP tool operations

```python
import anyio


async def load_data(file_path: str) -> Data:
    """Load data asynchronously."""
    async with anyio.open_file(file_path) as f:
        content = await f.read()
    return Data.parse(content)
```

### Design Patterns
- **Prefer**: Composition over inheritance
- **Use inheritance**: Only when it provides clear benefits
- Favor explicit over implicit

### Error Handling

**Best practices**:
- Use specific exception types, not bare `except:`
- Let exceptions propagate unless you can handle them meaningfully
- Validate inputs early with clear error messages
- Use context managers for resource cleanup

```python
async def validate_standard_name(name: str) -> bool:
    """Validate a standard name against grammar rules.
    
    Raises:
        ValueError: If name is empty
        GrammarError: If name violates grammar rules
    """
    if not name.strip():
        raise ValueError("name cannot be empty")
    
    try:
        return await grammar_validator.validate(name)
    except ValidationError as e:
        raise GrammarError(f"Invalid grammar: {e}") from e
```

**Exception guidelines**:
- Raise built-in exceptions when appropriate (`ValueError`, `TypeError`, etc.)
- Create custom exceptions for domain-specific errors
- Include context in exception messages
- Use exception chaining with `from` to preserve stack traces

### Code Style Guidelines

- Use absolute imports: `from imas_standard_names.module import Class`
- Place all imports at the top of the file unless properly justified elsewhere
- All MCP tool methods must be `async`
- Return structured data via `.model_dump()` or error dictionaries with schema
- 100% test coverage required for all new/modified code
- Follow existing patterns in `tools/` directory for MCP tool development
- **Never use ALL CAPS for emphasis** in documentation, docstrings, or user-facing text
  - Use **bold**, _italic_, or `code` formatting instead
  - Exception: acronyms (e.g., IMAS, MCP, CF) and constants in code

### Path Resolution

**Prefer importlib.resources over Path(__file__)** for resolving package paths:

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

## Documentation Standards
- Include concise docstrings for all public methods and classes
- Add usage examples in markdown format where helpful
- Document exceptions that may be raised

```python
def parse_standard_name(name: str) -> dict[str, str]:
    """Parse a standard name into its grammatical components.
    
    ## Example
    
    ```python
    parts = parse_standard_name("radial_component_of_magnetic_field")
    print(parts["component"])  # "radial"
    ```
    
    Raises:
        ValueError: If name is invalid
    """
    ...
```

### Code Philosophy

**Green field project**:
- No backward compatibility constraints
- Avoid terms like "new", "refactored", "enhanced", "replaces" in:
  - Comments
  - Module names
  - Class names
  - Function names

Write code as if it's always been this way.

## Links to Documentation

- Grammar rules: `/docs/grammar-reference.md`
- Style guidelines: `/docs/development/style-guide.md`
- User guidelines: `/docs/guidelines.md`
- Contributing: `CONTRIBUTING.md`
