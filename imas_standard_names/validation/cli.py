"""CLI entrypoint for validation (structural + semantic + quality)."""

from __future__ import annotations

import json
from pathlib import Path

import click

from ..database.integrity import verify_integrity
from ..database.read import CatalogRead
from ..paths import CATALOG_DIRNAME
from ..repository import StandardNameCatalog
from .quality import format_quality_report, run_quality_checks
from .semantic import run_semantic_checks
from .structural import run_structural_checks


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
@click.option(
    "--quality-check/--no-quality-check",
    default=True,
    show_default=True,
    help="Enable or disable quality checks on descriptions",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail validation on quality warnings (not just errors)",
)
@click.option(
    "--summary",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default=None,
    help="Output machine-readable summary (text or json format)",
)
def validate_catalog_cli(
    root: Path,
    mode: str,
    verify: bool,
    full: bool,
    quality_check: bool,
    strict: bool,
    summary: str | None,
):
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
                raise SystemExit(1) from e
            use_file = False

    if not use_file:
        repo = StandardNameCatalog(root)
        entries = {m.name: m for m in repo.list()}
        # No integrity verification in memory mode (fresh load)

    structural = run_structural_checks(entries)
    semantic = run_semantic_checks(entries)
    issues = structural + semantic

    # Run quality checks if enabled
    quality_issues = []
    if quality_check:
        quality_issues = run_quality_checks(entries)
        if quality_issues and not summary:
            click.echo("")
            click.echo(format_quality_report(quality_issues, show_level=None))
            click.echo("")

    # Count issues by level
    quality_errors = [msg for level, msg in quality_issues if level == "error"]
    quality_warnings = [msg for level, msg in quality_issues if level == "warning"]
    error_count = len(issues) + len(quality_errors)
    warning_count = len(quality_warnings)
    info_count = len([msg for level, msg in quality_issues if level == "info"])
    entry_count = len(entries)

    # Determine pass/fail status
    # Fail if: structural/semantic errors, quality errors, or (strict mode + warnings)
    has_errors = bool(issues) or bool(quality_errors)
    has_strict_warnings = strict and bool(quality_warnings)
    has_integrity_issues = bool(integrity_issues)

    # Output summary if requested
    if summary:
        if summary == "json":
            result = {
                "passed": not has_errors
                and not has_strict_warnings
                and not has_integrity_issues,
                "entries": entry_count,
                "errors": error_count,
                "warnings": warning_count,
                "info": info_count,
                "integrity_issues": len(integrity_issues),
            }
            click.echo(json.dumps(result))
        else:  # text
            status = "✓" if not has_errors and not has_strict_warnings else "✗"
            click.echo(
                f"{status} Validated {entry_count} entries "
                f"({error_count} errors, {warning_count} warnings)"
            )
        # Still exit with appropriate code
        if has_errors or has_strict_warnings:
            raise SystemExit(1)
        if has_integrity_issues:
            raise SystemExit(2)
        return

    # Original verbose output
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

    # Check for quality errors that should fail validation
    if quality_errors:
        click.echo(f"Validation FAILED: {len(quality_errors)} quality error(s)")
        raise SystemExit(1)

    # Check for warnings in strict mode
    if has_strict_warnings:
        click.echo(
            f"Validation FAILED (strict): {len(quality_warnings)} quality warning(s)"
        )
        raise SystemExit(1)

    if integrity_issues:
        click.echo("Validation PASSED (content) but integrity discrepancies detected.")
        raise SystemExit(2)
    click.echo("Validation PASSED (structural + semantic + quality checks).")
