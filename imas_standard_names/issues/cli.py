"""Click CLI commands for issue submission and standard name maintenance."""

from __future__ import annotations

import json
from collections.abc import Iterable
from io import StringIO
from pathlib import Path

import click
from strictyaml.ruamel import YAML

from imas_standard_names import schema
from imas_standard_names.generic_names import GenericNames
from imas_standard_names.issues.gh_repo import update_static_urls
from imas_standard_names.issues.image_assets import ImageProcessor
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.unit_of_work import UnitOfWork

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _legacy_private_load(root: Path):  # backward compat placeholder
    return StandardNameCatalog(root)


def format_error(error: Exception, submission_file: str | None = None) -> str:
    """Return formatted error message for invalid submissions."""
    error_message = (
        ":boom: The proposed Standard Name is not valid.\n"
        f"\n{type(error).__name__}: {error}\n"
    )
    if submission_file:
        try:
            with open(submission_file) as f:
                submission = json.load(f)
            yaml_str = StringIO()
            yaml.dump(submission, yaml_str)
        except Exception:
            pass
    error_message += (
        "\n"
        "> [!NOTE]\n"
        "> Edit the issue form and the automation will re-run validation.\n"
    )
    return error_message


# ---------------------------------------------------------------------------
# update_standardnames (directory-based)
# ---------------------------------------------------------------------------
@click.command()
@click.argument("standardnames_dir")
@click.argument("genericnames_file")
@click.argument("submission_file")
@click.option("--issue-link", default="")
@click.option(
    "--overwrite", default=False, is_flag=True, help="Allow replacing existing entry"
)
def update_standardnames(
    standardnames_dir: str,
    genericnames_file: str,
    submission_file: str,
    issue_link: str,
    overwrite: bool,
):
    """Validate and add a standard name (per-file schema) to a directory.

    Arguments:
      standardnames_dir  Directory containing per-file standard name YAML entries.
      genericnames_file  CSV of reserved generic names.
      submission_file    JSON issue form export.
    """
    root = Path(standardnames_dir)
    root.mkdir(parents=True, exist_ok=True)
    repo = StandardNameCatalog(root)
    genericnames = GenericNames(genericnames_file)

    try:
        # Raw JSON (not yet coerced) so we can normalise fields first
        raw_json = json.loads(Path(submission_file).read_text())
        # Normalise legacy key 'units' -> 'unit'
        if "unit" not in raw_json and "units" in raw_json:
            raw_json["unit"] = raw_json["units"]
        name = raw_json.get("name", "").strip()
        if not name:
            raise ValueError("Submission must include 'name'")
        # Generic name guard before schema validation
        genericnames.check(name)
        # Drop unsupported keys that may appear in issue form (e.g. options)
        for extraneous in ["options"]:
            raw_json.pop(extraneous, None)
        # Tags may arrive as a comma separated string or empty string
        raw_tags = raw_json.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

        # Minimal required fields mapping
        description = raw_json.get("description") or raw_json.get("documentation") or ""
        data = {
            "name": name,
            "kind": raw_json.get("kind", "scalar") or "scalar",
            "status": raw_json.get("status", "draft") or "draft",
            "unit": raw_json.get("unit", "") or "",
            "description": description,
            "tags": raw_tags or [],
            "links": [],
        }
        # Remove keys with empty string that are optional (pydantic will ignore missing)
        cleaned = {k: v for k, v in data.items() if v not in (None, "") or k == "name"}
        entry = schema.create_standard_name(cleaned)

        # Overwrite guard (only error if not overwriting)
        if repo.get(entry.name) and not overwrite:
            raise KeyError(
                f"The proposed standard name **{entry.name}** is already present. Use --overwrite to replace."
            )

        # Image processing (optional documentation rewrite)
        if description:
            img_proc = ImageProcessor(
                entry.name,
                description,
                image_dir=Path("docs/img") / entry.name,
                parents=1,
            )
            try:
                img_proc.download_images(remove_existing=True)
                # Append note about images to description (non-destructive)
                new_desc = img_proc.documentation_with_relative_paths()
                if new_desc and new_desc != description:
                    data["description"] = new_desc
                    entry = schema.create_standard_name(
                        {k: v for k, v in data.items() if v not in (None, "")}
                    )
            except Exception:  # Non-fatal: continue without images
                pass

        # Persist via unified repository + unit of work
        uow = UnitOfWork(repo)
        if repo.get(entry.name) and overwrite:
            uow.update(entry.name, entry)
        else:
            uow.add(entry)
        uow.commit()
        click.echo(
            ":sparkles: This proposal is ready for submission to the Standard Names repository."
        )
    except (ValueError, KeyError, NameError, Exception) as error:  # broad
        click.echo(format_error(error, submission_file))


# ---------------------------------------------------------------------------
# Queries (has / get)
# ---------------------------------------------------------------------------
@click.command()
@click.argument("standardnames_dir")
@click.argument("standard_name", nargs=-1)
def has_standardname(standardnames_dir: str, standard_name: Iterable[str]):
    """Return True/False if STANDARD_NAME exists in directory catalog."""
    name = " ".join(standard_name)
    if not name:
        click.echo("False")
        return
    root = Path(standardnames_dir)
    if not root.exists():
        click.echo("False")
        return
    try:
        repo = StandardNameCatalog(root)
    except Exception:
        click.echo("False")
        return
    click.echo(str(repo.get(name) is not None))


@click.command()
@click.argument("standardnames_dir")
@click.argument("standard_name", nargs=-1)
def get_standardname(standardnames_dir: str, standard_name: Iterable[str]):
    """Print the YAML of a single standard name entry."""
    name = " ".join(standard_name)
    root = Path(standardnames_dir)
    try:
        repo = StandardNameCatalog(root)
        entry = repo.get(name)
        if not entry:
            raise KeyError(name)
    except Exception as error:
        click.echo(format_error(error))
        return
    # Serialize similar to saved file
    data = {k: v for k, v in entry.model_dump().items() if v not in (None, [], "")}
    data["name"] = entry.name
    # Use ruamel yaml instance properly via context manager
    from io import StringIO as _S

    buf = _S()
    yaml.dump(data, buf)
    click.echo(buf.getvalue())


@click.command()
@click.argument("genericnames_file")
@click.argument("standard_name", nargs=-1)
def is_genericname(genericnames_file: str, standard_name: Iterable[str]):
    """Check if a standard name is already present in the generic names file."""
    name = " ".join(standard_name)
    click.echo(str(name in GenericNames(genericnames_file)))


# ---------------------------------------------------------------------------
# update_links (unchanged)
# ---------------------------------------------------------------------------
@click.command()
@click.argument("remote")
@click.option("--filename", default="README.md", help="File to update")
def update_links(remote: str, filename: str):
    """Update the README.md file with the remote's URL."""
    update_static_urls(filename, remote=remote)
