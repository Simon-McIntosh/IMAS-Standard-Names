"""CLI entrypoint for validation (structural + semantic)."""

from __future__ import annotations
import click
from pathlib import Path
from ..catalog.catalog import load_catalog
from .structural import run_structural_checks
from .semantic import run_semantic_checks


@click.command(name="validate_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--db",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional path to catalog.db; if provided and prefer-db not disabled will attempt SQLite load.",
)
@click.option(
    "--no-prefer-db",
    is_flag=True,
    help="Force YAML parsing even if SQLite is available.",
)
@click.option(
    "--require-fresh",
    is_flag=True,
    help="Reject stale SQLite artifact and fall back to YAML.",
)
def validate_catalog_cli(
    root: Path, db: Path | None, no_prefer_db: bool, require_fresh: bool
):
    # Load via dispatcher (this yields fully materialized models unless revalidate False is wired later via a flag)
    catalog = load_catalog(
        root, db_path=db, prefer_db=not no_prefer_db, require_fresh=require_fresh
    )
    entries = catalog.entries
    structural = run_structural_checks(entries)
    semantic = run_semantic_checks(entries)
    issues = structural + semantic
    if issues:
        click.echo("Validation FAILED:")
        for issue in issues:
            click.echo(f" - {issue}")
        raise SystemExit(1)
    click.echo("Validation PASSED (structural + semantic checks).")
