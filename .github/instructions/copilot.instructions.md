---
applyTo: '**'
---

# GitHub Copilot Instructions for IMAS Standard Names

## MCP-First Approach

This project provides MCP (Model Context Protocol) tools for working with IMAS standard names. Always prefer using MCP tools over direct file manipulation.

### Core Principle

Use MCP tools to interact with the standard names catalog. Never edit YAML files directly.

### Workflow

1. Use MCP tools to search, fetch, and validate standard names
2. Use `compose_standard_name` to build new names
3. Use `create_standard_names` and `edit_standard_names` for modifications
4. Use `write_standard_names` to persist changes (requires user permission)

### When to Read Files

Read source files ONLY when:
- Implementing new features in the codebase
- Modifying MCP tool implementations
- Debugging grammar validation logic
- Developing tests

Never read files for:
- Creating or editing standard names (use MCP tools)
- Understanding grammar rules (use `get_naming_grammar` tool)
- Searching the catalog (use `search_standard_names` tool)
- Validating names (use validation tools)

## Key MCP Tools

Available through the `imas-standard-names` MCP server:

```python
# Discovery and search
search_standard_names()      # Find names by concept
list_standard_names()        # List all available names
fetch_standard_names()       # Get complete metadata

# Grammar and composition
get_naming_grammar()         # Get grammar rules
compose_standard_name()      # Build valid names
parse_standard_name()        # Parse into components

# Creation and editing
create_standard_names()      # Create new entries
edit_standard_names()        # Modify existing entries
write_standard_names()       # Persist to disk (needs permission)

# Validation
check_standard_names()       # Validate existence
validate_catalog()           # Check catalog integrity
```

## Development Standards

- Use `uv run` for all Python commands
- Python 3.12+ (3.13 recommended)
- Async with `anyio`
- Pydantic for data models
- Test coverage target: 100%
- All MCP tool methods must be async

## Complete Documentation

See `AGENTS.md` for comprehensive development guidelines including:
- Fusion physics and geometry context
- Standard name grammar rules
- Common pitfalls to avoid
- Project structure and setup
- Python style guide
- MCP tool patterns
- Development workflow
- Testing standards

## Quick Reference

- **Project root**: `/home/ITER/mcintos/Code/imas-standard-names`
- **Standard names catalog**: Separate repository ([imas-standard-names-catalog](https://github.com/iterorganization/imas-standard-names-catalog))
- **Tests**: `tests/` (mirror source structure)
- **Grammar spec**: Accessible via `get_naming_grammar()` MCP tool
