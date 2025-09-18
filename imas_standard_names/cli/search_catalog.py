from __future__ import annotations
import click
from pathlib import Path
from ..repository import StandardNameRepository
from ..catalog.sqlite_read import CatalogRead


@click.command(name="search_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("query", type=str)
@click.option(
    "--limit", default=20, show_default=True, help="Maximum number of results"
)
@click.option("--meta", is_flag=True, help="Include score and highlights in output")
@click.option(
    "--mode",
    type=click.Choice(["auto", "file", "memory"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Search source preference: file (built DB), memory (fresh YAML load), or auto (prefer file).",
)
def search_catalog_cli(
    root: Path,
    query: str,
    limit: int,
    meta: bool,
    mode: str,
):
    """Search the catalog for QUERY using FTS (ranked) when available.

    Prints either a simple list of names (default) or a JSON array with
    metadata when --meta is used.
    """
    results = None
    source_label = "memory"
    db_path = root / "artifacts" / "catalog.db"
    use_file = False
    if mode.lower() == "file":
        use_file = True
    elif mode.lower() == "auto":
        use_file = db_path.exists()
    # File-backed read-only
    if use_file:
        try:
            ro = CatalogRead(db_path)
            results = ro.search(query, limit=limit, with_meta=meta)
            source_label = "file"
        except Exception:  # fall back silently
            results = None
    if results is None:
        repo = StandardNameRepository(root)
        results = repo.search(query, limit=limit, with_meta=meta)
        source_label = "memory"
    if meta:
        import json

        # results is List[dict]
        payload = []
        for r in results:  # type: ignore[assignment]
            # r expected dict from catalog.search when with_meta=True
            if isinstance(r, dict):
                payload.append(
                    {
                        "name": r.get("name"),
                        "score": r.get("score"),
                        "highlight_description": r.get("highlight_description"),
                        "highlight_documentation": r.get("highlight_documentation"),
                        "source": source_label,
                    }
                )
        click.echo(json.dumps(payload, indent=2))
    else:
        # results expected List[StandardName]; guard against unexpected dicts
        for e in results:  # type: ignore[assignment]
            if isinstance(e, dict):
                nm = e.get("name")
                if nm:
                    click.echo(nm)
                continue
            click.echo(getattr(e, "name", ""))
