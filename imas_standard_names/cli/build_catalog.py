"""CLI command: build catalog artifacts."""

from __future__ import annotations
import click
from pathlib import Path
from ..repositories import YamlStandardNameRepository
from ..storage.writer import write_catalog_artifacts


@click.command(name="build_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument(
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("imas_standard_names/resources/artifacts"),
)
@click.option("--quiet", is_flag=True, help="Suppress non-error output")
def build_catalog_cli(root: Path, out_dir: Path, quiet: bool):
    repo = YamlStandardNameRepository(root)
    entries = {e.name: e for e in repo.list()}
    written = write_catalog_artifacts(entries, out_dir)
    if not quiet:
        for w in written:
            click.echo(f"Wrote {w}")
