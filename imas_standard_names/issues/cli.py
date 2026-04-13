"""Click CLI commands for issue submission and standard name maintenance."""

from __future__ import annotations

from collections.abc import Iterable
from io import StringIO
from pathlib import Path

import click
from strictyaml.ruamel import YAML

from imas_standard_names.generic_names import GenericNames
from imas_standard_names.issues.gh_repo import update_static_urls
from imas_standard_names.repository import StandardNameCatalog

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _legacy_private_load(root: Path):  # backward compat placeholder
    return StandardNameCatalog(root)


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
        click.echo(
            f":boom: The proposed Standard Name is not valid.\n"
            f"\n{type(error).__name__}: {error}\n"
        )
        return
    # Serialize similar to saved file
    data = {k: v for k, v in entry.model_dump().items() if v not in (None, [], "")}
    data["name"] = entry.name
    # Use ruamel yaml instance properly via context manager
    buf = StringIO()
    yaml.dump(data, buf)
    click.echo(buf.getvalue())


@click.command()
@click.argument("standard_name", nargs=-1)
def is_genericname(standard_name: Iterable[str]):
    """Check if a standard name is a generic physical base.

    Arguments:
      standard_name      Name to check against generic physical bases.
    """
    name = " ".join(standard_name)
    click.echo(str(name in GenericNames()))


# ---------------------------------------------------------------------------
# update_links (unchanged)
# ---------------------------------------------------------------------------
@click.command()
@click.argument("remote")
@click.option("--filename", default="README.md", help="File to update")
def update_links(remote: str, filename: str):
    """Update the README.md file with the remote's URL."""
    update_static_urls(filename, remote=remote)
