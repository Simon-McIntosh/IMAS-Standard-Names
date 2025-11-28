"""Documentation build command for Standard Names catalog.

Provides the `docs` Click command group for building standalone
documentation sites from external catalog repositories.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import click

from ..rendering.catalog import CatalogRenderer

# Minimal mkdocs.yml template for catalog-only documentation (with mike plugin)
MKDOCS_TEMPLATE = """\
site_name: "{site_name}"
site_url: "{site_url}"

plugins:
  - search
  - mike:
      canonical_version: latest
      version_selector: true
      css_dir: stylesheets
      javascript_dir: javascripts

nav:
  - Home: index.md
  - Standard Names: catalog.md

theme:
  name: material
  features:
    - navigation.tracking
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.top
    - search.highlight

extra:
  version:
    provider: mike

markdown_extensions:
  - pymdownx.arithmatex:
      generic: true
  - footnotes
  - attr_list
  - toc:
      permalink: true

extra_css:
  - stylesheets/catalog.css

extra_javascript:
  - https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js
"""

# Simpler mkdocs.yml template for local preview (no mike plugin)
MKDOCS_SERVE_TEMPLATE = """\
site_name: "{site_name}"
site_url: "{site_url}"

plugins:
  - search

nav:
  - Home: index.md
  - Standard Names: catalog.md

theme:
  name: material
  features:
    - navigation.tracking
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.top
    - search.highlight

markdown_extensions:
  - pymdownx.arithmatex:
      generic: true
  - footnotes
  - attr_list
  - toc:
      permalink: true

extra_css:
  - stylesheets/catalog.css

extra_javascript:
  - https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js
"""

CATALOG_CSS = """\
/* Standard Names Catalog Styles */
.standard-name {
    margin-bottom: 2rem;
    padding: 1rem;
    border-left: 3px solid var(--md-primary-fg-color);
}

.standard-name h4 {
    margin-top: 0;
    color: var(--md-primary-fg-color);
}

