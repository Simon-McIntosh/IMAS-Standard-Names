# IMAS Standard Names Catalog Development Guide

This guide explains how to set up and develop the separate `imas-standard-names-catalog` repository containing YAML source files for standard names.

## Overview

The IMAS Standard Names project uses a **two-repository architecture**:

1. **imas-standard-names** (this repo): Tools, MCP server, grammar, validation
2. **imas-standard-names-catalog** (separate repo): YAML catalog files only

This separation allows:
- **Independent versioning**: Catalog data evolves separately from tools
- **Clean architecture**: Pure data repo without Python code
- **Flexible deployment**: Users can pin catalog version while floating tool version
- **Read-only distribution**: Pre-built `.db` files prevent accidental edits

## Creating the Catalog Repository

### Repository Structure

```
imas-standard-names-catalog/
├── standard_names/              # YAML source files (organized by domain)
│   ├── physics/
│   │   ├── temperature/
│   │   │   ├── electron_temperature.yml
│   │   │   └── ion_temperature.yml
│   │   ├── density/
│   │   └── pressure/
│   ├── geometry/
│   │   ├── position/
│   │   └── shape/
│   └── diagnostics/
├── docs/                        # MkDocs documentation for catalog
│   ├── mkdocs.yml
│   └── index.md
├── .github/
│   └── workflows/
│       └── release.yml          # CI: Build .db, deploy docs
├── .gitignore
├── README.md
├── LICENSE
└── pyproject.toml               # Minimal metadata (no Python code)
```

### Initial Setup

```bash
# Create the repository
mkdir imas-standard-names-catalog
cd imas-standard-names-catalog

# Initialize git
git init
git branch -m main

# Create directory structure
mkdir -p standard_names/{physics,geometry,diagnostics}
mkdir -p docs
mkdir -p .github/workflows
```

### pyproject.toml (Minimal)

```toml
[project]
name = "imas-standard-names-catalog"
version = "1.0.0"
description = "IMAS Standard Names YAML catalog source files"
readme = "README.md"
license = {text = "CC BY-ND 4.0"}
authors = [
    {name = "ITER Organization", email = "iter@iter.org"},
]
requires-python = ">=3.12"

[project.urls]
Homepage = "https://github.com/iterorg/imas-standard-names-catalog"
Documentation = "https://iterorg.github.io/imas-standard-names-catalog"
Repository = "https://github.com/iterorg/imas-standard-names-catalog"

[build-system]
requires = ["hatchling>=1.25.0"]
build-backend = "hatchling.build"
```

### .gitignore

```gitignore
# Build artifacts
*.db
*.pyc
__pycache__/
.pytest_cache/
*.egg-info/
dist/
build/
site/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

### README.md Template

```markdown
# IMAS Standard Names Catalog

YAML source files for the IMAS Standard Names catalog.

## Installation

### For Users (Read-Only Access)

Download pre-built catalog from releases:

