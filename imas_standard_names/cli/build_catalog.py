"""CLI command: build catalog SQLite artifact.

Replaces previous JSON artifact generation. Produces a single
`catalog.db` SQLite file containing all validated standard names
and related provenance/meta tables.
"""

from __future__ import annotations
import click
from pathlib import Path
from ..repositories import YamlStandardNameRepository
from ..storage.sqlite import build_sqlite_catalog
import time


@click.command(name="build_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--db",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=Path("imas_standard_names/resources/artifacts/catalog.db"),
    help="Path to output SQLite catalog artifact.",
)
@click.option(
    "--version", default="dev", help="Version string to embed in artifact metadata."
)
@click.option("--quiet", is_flag=True, help="Suppress non-error output")
@click.option(
    "--rebuild-if-stale/--no-rebuild-if-stale",
    default=True,
    show_default=True,
    help="Rebuild only when YAML sources changed (uses max mtime).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force rebuild even if artifact appears fresh.",
)
def build_catalog_cli(
    root: Path, db: Path, version: str, quiet: bool, rebuild_if_stale: bool, force: bool
):
    start = time.time()
    # Freshness check: if db exists and not forcing, compare stored max_yaml_mtime
    if db.exists() and (rebuild_if_stale or not force):
        try:
            import sqlite3

            conn = sqlite3.connect(db)
            cur = conn.cursor()
            cur.execute("SELECT value FROM meta WHERE key='max_yaml_mtime'")
            row = cur.fetchone()
            conn.close()
            db_mtime = float(row[0]) if row and row[0] else 0.0
            yaml_mtimes = [p.stat().st_mtime for p in Path(root).rglob("*.yml")]
            current_max = max(yaml_mtimes) if yaml_mtimes else 0.0
            fresh = current_max <= db_mtime + 1e-9
            if fresh and rebuild_if_stale and not force:
                if not quiet:
                    click.echo(f"Catalog fresh: {db} (no rebuild needed)")
                return
        except Exception:
            # Continue with rebuild on any inspection error
            pass
    repo = YamlStandardNameRepository(root)
    entries = {e.name: e for e in repo.list()}
    # derive max mtime for freshness tracking
    mtimes = [p.stat().st_mtime for p in root.rglob("*.yml")]
    max_mtime = max(mtimes) if mtimes else None
    # Cast to satisfy static type expectations (StandardName derives from StandardNameBase)
    path = build_sqlite_catalog(entries, db, version=version, max_yaml_mtime=max_mtime)  # type: ignore[arg-type]
    if not quiet:
        click.echo(
            f"Rebuilt {path} ({len(entries)} entries) in {time.time() - start:.2f}s"
        )
