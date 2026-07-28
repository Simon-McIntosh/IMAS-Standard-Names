---
applyTo: '**'
---

# GitHub Copilot Instructions for IMAS Standard Names

## What This Repository Owns

This is the grammar library: the controlled vocabulary, the parser and
renderer, catalog validation, and the documentation site. It does not create
standard names, and it does not serve tools to AI assistants — both belong to
[imas-codex](https://github.com/iterorganization/imas-codex).

### Core Principle

Never edit catalog YAML by hand. Names are minted, edited, and persisted
through imas-codex's `sn` pipeline, which calls this repository's grammar API.

### Working Here

Read and change source files when:

- Extending the grammar, vocabulary, or parser
- Fixing grammar validation logic
- Working on the catalog build or the documentation site
- Developing tests

## Key Python Entry Points

```python
from imas_standard_names.grammar import parse, compose
from imas_standard_names.grammar.context import get_grammar_context
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names import canonical_unit
```

- `parse` / `compose` — the grammar round trip; every name must survive it
- `get_grammar_context()` — grammar rules and vocabulary for LLM pipelines
- `StandardNameCatalog` — catalog query
- `canonical_unit()` — the single unit authority

Command line: `standard-names` (build, search, serve the site),
`validate_catalog`, `build-grammar`, `generate-schema`.

## Development Standards

- Use `uv run` for all Python commands
- Python 3.12+ (3.13 recommended)
- Async with `anyio`
- Pydantic for data models
- Test coverage target: 100%

## Complete Documentation

See `AGENTS.md` for comprehensive development guidelines including:
- Fusion physics and geometry context
- Standard name grammar rules
- Common pitfalls to avoid
- Project structure and setup
- Python style guide
- Development workflow
- Testing standards

## Quick Reference

- **Project root**: `/home/ITER/mcintos/Code/imas-standard-names`
- **Standard names catalog**: Separate repository ([imas-standard-names-catalog](https://github.com/iterorganization/imas-standard-names-catalog))
- **Tests**: `tests/` (mirror source structure)
- **Grammar spec**: `imas_standard_names/grammar/specification.yml`
