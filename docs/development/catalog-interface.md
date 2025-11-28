# Catalog Repository CLI Interface

This document defines the CLI interface between `imas-standard-names` and the `imas-standard-names-catalog` repository. The catalog repository is designed as a zero-code repository containing only YAML standard name definitions.

## Overview

The `imas-standard-names` package provides CLI commands that the catalog repository uses in its CI workflows:

| Command | Purpose | Exit Codes |
|---------|---------|------------|
| `validate_catalog` | Validate YAML files | 0=pass, 1=fail, 2=integrity issues |
| `standard-names build` | Build catalog.db | 0=success, 1=error |
| `standard-names catalog-site` | Generate standalone documentation site | 0=success, 1=error |

## Installation

The catalog repository should install `imas-standard-names` as a dependency:

```yaml
# In catalog repo pyproject.toml or requirements
dependencies:
  - imas-standard-names>=X.Y.Z
```

Or in CI:

```yaml
- run: uv pip install imas-standard-names
```

## CLI Commands

### Validate Catalog

Validates YAML structure, grammar, and quality checks.

```bash
validate_catalog <catalog_path> [OPTIONS]
```

**Arguments:**
- `catalog_path` — Path to directory containing YAML standard name files

**Options:**
- `--mode [auto|file|memory]` — Source mode (default: auto)
- `--quality-check/--no-quality-check` — Enable or disable quality checks (default: enabled). Requires `quality` extra: `pip install imas-standard-names[quality]`
- `--strict` — Fail validation on warnings, not just errors
- `--summary [text|json]` — Output machine-readable summary

**Examples:**

```bash
# Basic validation with quality checks
validate_catalog standard_names/

# Skip quality checks (faster, for quick validation)
validate_catalog standard_names/ --no-quality-check

# CI-friendly summary output
validate_catalog standard_names/ --summary text
# Output: ✓ Validated 305 entries (0 errors, 134 warnings)

# Strict mode: fail on any warnings
validate_catalog standard_names/ --strict --summary text

# JSON output for programmatic parsing
validate_catalog standard_names/ --summary json
# Output: {"passed": true, "entries": 305, "errors": 0, "warnings": 134, "info": 0, "integrity_issues": 0}
```

**Exit Codes:**
- `0` — Validation passed
- `1` — Validation failed (errors found, or warnings in strict mode)
- `2` — Integrity issues detected

---

### Build Catalog Database

Builds SQLite catalog from YAML files.

```bash
standard-names build <catalog_path> [OPTIONS]
```

**Arguments:**
- `catalog_path` — Path to directory containing YAML standard name files

**Options:**
- `--db <path>` — Output database path (default: `<catalog_path>/.catalog/catalog.db`)
- `--verify` — Output verification summary with file size and entry count
- `--overwrite/--no-overwrite` — Overwrite existing DB (default: overwrite)

**Examples:**

```bash
# Basic build
standard-names build standard_names/

# Build with verification output (recommended for CI)
standard-names build standard_names/ --db catalog.db --verify
# Output: ✓ Built catalog.db: 45.2 KB, 305 entries
```

---

### Catalog Site Commands

Generates standalone documentation sites for catalog repositories. These commands are distinct from the main `imas-standard-names` project documentation.

#### Serve (Local Preview)

```bash
standard-names catalog-site serve <catalog_path> [OPTIONS]
```

Serves a temporary documentation site locally for previewing changes.

**Arguments:**
- `catalog_path` — Path to directory containing YAML standard name files

**Options:**
- `--site-name <name>` — Site name (default: "Standard Names Catalog")
- `--port <port>` — Port to serve on (default: 8000)
- `--host <host>` — Host to bind to (default: 127.0.0.1)

**Examples:**

```bash
# Preview catalog locally
standard-names catalog-site serve standard_names/

# Serve on different port
standard-names catalog-site serve standard_names/ --port 8080
```

#### Deploy (Versioned Publishing)

```bash
standard-names catalog-site deploy <catalog_path> --version <version> [OPTIONS]
```

Deploys versioned documentation using mkdocs + mike.

**Arguments:**
- `catalog_path` — Path to directory containing YAML standard name files

**Options:**
- `--version <version>` — Version string (required, e.g., "v1.0", "main", "pr-123")
- `--site-name <name>` — Site name (default: "Standard Names Catalog")
- `--site-url <url>` — Site URL
- `--push` — Push to gh-pages branch
- `--set-default` — Set this version as the default (latest)

**Examples:**

```bash
# Deploy and push version
standard-names catalog-site deploy standard_names/ --version v1.0.0 --push

# Deploy, push, and set as default
standard-names catalog-site deploy standard_names/ --version v1.0.0 --push --set-default

# Deploy for PR preview (no push, for artifacts)
standard-names catalog-site deploy standard_names/ --version pr-123
```

**Requirements:**
- `mike` must be installed: `uv add --group docs mike`
- Git repository with gh-pages branch configured

---

## CI Workflow Example

```yaml
name: Catalog CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Install dependencies
        run: uv pip install imas-standard-names
      
      - name: Validate catalog
        run: uv run validate_catalog standard_names/ --summary text
      
      - name: Build catalog database
        run: uv run standard-names build standard_names/ --db catalog.db --verify

  docs:
    runs-on: ubuntu-latest
    needs: validate
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          uv pip install imas-standard-names
          uv pip install mike mkdocs-material
      
      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
      
      - name: Deploy docs
        run: |
          uv run standard-names catalog-site deploy standard_names/ \
            --version ${{ github.ref_name }} \
            --push \
            --set-default
```

---

## Documentation Content

The `standard-names catalog-site` commands generate:

1. **index.md** — From catalog's `README.md` if present, otherwise auto-generated overview
2. **catalog.md** — Complete browsable catalog organized by primary tag and base name

The generated site includes:
- Full-text search
- Version selector (via mike, for deploy command)
- Responsive material theme
- Anchor links for each standard name

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `STANDARD_NAMES_CATALOG_ROOT` | Default catalog path for MCP server and tools |

---

## Version Compatibility

This interface is provided by `imas-standard-names` version 0.X.Y and later. The catalog repository should pin to a compatible version range to ensure CI stability.
