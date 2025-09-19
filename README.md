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

### Programmatic Usage (Repository, Build, Read-Only)

The YAML files are the authoritative source. A `StandardNameRepository` loads them
into an in-memory SQLite catalog (with FTS) for fast queries and authoring.

Basic queries:

```python
from pathlib import Path
from imas_standard_names.repository import StandardNameRepository

repo = StandardNameRepository(Path("resources/standard_names"))
print([m.name for m in repo.list()][:5])
print(repo.get("electron_temperature").unit)
print(repo.search("electron temperature", limit=3))
```

Mutations use a UnitOfWork boundary (add/update/remove/rename then commit to rewrite YAML):

```python
from imas_standard_names import schema

uow = repo.start_uow()
model = schema.create_standard_name({
   "name": "ion_density",
   "kind": "scalar",
   "unit": "m^-3",
   "description": "Ion number density.",
   "status": "draft",
})
uow.add(model)
uow.commit()  # writes ion_density.yml
```

### Building a Definitive SQLite Catalog

For distribution or read-only consumers, build a file-backed catalog that mirrors
YAML exactly:

```python
from pathlib import Path
from imas_standard_names.catalog.sqlite_build import build_catalog
from imas_standard_names.catalog.sqlite_read import CatalogRead

root = Path("resources/standard_names")
db_path = build_catalog(root, root / "artifacts" / "catalog.db")
ro = CatalogRead(db_path)
print(len(ro.list()))
```

CLI equivalent:

```bash
python -m imas_standard_names.cli.build_catalog resources/standard_names --db resources/standard_names/artifacts/catalog.db
```

### Architectural Components

| Component                | Purpose                                                                 |
| ------------------------ | ----------------------------------------------------------------------- |
| `YamlStore`              | Discover, load, and write per-file YAML entries (authoritative).        |
| `CatalogReadWrite`       | Ephemeral in-memory SQLite (authoring session).                         |
| `CatalogBuild`           | File-backed builder (creates persistent SQLite mirror).                 |
| `CatalogRead`            | Read-only view over file-backed SQLite snapshot.                        |
| `StandardNameRepository` | Facade combining `YamlStore` + `CatalogReadWrite` + search.             |
| `UnitOfWork`             | Batched mutation (add/update/remove/rename + validation + YAML commit). |

### Search

Search uses SQLite FTS5 ranking (bm25) with a substring fallback. Request metadata:

```python
repo.search("temperature gradient", with_meta=True, limit=5)
```

Returns objects including name, score, and highlighted description/documentation spans.

### Validation

Load-time validation (structural + semantic) aborts on invalid YAML. During a UoW
commit, the full staged view is revalidated before writing to disk.

CLI validation supports file-backed or fresh memory modes plus optional integrity verification:

```bash
python -m imas_standard_names.validation.cli validate_catalog resources/standard_names \
   --mode auto            # auto | file | memory
   --verify               # (file mode) compare integrity table to current YAML (size/mtime or full)
   --full                 # recompute hashes & check aggregate manifest
```

Exit codes:
| Code | Meaning |
|------|---------|
| 0 | Structural & semantic valid (and no integrity issues, or integrity issues only if code not raised) |
| 1 | Structural/semantic validation failed (no integrity issues) |
| 2 | Structural/semantic valid but integrity discrepancies detected |

Integrity issue codes: `mismatch-meta`, `hash-mismatch`, `missing-on-disk`, `missing-in-db`, `manifest-mismatch`.

### Migration (Legacy APIs Removed)

Legacy `StandardNameCatalog`, `load_catalog`, artifact rebuild flags, and
repository variants have been replaced by the unified repository and explicit
build step (`build_catalog`). If you previously relied on a JSON or legacy
artifact, switch to invoking `build_catalog` and consuming with `CatalogRead`.

### Debugging Foreign Key (FK) Errors & Logging

The in-memory authoring catalog enables SQLite foreign keys. Vector entries
reference their component scalar names. If components are missing when the
repository attempts to insert a vector you will now receive a diagnostic:

```text
sqlite3.IntegrityError: Foreign key constraint failed while inserting vector 'gradient_of_poloidal_flux'.
Missing component standard_name rows: radial_component_of_gradient_of_poloidal_flux, ...
Insert the component scalar definitions before the vector or reorder YAML files.
```

The `StandardNameRepository` performs a two-pass load (non-vectors first,
then vectors) to avoid ordering issues during initial load from YAML. If you
manually insert new models at runtime ensure scalar components / dependencies
exist before derived vectors or expression provenance rows.

Set an environment variable to enable verbose logging (helpful for tracing
load order and pinpointing the first failing name):

PowerShell (Windows):

```powershell
setx IMAS_SN_LOG_LEVEL DEBUG
# start a new shell OR for current session:
$env:IMAS_SN_LOG_LEVEL = "DEBUG"
python -m imas_standard_names.cli.build_catalog resources/standard_names
```

Unix shells:

```bash
IMAS_SN_LOG_LEVEL=DEBUG python -m imas_standard_names.cli.build_catalog resources/standard_names
```

Accepted levels: DEBUG, INFO, WARNING, ERROR (default WARNING). The catalog
logger name is `imas_standard_names.catalog`.

### Roadmap

See the evolving [Roadmap](docs/roadmap.md) for phased milestones (vectors, frames, operator validation, lifecycle governance, and future tensor support).

GitHub Actions automatically build and deploy the documentation whenever you push changes to the main branch. We version the documentation using [Mike](https://github.com/jimporter/mike), allowing versions to be accessible simultaneously.

### Local Documentation Development

You can use the blazing fast [uv](https://github.com/astral-sh/uv) workflow (used in CI) or a plain virtual environment.

Using uv (recommended):

```bash
uv venv
. .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync --all-extras --no-dev  # install runtime + extras used for docs (dev tools excluded)
uv run mkdocs serve
```

Using a plain virtual environment + pip:

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
# Install documentation dependencies (includes Mike) – via uv or pip
uv sync --extra docs  # or: pip install .[docs]

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
