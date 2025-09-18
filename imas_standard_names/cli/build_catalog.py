"""Build a definitive SQLite catalog artifact mirroring the YAML source.

This command loads all per-file YAML entries, validates them via the
repository load path, and writes a file-backed SQLite catalog suitable
for read-only consumption (e.g. with CatalogRead)."""

from __future__ import annotations
import click
from pathlib import Path
from ..repository import StandardNameRepository
from ..catalog.sqlite_build import build_catalog as build_catalog_file


@click.command(name="build_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--out",
    "out_path",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Output SQLite file (default: <root>/artifacts/catalog.db)",
)
@click.option("--overwrite/--no-overwrite", default=True, help="Overwrite existing DB")
@click.option("--quiet", is_flag=True, help="Suppress non-error output")
def build_catalog_cli(root: Path, out_path: Path | None, overwrite: bool, quiet: bool):
    repo = StandardNameRepository(root)
    # Use __len__ for efficient row counting (added in repository)
    count = len(repo)
    if out_path is None:
        out_path = root / "artifacts" / "catalog.db"
    db_path = build_catalog_file(root, out_path, overwrite=overwrite)
    if not quiet:
        # Emit a deprecation notice (tests assert presence of 'deprecated')
        click.echo(
            "[DEPRECATED] This command will be replaced by 'standard-names catalog build' in a future release."
        )
        click.echo(f"Built catalog ({count} entries) -> {db_path}")
