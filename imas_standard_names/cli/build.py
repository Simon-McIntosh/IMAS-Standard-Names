"""Build command for Standard Names catalog.

Provides the `build` Click command used to construct the SQLite catalog
from YAML standard name definitions.
"""

from __future__ import annotations

import os
from pathlib import Path

import click

from ..database.build import build_catalog as build_catalog_file
from ..paths import CATALOG_DIRNAME, CatalogPaths
from ..repository import StandardNameCatalog


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable units."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@click.command("build")
@click.argument(
    "yaml_path",
    required=False,
    type=str,
)
@click.option(
    "--db",
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help=f"Output SQLite catalog file (default: <yaml_path>/{CATALOG_DIRNAME}/catalog.db)",
)
@click.option("--overwrite/--no-overwrite", default=True, help="Overwrite existing DB")
@click.option(
    "--verify",
    is_flag=True,
    help="Output verification summary with file size and entry count",
)
def build_cmd(
    yaml_path: str | Path | None, db_path: Path | None, overwrite: bool, verify: bool
):
    """Build a definitive SQLite catalog database from YAML sources.

    YAML_PATH (optional): path or pattern to the standard names directory.
        * None -> packaged standard names root
        * existing path -> used directly
        * pattern -> first matching subdirectory under packaged standard_names
    DB_PATH (optional via --db): resolved (patterns allowed); if omitted a
    catalog is placed under <yaml_path>/{CATALOG_DIRNAME}/catalog.db
    """
    paths = CatalogPaths("standard_names" if yaml_path is None else yaml_path, db_path)
    repo = StandardNameCatalog(paths.yaml_path)
    count = len(repo)
    paths.ensure_catalog_dir()
    final_db = build_catalog_file(
        paths.yaml_path, paths.catalog_path, overwrite=overwrite
    )

    if verify:
        file_size = os.path.getsize(final_db)
        click.echo(f"✓ Built {final_db.name}: {_format_file_size(file_size)}, {count} entries")
    else:
        click.echo(f"Built catalog ({count} entries) -> {final_db}")


__all__ = ["build_cmd"]
