[![pre-commit][pre-commit-badge]][pre-commit-link]
[![Ruff][ruff-badge]][ruff-link]
[![Python versions][python-badge]][python-link]
[![CI/CD status][build-deploy-badge]][build-deploy-link]
[![Coverage status][codecov-badge]][codecov-link]
[![Documentation][docs-badge]][docs-link]

# IMAS Standard Names

Grammar library for IMAS Standard Names — a controlled vocabulary for fusion data variables.

This repository owns the grammar: the controlled vocabulary, the parser and
renderer, catalog validation, and the documentation site. AI-assistant tools
over standard names are served by
[imas-codex](https://github.com/iterorganization/imas-codex).

## Quick Start

```bash
pip install imas-standard-names
```

### Python Library

```python
from imas_standard_names import StandardNameIR, compose, parse
from imas_standard_names.repository import StandardNameCatalog

catalog = StandardNameCatalog()
entry = catalog.get("electron_temperature")
print(f"{entry.name}: {entry.unit} — {entry.description}")

# Strict parsing is the validity oracle for both flat names and recursive
# operator expressions.
result = parse("square_of_inverse_of_pressure", strict=True)
assert isinstance(result.ir, StandardNameIR)
assert [operator.op for operator in result.ir.operators] == ["square", "inverse"]
assert compose(result.ir) == "square_of_inverse_of_pressure"
```

## Installation

The tools and catalog are distributed separately:

| Package | Purpose |
|---------|---------|
| `imas-standard-names` | Grammar library, parser, validation |
| `imas-standard-names-catalog` | Standard names catalog (YAML + SQLite) |

### Basic Installation

```bash
# Tools + catalog (recommended)
pip install imas-standard-names[catalog]

# Tools only
pip install imas-standard-names
```

### Catalog Options

The catalog can be accessed in several ways:

```bash
# Option 1: Install catalog package (recommended)
pip install imas-standard-names-catalog

# Option 2: Download pre-built database
wget https://github.com/iterorganization/imas-standard-names-catalog/releases/latest/download/catalog.db
export STANDARD_NAMES_CATALOG_DB=./catalog.db

# Option 3: Clone catalog repository (for development)
git clone https://github.com/iterorganization/imas-standard-names-catalog.git
export STANDARD_NAMES_CATALOG_ROOT=./imas-standard-names-catalog/standard_names
```

### Development Setup

```bash
git clone https://github.com/iterorganization/imas-standard-names.git
cd imas-standard-names
uv sync
```

## Architecture

This project uses a two-repository architecture:

- **[imas-standard-names](https://github.com/iterorganization/imas-standard-names)** (this repo): Grammar library, parser, validation, Python API
- **[imas-standard-names-catalog](https://github.com/iterorganization/imas-standard-names-catalog)**: YAML source files and pre-built SQLite database

Name *generation* is handled by [imas-codex](https://github.com/iterorganization/imas-codex), which uses ISN's grammar API to mint candidates.

This separation allows independent versioning — catalog content, tooling, and generation logic evolve separately.

## Documentation

Full documentation: **[iterorganization.github.io/IMAS-Standard-Names](https://iterorganization.github.io/IMAS-Standard-Names/)**

- [Grammar Reference](https://iterorganization.github.io/IMAS-Standard-Names/grammar-reference/) — naming rules and vocabulary
- [Guidelines](https://iterorganization.github.io/IMAS-Standard-Names/guidelines/) — patterns and conventions
- [Quick Start](https://iterorganization.github.io/IMAS-Standard-Names/development/quickstart/) — getting started
- [Architecture](docs/architecture/boundary.md) — project boundary and API contract

## Python API

| Entry point | Purpose |
|------|---------|
| `imas_standard_names.parse(name, strict=True)` | Authoritative validation for flat and recursively ordered grammar |
| `imas_standard_names.parse(name)` | Diagnostic parse into a lossless `StandardNameIR` |
| `imas_standard_names.compose` | Render a `StandardNameIR` into its canonical spelling |
| `imas_standard_names.StandardNameIR` | Public recursive representation; operator lists are outermost first |
| `imas_standard_names.grammar.model.parse_standard_name` | Strict-validating projection into the flat `StandardName` facade; may reject a valid ordered tree it cannot represent |
| `imas_standard_names.validate_round_trip` | Diagnostic parse/render drift check; not a validity test |
| `imas_standard_names.grammar.context.get_grammar_context` | Grammar rules and vocabulary for LLM pipelines |
| `imas_standard_names.repository.StandardNameCatalog` | Query the catalog |
| `imas_standard_names.canonical_unit` | Canonical unit authority |
| `standard-names` (CLI) | Build, search, and serve the catalog site |
| `validate_catalog` (CLI) | Check catalog integrity and grammar compliance |

Tools that expose these over the Model Context Protocol live in
[imas-codex](https://github.com/iterorganization/imas-codex).

## License

MIT

[python-badge]: https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue
[python-link]: https://www.python.org/downloads/
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json
[ruff-link]: https://docs.astral.sh/ruff/
[pre-commit-badge]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
[pre-commit-link]: https://github.com/pre-commit/pre-commit
[build-deploy-badge]: https://img.shields.io/github/actions/workflow/status/iterorganization/IMAS-Standard-Names/test.yml?branch=main&color=brightgreen&label=CI%2FCD
[build-deploy-link]: https://codecov.io/gh/iterorganization/IMAS-Standard-Names/tests/main
[codecov-badge]: https://codecov.io/gh/iterorganization/IMAS-Standard-Names/graph/badge.svg
[codecov-link]: https://codecov.io/gh/iterorganization/IMAS-Standard-Names
[docs-badge]: https://img.shields.io/badge/docs-online-brightgreen
[docs-link]: https://iterorganization.github.io/IMAS-Standard-Names/
