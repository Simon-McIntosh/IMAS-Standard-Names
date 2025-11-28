# Catalog Site CLI

The `standard-names catalog-site` command group generates standalone documentation sites for external catalog repositories containing YAML standard name definitions.

## Purpose

This CLI is designed for **external catalog repositories** (e.g., `imas-standard-names-catalog`), not for building documentation for the `imas-standard-names` project itself. It allows catalog maintainers to:

- Preview their catalog changes locally before committing
- Deploy versioned documentation sites via CI/CD pipelines

For `imas-standard-names` project documentation, use `mkdocs serve` directly from the project root.

## Commands

### `serve` — Local Preview

Generates a temporary mkdocs site and serves it locally. No git repository or mike installation required.

```bash
standard-names catalog-site serve <catalog_path> [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--site-name` | "Standard Names Catalog" | Site title |
| `--port` | 8000 | Port to serve on |
| `--host` | 127.0.0.1 | Host to bind to |

**Example:**

```bash
# Preview catalog at http://localhost:8000
standard-names catalog-site serve ./standard_names

# Custom port
standard-names catalog-site serve ./standard_names --port 8080
```

### `deploy` — Versioned Publishing

Deploys versioned documentation using mkdocs + mike. Requires a git repository.

```bash
standard-names catalog-site deploy <catalog_path> --version <version> [OPTIONS]
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--version` | Yes | Version string (e.g., "v1.0", "main") |
| `--site-name` | No | Site title |
| `--site-url` | No | Published site URL |
| `--push` | No | Push to gh-pages branch |
| `--set-default` | No | Set as default version (latest) |

**Example:**

```bash
# Deploy version and push to gh-pages
standard-names catalog-site deploy ./standard_names --version v1.0.0 --push

# Deploy and set as default
standard-names catalog-site deploy ./standard_names --version v1.0.0 --push --set-default
```

## Migration from `docs` Command

The `catalog-site` command replaces the previous `docs` command group:

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `standard-names docs build ... --version X` | `standard-names catalog-site deploy ... --version X` | Renamed for clarity |
| `standard-names docs serve ...` | `standard-names catalog-site serve ...` | Unchanged functionality |
| `standard-names docs alias ...` | *(removed)* | Use mike directly if needed |

### Why the rename?

- **Clarity**: `docs` was confusing—it sounded like it built documentation for this project
- **Intent**: `catalog-site` clearly indicates it generates a standalone site for catalog content
- **Separation**: Distinguishes catalog documentation from project documentation

## Generated Site Content

Both commands generate a mkdocs-material site with:

| Page | Content |
|------|---------|
| `index.md` | Catalog README.md if present, otherwise auto-generated overview |
| `catalog.md` | Full browsable catalog organized by primary tag and base name |

Features:
- Full-text search
- Responsive material theme
- Anchor links for each standard name
- Version selector (deploy command only)

## Requirements

| Command | Requirements |
|---------|--------------|
| `serve` | mkdocs, mkdocs-material |
| `deploy` | mkdocs, mkdocs-material, mike, git repository |

Install with:

```bash
uv add --group docs mike mkdocs-material
```

## CI Workflow Example

```yaml
name: Deploy Catalog Docs

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
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
          uv run standard-names catalog-site deploy ./standard_names \
            --version ${{ github.ref_name }} \
            --push \
            --set-default
```