\`\`\`bash
# Download catalog.db from latest release
wget https://github.com/iterorg/imas-standard-names-catalog/releases/latest/download/catalog.db

# Use with imas-standard-names
export STANDARD_NAMES_CATALOG_DB=./catalog.db
\`\`\`

Or install the catalog package (when available):

\`\`\`bash
pip install imas-standard-names[catalog]
\`\`\`

### For Developers (Read-Write Access)

Clone this repository and point imas-standard-names to it:

\`\`\`bash
# Clone catalog
git clone https://github.com/iterorg/imas-standard-names-catalog.git
cd imas-standard-names-catalog

# Install imas-standard-names tools
pip install imas-standard-names[quality]

# Point to local catalog
export STANDARD_NAMES_CATALOG_ROOT=$(pwd)/standard_names

# Verify
python -c "from imas_standard_names import StandardNameCatalog; cat = StandardNameCatalog(); print(f'Entries: {len(cat)}')"
\`\`\`

## Repository Structure

- \`standard_names/\` - YAML source files organized by domain
- \`docs/\` - MkDocs documentation (auto-generated from YAML)
- \`.github/workflows/\` - CI/CD for building .db and deploying docs

## Adding New Standard Names

### 1. Create YAML File

\`\`\`bash
# Example: Add new physics quantity
touch standard_names/physics/temperature/bulk_ion_temperature.yml
\`\`\`

### 2. Edit YAML

\`\`\`yaml
name: bulk_ion_temperature
kind: scalar
unit: keV
status: draft
description: Average temperature of bulk ion population.
tags:
  - physics
  - temperature
  - ions
\`\`\`

### 3. Validate Locally

\`\`\`bash
# Requires imas-standard-names tools
validate_catalog standard_names/
\`\`\`

### 4. Commit and Push

\`\`\`bash
git add standard_names/physics/temperature/bulk_ion_temperature.yml
git commit -m "Add bulk_ion_temperature standard name"
git push origin main
\`\`\`

### 5. Create Pull Request

Open PR for review. CI will validate your changes.

## Releasing

### Version Tagging

\`\`\`bash
# Create release tag
git tag -a v1.1.0 -m "Release v1.1.0: Added 10 new temperature quantities"
git push origin v1.1.0
\`\`\`

### Automatic Release Process

When you push a tag, GitHub Actions automatically:
1. Builds \`catalog.db\` from YAML files
2. Generates documentation site
3. Creates GitHub Release with \`catalog.db\` artifact
4. Deploys docs to GitHub Pages

## Documentation

Documentation is automatically built from YAML metadata and deployed to:
https://iterorg.github.io/imas-standard-names-catalog

## License

CC BY-ND 4.0 - See LICENSE file
\`\`\`

## CI/CD Setup

### GitHub Actions Workflow

Create `.github/workflows/release.yml`:

```yaml
name: Build and Release Catalog

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout catalog repository
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install build tools
        run: |
          pip install imas-standard-names
          pip install mkdocs-material
      
      - name: Validate catalog
        run: |
          validate_catalog standard_names/
      
      - name: Build catalog.db
        run: |
          python -c "
          from imas_standard_names.database.build import build_catalog
          from pathlib import Path
          build_catalog(Path('standard_names'), Path('catalog.db'))
          print(f'Built catalog.db: {Path(\"catalog.db\").stat().st_size / 1024:.1f} KB')
          "
      
      - name: Build documentation
        run: |
          mkdocs build
      
      - name: Create Release
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v1
        with:
          files: catalog.db
          body: |
            ## IMAS Standard Names Catalog ${{ github.ref_name }}
            
            ### Installation
            
            Download \`catalog.db\` and use with:
            \`\`\`bash
            export STANDARD_NAMES_CATALOG_DB=/path/to/catalog.db
            \`\`\`
            
            ### Using with imas-standard-names
            
            \`\`\`python
            from imas_standard_names import StandardNameCatalog
            catalog = StandardNameCatalog()  # Auto-discovers catalog
            print(catalog.search("temperature"))
            \`\`\`
            
            For read-write access, clone the repository:
            \`\`\`bash
            git clone https://github.com/iterorg/imas-standard-names-catalog.git
            export STANDARD_NAMES_CATALOG_ROOT=./imas-standard-names-catalog/standard_names
            \`\`\`
      
      - name: Deploy documentation to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
```

### Validation Workflow

Create `.github/workflows/validate.yml`:

```yaml
name: Validate Catalog

on:
  pull_request:
    paths:
      - 'standard_names/**/*.yml'
  push:
    branches:
      - main

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install validation tools
        run: pip install imas-standard-names[quality]
      
      - name: Validate YAML structure
        run: validate_catalog standard_names/
      
      - name: Check for duplicates
        run: |
          python -c "
          from pathlib import Path
          import yaml
          
          names = set()
          duplicates = []
          
          for yml_file in Path('standard_names').rglob('*.yml'):
              with open(yml_file) as f:
                  data = yaml.safe_load(f)
                  name = data.get('name')
                  if name in names:
                      duplicates.append(name)
                  names.add(name)
          
          if duplicates:
              print(f'ERROR: Duplicate names found: {duplicates}')
              exit(1)
          print(f'✓ No duplicates found ({len(names)} unique names)')
          "
```

## MkDocs Configuration

Create `docs/mkdocs.yml`:

```yaml
site_name: IMAS Standard Names Catalog
site_url: https://iterorg.github.io/imas-standard-names-catalog
repo_url: https://github.com/iterorg/imas-standard-names-catalog
repo_name: iterorg/imas-standard-names-catalog

theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.instant
    - navigation.tracking
    - navigation.sections
    - navigation.expand
    - search.suggest
    - search.highlight
    - content.code.copy

nav:
  - Home: index.md
  - Physics Quantities: physics/index.md
  - Geometry: geometry/index.md
  - Diagnostics: diagnostics/index.md

markdown_extensions:
  - admonition
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.tabbed
  - tables

plugins:
  - search
  - macros:
      module_name: generate_catalog_docs
```

Create `docs/generate_catalog_docs.py`:

