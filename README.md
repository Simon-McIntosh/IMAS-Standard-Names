[![pre-commit][pre-commit-badge]][pre-commit-link]
[![Ruff][ruff-badge]][ruff-link]
[![Python versions][python-badge]][python-link]
[![CI/CD status][build-deploy-badge]][build-deploy-link]
[![Coverage status][codecov-badge]][codecov-link]
[![Documentation][docs-badge]][docs-link]

# IMAS Standard Names

MCP server and Python library for working with IMAS Standard Names — a controlled vocabulary for fusion data variables.

## Quick Start

### MCP Server

Configure your AI assistant to use the standard names tools:

```bash
# Install the MCP server
uv tool install imas-standard-names

# Or with pip
pip install imas-standard-names
```

Add to your MCP configuration (e.g., Claude Desktop, VS Code):

```json
{
  "mcpServers": {
    "imas-standard-names": {
      "command": "standard-names-mcp"
    }
  }
}
```

### Python Library

```python
from imas_standard_names import StandardNameCatalog

catalog = StandardNameCatalog()
entry = catalog.get("electron_temperature")
print(f"{entry.name}: {entry.unit} — {entry.description}")
```

## Installation

The tools and catalog are distributed separately:

| Package | Purpose |
|---------|---------|
| `imas-standard-names` | MCP server, grammar, validation tools |
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

# Option 3: Clone catalog repository (for editing)
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

- **[imas-standard-names](https://github.com/iterorganization/imas-standard-names)** (this repo): MCP server, grammar, validation, Python API
- **[imas-standard-names-catalog](https://github.com/iterorganization/imas-standard-names-catalog)**: YAML source files and pre-built SQLite database

This separation allows independent versioning — catalog content evolves separately from tooling.

## Documentation

Full documentation: **[iterorganization.github.io/IMAS-Standard-Names](https://iterorganization.github.io/IMAS-Standard-Names/)**

- [Grammar Reference](https://iterorganization.github.io/IMAS-Standard-Names/grammar-reference/) — naming rules and vocabulary
- [Guidelines](https://iterorganization.github.io/IMAS-Standard-Names/guidelines/) — patterns and conventions
- [Quick Start](https://iterorganization.github.io/IMAS-Standard-Names/development/quickstart/) — creating new standard names

## MCP Tools

The MCP server provides tools for AI assistants to work with standard names:

### Discovery & Search
| Tool | Purpose |
|------|---------|
| `search_standard_names` | Find names by concept using semantic search |
| `list_standard_names` | List all names with filtering by status, tags, kind |
| `fetch_standard_names` | Get complete metadata for specific names |
| `check_standard_names` | Fast batch validation of name existence |

### Grammar & Schema
| Tool | Purpose |
|------|---------|
| `get_grammar` | Grammar rules, patterns, and composition guidance |
| `get_schema` | Entry schema for creating standard names |
| `get_vocabulary` | Controlled vocabulary tokens by segment |

### Composition & Parsing
| Tool | Purpose |
|------|---------|
| `compose_standard_name` | Build valid names from structured parts |
| `parse_standard_name` | Parse names into grammatical components |

### Editing & Persistence
| Tool | Purpose |
|------|---------|
| `create_standard_names` | Create new catalog entries (in-memory) |
| `edit_standard_names` | Modify, rename, or delete entries (in-memory) |
| `write_standard_names` | Persist pending changes to disk |

### Validation & Reference
| Tool | Purpose |
|------|---------|
| `validate_catalog` | Check catalog integrity and grammar |
| `manage_vocabulary` | Vocabulary gap detection and management |
| `get_tokamak_parameters` | Reference tokamak machine parameters |

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
