"""Build command for Standard Names catalog.

Provides the `build` Click command used to construct the SQLite catalog
from YAML standard name definitions.
"""

from __future__ import annotations

from pathlib import Path
import click

from ..paths import CatalogPaths, CATALOG_DIRNAME
from ..repository import StandardNameRepository
from ..catalog.sqlite_build import build_catalog as build_catalog_file


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
def build_cmd(yaml_path: str | Path | None, db_path: Path | None, overwrite: bool):
    """Build a definitive SQLite catalog database from YAML sources.

    YAML_PATH (optional): path or pattern to the standard names directory.
        * None -> packaged standard names root
        * existing path -> used directly
        * pattern -> first matching subdirectory under packaged standard_names
    DB_PATH (optional via --db): resolved (patterns allowed); if omitted a
    catalog is placed under <yaml_path>/{CATALOG_DIRNAME}/catalog.db
    """
    paths = CatalogPaths("standard_names" if yaml_path is None else yaml_path, db_path)
    repo = StandardNameRepository(paths.yaml_path)
    count = len(repo)
    paths.ensure_catalog_dir()
    final_db = build_catalog_file(
        paths.yaml_path, paths.catalog_path, overwrite=overwrite
    )
    click.echo(f"Built catalog ({count} entries) -> {final_db}")


__all__ = ["build_cmd"]
