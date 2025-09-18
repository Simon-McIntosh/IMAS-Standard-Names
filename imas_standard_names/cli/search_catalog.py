from __future__ import annotations
import click
from pathlib import Path
from ..catalog.catalog import load_catalog


@click.command(name="search_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("query", type=str)
@click.option(
    "--limit", default=20, show_default=True, help="Maximum number of results"
)
@click.option("--meta", is_flag=True, help="Include score and highlights in output")
@click.option(
    "--db",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Explicit path to catalog.db (optional)",
)
@click.option(
    "--no-prefer-db", is_flag=True, help="Force YAML even if SQLite is available"
)
@click.option(
    "--require-fresh",
    is_flag=True,
    help="Reject stale SQLite artifact and fallback to YAML",
)
def search_catalog_cli(
    root: Path,
    query: str,
    limit: int,
    meta: bool,
    db: Path | None,
    no_prefer_db: bool,
    require_fresh: bool,
):
    """Search the catalog for QUERY using FTS (ranked) when available.

    Prints either a simple list of names (default) or a JSON array with
    metadata when --meta is used.
    """
    catalog = load_catalog(
        root=root,
        db_path=db,
        prefer_db=not no_prefer_db,
        strict=True,
        require_fresh=require_fresh,
    )
    results = catalog.search(query, limit=limit, with_meta=meta)
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
                        "source": catalog.source,
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
