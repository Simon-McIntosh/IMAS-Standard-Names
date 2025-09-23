"""CLI entrypoint for validation (structural + semantic)."""

from __future__ import annotations
import click
from pathlib import Path
from ..repository import StandardNameRepository
from ..paths import CATALOG_DIRNAME
from ..catalog.sqlite_read import CatalogRead
from ..catalog.integrity import verify_integrity
from .structural import run_structural_checks
from .semantic import run_semantic_checks


@click.command(name="validate_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--mode",
    type=click.Choice(["auto", "file", "memory"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Source: file (built DB), memory (fresh YAML), or auto (prefer file).",
)
@click.option("--verify", is_flag=True, help="Verify integrity table (file mode only)")
@click.option(
    "--full",
    is_flag=True,
    help="When verifying, recompute hashes even if metadata matches",
)
def validate_catalog_cli(root: Path, mode: str, verify: bool, full: bool):
    db_path = root / CATALOG_DIRNAME / "catalog.db"
    use_file = False
    if mode == "file":
        use_file = True
    elif mode == "auto":
        use_file = db_path.exists()

    integrity_issues = []
    entries = {}
    if use_file:
        try:
            ro = CatalogRead(db_path)
            entries = {m.name: m for m in ro.list()}
            if verify:
                integrity_issues = verify_integrity(root, db_path, full=full)
        except Exception as e:  # fallback to memory if auto
            if mode == "file":
                click.echo(f"Failed to open file-backed catalog: {e}")
                raise SystemExit(1)
            use_file = False

    if not use_file:
        repo = StandardNameRepository(root)
        entries = {m.name: m for m in repo.list()}
        # No integrity verification in memory mode (fresh load)

    structural = run_structural_checks(entries)
    semantic = run_semantic_checks(entries)
    issues = structural + semantic

    if integrity_issues:
        click.echo("Integrity issues:")
        for iss in integrity_issues:
            code = iss.get("code")
            name = iss.get("name", iss.get("detail", ""))
            click.echo(f" - {code}: {name}")
    if issues:
        click.echo("Validation FAILED:")
        for issue in issues:
            click.echo(f" - {issue}")
        raise SystemExit(1 if not integrity_issues else 2)
    if integrity_issues:
        click.echo("Validation PASSED (content) but integrity discrepancies detected.")
        raise SystemExit(2)
    click.echo("Validation PASSED (structural + semantic checks).")
