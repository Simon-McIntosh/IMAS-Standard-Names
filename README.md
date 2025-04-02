[![image](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/Simon-McIntosh/IMAS-Standard-Names.git)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/charliermarsh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![pytest](https://github.com/Simon-McIntosh/IMAS-Standard-Names/actions/workflows/python-package.yml/badge.svg)](https://Simon-McIntosh.github.io/IMAS-Standard-Names/pytest)
[![coverage](https://github.com/Simon-McIntosh/IMAS-Standard-Names/blob/gh-pages/badges/coverage.svg)](https://Simon-McIntosh.github.io/IMAS-Standard-Names/coverage)
[![docs](https://img.shields.io/badge/docs-online-brightgreen)](https://Simon-McIntosh.github.io/IMAS-Standard-Names/)

# IMAS Standard Names

This repository hosts a collection of Standard Names used in the Fusion
Conventions and logic for creating a static website for documentation.

## Documentation

The project documentation is available at our [GitHub Pages site](https://Simon-McIntosh.github.io/IMAS-Standard-Names/).

GitHub Actions automatically build and deploy the documentation whenever you push changes to the main branch. The documentation is versioned using [Mike](https://github.com/jimporter/mike), allowing multiple versions to be accessible simultaneously.

### Local Documentation Development

To build the documentation locally, run:

```bash
# create virtual environment
python -m venv
. venv/bin/activate

# Install documentation dependencies
pip install .[docs]

# Build the documentation
mkdocs build

# To preview the documentation locally
mkdocs serve
```

### Working with Versioned Documentation

This project uses Mike to manage versioned documentation. To work with versioned documentation locally:

```bash
# Install documentation dependencies (includes Mike)
pip install .[docs]

# Initialize a git repo if not already done
git init

# Build and serve multiple versions using Mike
mike deploy 0.1 latest --update-aliases
mike deploy 0.2 --update-aliases
mike serve  # Serves the versioned documentation locally

# List all versions of the documentation
mike list

# Set the default version
mike set-default latest
```

When the CI/CD pipeline runs, it automatically deploys documentation for:

- `main` branch as "latest"
- `develop` branch as "develop"
- `submit` branch as "submit"

Each branch will be available as a separate version in the version selector dropdown on the documentation site.