```python
"""Generate catalog documentation from YAML files."""

from pathlib import Path
import yaml

def define_env(env):
    """Hook for mkdocs-macros plugin."""
    
    @env.macro
    def list_standard_names(domain: str = None):
        """Generate markdown table of standard names."""
        catalog_path = Path('../standard_names')
        
        rows = []
        for yml_file in sorted(catalog_path.rglob('*.yml')):
            with open(yml_file) as f:
                data = yaml.safe_load(f)
            
            if domain and not str(yml_file).startswith(f'standard_names/{domain}'):
                continue
            
            name = data.get('name', '')
            unit = data.get('unit', '—')
            desc = data.get('description', '')
            status = data.get('status', 'draft')
            
            rows.append(f"| `{name}` | {unit} | {desc[:80]}{'...' if len(desc) > 80 else ''} | {status} |")
        
        header = "| Name | Unit | Description | Status |\n|------|------|-------------|--------|\n"
        return header + '\n'.join(rows)
```

## Development Workflow

### Local Development Setup

```bash
# 1. Clone both repositories
git clone https://github.com/iterorg/imas-standard-names.git
git clone https://github.com/iterorg/imas-standard-names-catalog.git

# 2. Install tools in development mode
cd imas-standard-names
uv sync
cd ..

# 3. Point to local catalog
export STANDARD_NAMES_CATALOG_ROOT=$(pwd)/imas-standard-names-catalog/standard_names

# 4. Verify setup
python -c "from imas_standard_names import StandardNameCatalog; cat = StandardNameCatalog(); print(f'Mode: {\"read-write\" if not cat.read_only else \"read-only\"}')"
```

### Adding New Standard Names

```bash
cd imas-standard-names-catalog

# Create feature branch
git checkout -b feature/add-radiation-quantities

# Add YAML files
cat > standard_names/physics/radiation/bremsstrahlung_radiation_power.yml <<EOF
name: bremsstrahlung_radiation_power
kind: scalar
unit: W
status: draft
description: Total bremsstrahlung radiation power emitted by plasma.
tags:
  - physics
  - radiation
  - power
EOF

# Validate
validate_catalog standard_names/

# Build and test locally
python -c "
from imas_standard_names.database.build import build_catalog
from pathlib import Path
build_catalog(Path('standard_names'), Path('test_catalog.db'))
"

# Commit and push
git add standard_names/physics/radiation/
git commit -m "Add bremsstrahlung radiation power"
git push origin feature/add-radiation-quantities

# Open PR
gh pr create --title "Add bremsstrahlung radiation quantities" --body "Adds standard names for radiation power measurements"
```

### Testing Changes

```bash
# Test with imas-standard-names tools
python <<EOF
from imas_standard_names import StandardNameCatalog

cat = StandardNameCatalog()
print(f"Total entries: {len(cat)}")
print(f"Search results: {cat.search('radiation')}")

# Test write operations
from imas_standard_names.catalog.edit import EditCatalog
edit = EditCatalog(cat)
edit.add({
    'name': 'test_quantity',
    'kind': 'scalar',
    'unit': 'kg',
    'description': 'Test quantity',
    'status': 'draft',
    'tags': ['test']
})
print("Write test: OK")
EOF
```

### Release Process

```bash
# 1. Update version and create tag
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# 2. CI automatically:
#    - Builds catalog.db
#    - Creates GitHub Release
#    - Deploys documentation

# 3. Verify release
wget https://github.com/iterorg/imas-standard-names-catalog/releases/download/v1.2.0/catalog.db
python -c "from imas_standard_names import StandardNameCatalog; cat = StandardNameCatalog('catalog.db'); print(len(cat))"
```

## Best Practices

### YAML Organization

- **Group by domain**: `physics/`, `geometry/`, `diagnostics/`
- **Use subdirectories**: `physics/temperature/`, `physics/density/`
- **One file per name**: `electron_temperature.yml`
- **Consistent naming**: Match filename to `name` field

### Version Management

- **Semantic versioning**: `v1.2.3` (major.minor.patch)
- **Major**: Breaking changes to existing names
- **Minor**: New standard names added
- **Patch**: Documentation/metadata fixes

### Collaboration

- **Branch per feature**: `feature/add-X`, `fix/update-Y`
- **Descriptive commits**: "Add electron temperature variants"
- **PR reviews**: Require approval before merge
- **CI validation**: All PRs must pass validation

## Troubleshooting

### Build Failures

**Error**: `validate_catalog` fails

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('problematic_file.yml'))"

# Check schema
validate_catalog standard_names/ --verbose
```

**Error**: Duplicate names

```bash
# Find duplicates
find standard_names -name "*.yml" -exec grep "^name:" {} \; | sort | uniq -d
```

### GitHub Actions Issues

**Actions not triggering**:
- Verify `.github/workflows/` files are committed
- Check workflow syntax with `gh workflow view`
- Ensure repository settings allow Actions

## Resources

- [imas-standard-names Documentation](https://iterorganization.github.io/imas-standard-names)
- [YAML Specification](https://yaml.org/spec/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
