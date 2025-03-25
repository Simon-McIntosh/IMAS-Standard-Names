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

GitHub Actions automatically build and deploy the documentation whenever you push changes to the main branch. To build the documentation locally, run:

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