.standard-name code {
    background-color: var(--md-code-bg-color);
    padding: 0.2em 0.4em;
    border-radius: 3px;
}
"""


def _check_mike_available() -> bool:
    """Check if mike is available in the environment."""
    return shutil.which("mike") is not None


def _mike_error_message() -> str:
    """Return error message with installation instructions."""
    return (
        "mike is required for versioned documentation.\n"
        "Install with: uv add --group docs mike\n"
        "Or: pip install mike"
    )


@click.group("docs")
def docs_cmd():
    """Documentation build commands for catalog sites."""


@docs_cmd.command("build")
@click.argument(
    "catalog_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--version",
    "doc_version",
    required=True,
    help="Version string for docs (e.g., 'v0.1', 'main', 'pr-123')",
)
@click.option(
    "--site-name",
    default="Standard Names Catalog",
    help="Site name for documentation",
)
@click.option(
    "--site-url",
    default="",
    help="Site URL for documentation",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push to gh-pages branch after build",
)
@click.option(
    "--set-default",
    is_flag=True,
    help="Set this version as the default",
)
@click.option(
    "--output",
    "output_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for generated docs (default: temporary directory)",
)
def build_docs(
    catalog_path: Path,
    doc_version: str,
    site_name: str,
    site_url: str,
    push: bool,
    set_default: bool,
    output_dir: Path | None,
):
    """Build documentation site from catalog YAML files.

    CATALOG_PATH: Path to directory containing standard name YAML files.

    Generates a complete mkdocs site with:
    - index.md from catalog README.md (if present)
    - catalog.md with rendered standard names catalog

    Then deploys using mike for versioned documentation.
    """
    if not _check_mike_available():
        click.echo(f"Error: {_mike_error_message()}", err=True)
        raise SystemExit(1)

    # Create renderer and generate content
    renderer = CatalogRenderer(catalog_path)
    stats = renderer.get_stats()

    if stats["total_names"] == 0:
        click.echo("Warning: No standard names found in catalog", err=True)

    # Set up docs directory
    if output_dir:
        docs_dir = output_dir
        docs_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        temp_dir = tempfile.mkdtemp(prefix="sn-docs-")
        docs_dir = Path(temp_dir)
        cleanup = True

    try:
        # Create docs structure
        docs_content_dir = docs_dir / "docs"
        docs_content_dir.mkdir(exist_ok=True)
        stylesheets_dir = docs_content_dir / "stylesheets"
        stylesheets_dir.mkdir(exist_ok=True)

        # Generate mkdocs.yml
        mkdocs_config = MKDOCS_TEMPLATE.format(
            site_name=site_name,
            site_url=site_url,
        )
        (docs_dir / "mkdocs.yml").write_text(mkdocs_config)

        # Generate CSS
        (stylesheets_dir / "catalog.css").write_text(CATALOG_CSS)

        # Generate index.md from README or create default
        readme_path = catalog_path / "README.md"
        if readme_path.exists():
            index_content = readme_path.read_text(encoding="utf-8")
        else:
            # Generate default index from catalog stats
            # Use link_prefix to point to catalog.md for category links
            index_content = f"# {site_name}\n\n"
            index_content += renderer.render_overview(link_prefix="catalog.md")

        (docs_content_dir / "index.md").write_text(index_content)

        # Generate catalog.md (no link prefix needed, anchors are on same page)
        catalog_content = "# Standard Names Catalog\n\n"
        catalog_content += renderer.render_overview()
        catalog_content += "\n---\n\n"
        catalog_content += renderer.render_catalog()
        (docs_content_dir / "catalog.md").write_text(catalog_content)

        click.echo(f"Generated docs for {stats['total_names']} standard names")

        # Build with mike
        mike_args = ["mike", "deploy", doc_version]
        if set_default:
            mike_args.append("--update-aliases")
            mike_args.append("latest")
        if push:
            mike_args.append("--push")

        # Run mike from the docs directory
        env = os.environ.copy()
        result = subprocess.run(
            mike_args,
            cwd=docs_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            click.echo(f"mike deploy failed:\n{result.stderr}", err=True)
            raise SystemExit(1)

        click.echo(f"✓ Deployed docs version '{doc_version}'")
        if set_default:
            click.echo("✓ Set as default version (latest)")
        if push:
            click.echo("✓ Pushed to gh-pages")

    finally:
        if cleanup and output_dir is None:
            shutil.rmtree(docs_dir, ignore_errors=True)


@docs_cmd.command("alias")
@click.option(
    "--version",
    "doc_version",
    required=True,
    help="Version to create alias for",
)
@click.option(
    "--alias",
    required=True,
    help="Alias name (e.g., 'latest', 'stable')",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push to gh-pages branch",
)
def alias_docs(doc_version: str, alias: str, push: bool):
    """Create a version alias for documentation.

    Creates an alias pointing to an existing version, useful for
    'latest' or 'stable' aliases.
    """
    if not _check_mike_available():
        click.echo(f"Error: {_mike_error_message()}", err=True)
        raise SystemExit(1)

    mike_args = ["mike", "alias", doc_version, alias]
    if push:
        mike_args.append("--push")

    result = subprocess.run(
        mike_args,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        click.echo(f"mike alias failed:\n{result.stderr}", err=True)
        raise SystemExit(1)

    click.echo(f"✓ Created alias '{alias}' -> '{doc_version}'")
    if push:
        click.echo("✓ Pushed to gh-pages")


@docs_cmd.command("serve")
@click.argument(
    "catalog_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--site-name",
    default="Standard Names Catalog",
    help="Site name for documentation",
)
@click.option(
    "--port",
    default=8000,
    help="Port to serve on (default: 8000)",
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind to (default: 127.0.0.1)",
)
def serve_docs(
    catalog_path: Path,
    site_name: str,
    port: int,
    host: str,
):
    """Serve documentation locally for preview.

    CATALOG_PATH: Path to directory containing standard name YAML files.

    Generates a temporary mkdocs site and serves it locally for preview.
    Does not require mike or a git repository.
    """
    # Create renderer and generate content
    renderer = CatalogRenderer(catalog_path)
    stats = renderer.get_stats()

    if stats["total_names"] == 0:
        click.echo("Warning: No standard names found in catalog", err=True)

    # Set up temporary docs directory
    temp_dir = tempfile.mkdtemp(prefix="sn-docs-serve-")
    docs_dir = Path(temp_dir)

    try:
        # Create docs structure
        docs_content_dir = docs_dir / "docs"
        docs_content_dir.mkdir(exist_ok=True)
        stylesheets_dir = docs_content_dir / "stylesheets"
        stylesheets_dir.mkdir(exist_ok=True)

        # Generate mkdocs.yml (without mike plugin for local serving)
        mkdocs_config = MKDOCS_SERVE_TEMPLATE.format(
            site_name=site_name,
            site_url=f"http://{host}:{port}/",
        )
        (docs_dir / "mkdocs.yml").write_text(mkdocs_config)

        # Generate CSS
        (stylesheets_dir / "catalog.css").write_text(CATALOG_CSS)

        # Generate index.md from README or create default
        readme_path = catalog_path / "README.md"
        if readme_path.exists():
            index_content = readme_path.read_text(encoding="utf-8")
        else:
            # Generate default index from catalog stats
            # Use link_prefix to point to catalog.md for category links
            index_content = f"# {site_name}\n\n"
            index_content += renderer.render_overview(link_prefix="catalog.md")

        (docs_content_dir / "index.md").write_text(index_content)

        # Generate catalog.md (no link prefix needed, anchors are on same page)
        catalog_content = "# Standard Names Catalog\n\n"
        catalog_content += renderer.render_overview()
        catalog_content += "\n---\n\n"
        catalog_content += renderer.render_catalog()
        (docs_content_dir / "catalog.md").write_text(catalog_content)

        click.echo(f"Generated docs for {stats['total_names']} standard names")
        click.echo(f"Serving at http://{host}:{port}/")
        click.echo("Press Ctrl+C to stop...")

        # Serve with mkdocs
        result = subprocess.run(
            ["mkdocs", "serve", "--dev-addr", f"{host}:{port}"],
            cwd=docs_dir,
        )

        if result.returncode != 0:
            raise SystemExit(result.returncode)

    finally:
        shutil.rmtree(docs_dir, ignore_errors=True)


__all__ = ["docs_cmd"]
