[![pre-commit][pre-commit-badge]][pre-commit-link]
[![Ruff][ruff-badge]][ruff-link]
[![Python versions][python-badge]][python-link]
[![CI/CD status][build-deploy-badge]][build-deploy-link]
[![Coverage status][codecov-badge]][codecov-link]
[![Documentation][docs-badge]][docs-link]

# IMAS Standard Names

This repository documents a collection of Standard Names used in the Fusion Conventions. To submit proposals for new Standard Names or changes to existing Standard Names, please use one of the supplied issue templates. The issue templates use the following "zero-code" submission process:

> Data Harvest Note: For bootstrapping new entries (especially Phase 1 equilibrium
> reconstruction attributes), use the IMAS MCP server configured in
> `.vscode/mcp.json` (tool id `imas`) to extract existing coil, probe, loop,
> and equilibrium geometry information from the IMAS Data Dictionary. This
> ensures proposed names align with available diagnostics and metadata.

1. **Create an Issue**: Use the provided issue templates to create a new issue.
   - For new Standard Names, use the "New Standard Name" template.
   - For changes to existing Standard Names, use the "Change Existing Standard Name" template.
2. **Fill in the Template**: Provide all required information in the issue template.
   - For new Standard Names, include details such as the proposed name, description, and any relevant references.
   - For changes to existing Standard Names, specify the name of the existing Standard Name and the proposed changes.
3. **Submit the Issue**: Once you have filled in the template, submit the issue.
4. **Review Process**: We outline the review process as follows:
   - Following submission, a GitHub action will automatically check the issue for compliance with the Fusion Conventions and flag any errors or missing information.
   - After successful automatic processing, a member of the IMAS Standard Names team will review your issue.
   - The team may request information or clarification if needed.
5. **Approval**: Once your issue is sufficiently developed, collaborators with privileges will tag it with the 'approve' label.
6. **Submission**: After approval, a GitHub action will automatically commit the Standard Name proposal to the `submit` branch. The action will raise a _draft_ Pull Request pointing from the `submit` branch to the `develop` branch, if one is not already present.
7. **Final Review**: Once we collect a batch of Standard Name proposals, the Pull Request will undergo final review and approval.
8. **Release**: We will tag releases that merge approved changes from the `develop` branch back to the `main` branch accordingly.
9. **Feedback**: We encourage feedback on the Standard Names to ensure they meet community needs. Please submit your feedback through the provided issue templates to support discussion and improvements.

## Branching Strategy

This project uses a Git branching strategy to manage development and releases. The principal branches are:

- The `submit` branch collects and reviews proposed changes to the Standard Names.
- We use the `develop` branch for ongoing development and testing of new Standard Names.
- We create tagged releases of the Standard Names project and associated documentation from the `main` branch.

## Documentation

The project documentation is available at our [GitHub Pages site](https://Simon-McIntosh.github.io/IMAS-Standard-Names/).

### Data Layout (Per-File Schema)

Each Standard Name lives in its own YAML file under `resources/standard_names/` (or a user-defined directory).

Minimal scalar example:

```yaml
name: electron_temperature
kind: scalar
unit: keV
description: Electron temperature.
status: draft
```

### CLI Usage

All issue automation and local maintenance use the new CLI entry points (backed by the per-file schema):

| Command                                                                                        | Purpose                                                                  |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `update_standardnames <standardnames_dir> <generic_names.csv> <submission.json> [--overwrite]` | Check and add (or overwrite) a proposal from a GitHub issue JSON export. |
| `has_standardname <standardnames_dir> <name>`                                                  | Returns `True` / `False` for existence.                                  |
| `get_standardname <standardnames_dir> <name>`                                                  | Prints the YAML for a single entry.                                      |
| `diff_standardnames <old_dir> <new_dir> <report.json> [--export-dir DIR]`                      | JSON diff (added/removed/changed[/unchanged]) and optional export.       |
| `is_genericname <generic_names.csv> <token>`                                                   | Tests if a token collides with a reserved generic name.                  |
| `update_links <remote>`                                                                        | Rewrites badge/URL references in README for a fork remote.               |

The issue form submission JSON is normalized in-place (e.g. `units` → `unit`, empty strings removed, `documentation` merged into `description`). The CLI discards unsupported legacy keys such as `options`.

### Deprecations Removed

### Migration Notes

If you depended on loading a single aggregated YAML, build an index by scanning the directory:

```python
from pathlib import Path
from imas_standard_names.catalog.catalog import StandardNameCatalog

catalog = StandardNameCatalog(Path("resources/standard_names")).load()
print(catalog.entries["electron_temperature"].unit)
```

Programmatic creation (Repository + UnitOfWork):

```python
from pathlib import Path
from imas_standard_names import schema
from imas_standard_names.repositories import YamlStandardNameRepository
from imas_standard_names.unit_of_work import UnitOfWork

root = Path("resources/standard_names/plasma")
root.mkdir(parents=True, exist_ok=True)
repo = YamlStandardNameRepository(root)
uow = UnitOfWork(repo)
entry = schema.create_standard_name({
   "name": "ion_density",
   "kind": "scalar",
   "unit": "m^-3",
   "description": "Ion number density.",
   "status": "draft",
})
uow.add(entry)
uow.commit()
```

### Roadmap

See the evolving [Roadmap](docs/roadmap.md) for phased milestones (vectors, frames, operator validation, lifecycle governance, and future tensor support).

GitHub Actions automatically build and deploy the documentation whenever you push changes to the main branch. We version the documentation using [Mike](https://github.com/jimporter/mike), allowing versions to be accessible simultaneously.

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

# Build and serve versions using Mike
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

[python-badge]: https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue
[python-link]: https://www.python.org/downloads/
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json
[ruff-link]: https://docs.astral.sh/ruff/
[pre-commit-badge]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
[pre-commit-link]: https://github.com/pre-commit/pre-commit
[build-deploy-badge]: https://img.shields.io/github/actions/workflow/status/Simon-McIntosh/IMAS-Standard-Names/test-project.yml?branch=main&color=brightgreen&label=CI%2FCD
[build-deploy-link]: https://codecov.io/gh/Simon-McIntosh/IMAS-Standard-Names/tests/main
[codecov-badge]: https://codecov.io/gh/Simon-McIntosh/IMAS-Standard-Names/graph/badge.svg
[codecov-link]: https://codecov.io/gh/Simon-McIntosh/IMAS-Standard-Names
[docs-badge]: https://img.shields.io/badge/docs-online-brightgreen
[docs-link]: https://Simon-McIntosh.github.io/IMAS-Standard-Names/
