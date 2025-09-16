"""CLI entrypoint for validation (structural + semantic)."""

from __future__ import annotations
import click
from pathlib import Path
from ..storage.loader import load_catalog
from .structural import run_structural_checks
from .semantic import run_semantic_checks


@click.command(name="validate_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
def validate_catalog_cli(root: Path):
    entries = load_catalog(root)
    structural = run_structural_checks(entries)
    semantic = run_semantic_checks(entries)
    issues = structural + semantic
    if issues:
        click.echo("Validation FAILED:")
        for issue in issues:
            click.echo(f" - {issue}")
        raise SystemExit(1)
    click.echo("Validation PASSED (structural + semantic checks).")
