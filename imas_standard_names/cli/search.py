"""Search command for Standard Names catalog.

Provides the `search` Click command which can search either an existing
SQLite catalog (file mode) or load YAML definitions into memory.
"""

from __future__ import annotations

from pathlib import Path
import json
import click

from ..paths import CatalogPaths
from ..repository import StandardNameRepository
from ..catalog.sqlite_read import CatalogRead


@click.command("search")
@click.argument("query", type=str)
@click.argument("yaml_path", required=False, type=str)
@click.option(
    "--limit", default=20, show_default=True, help="Maximum number of results"
)
@click.option("--meta", is_flag=True, help="Include score/highlights in JSON output")
@click.option(
    "--mode",
    type=click.Choice(["auto", "file", "memory"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Search source preference: file (built DB), memory (fresh YAML load), or auto (prefer file).",
)
def search_cmd(
    query: str, yaml_path: str | Path | None, limit: int, meta: bool, mode: str
):
    """Search the catalog for QUERY, optionally using a built SQLite file.

    ROOT optional: path or pattern (see build for semantics).
    """
    paths = CatalogPaths("standard_names" if yaml_path is None else yaml_path, None)
    resolved_root = paths.yaml_path
    db_path = paths.catalog_path
    results = None
    source_label = "memory"
    use_file = False
    if mode.lower() == "file":
        use_file = True
    elif mode.lower() == "auto":
        use_file = db_path.exists()
    if use_file:
        try:
            ro = CatalogRead(db_path)
            results = ro.search(query, limit=limit, with_meta=meta)
            source_label = "file"
        except Exception:  # pragma: no cover - fallback
            results = None
    if results is None:
        repo = StandardNameRepository(resolved_root)
        results = repo.search(query, limit=limit, with_meta=meta)
        source_label = "memory"
    if meta:
        payload = []
        for r in results:  # type: ignore[assignment]
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
            else:  # StandardName model
                payload.append(
                    {
                        "name": getattr(r, "name", None),
                        "score": None,
                        "highlight_description": None,
                        "highlight_documentation": None,
                        "source": source_label,
                    }
                )
        click.echo(json.dumps(payload, indent=2))
    else:
        if not results:
            # No matches -> distinctive non-zero exit code for scripting
            raise SystemExit(1)
        # Print count header only if more than one to stay minimal for single result
        if len(results) > 1:
            click.echo(f"{len(results)} results:")
        for e in results:  # type: ignore[assignment]
            # Results may be plain strings, dicts (meta), or StandardName models
            if isinstance(e, str):
                click.echo(e)
                continue
            if isinstance(e, dict):
                nm = e.get("name")
                if nm:
                    click.echo(nm)
                continue
            # Fallback: model object
            click.echo(getattr(e, "name", ""))


__all__ = ["search_cmd"]
