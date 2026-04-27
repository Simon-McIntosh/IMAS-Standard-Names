"""Top-level catalog site commands for Standard Names.

Provides ``serve`` and ``site-deploy`` Click commands for generating standalone
documentation sites from external catalog repositories containing YAML
standard name definitions.

Renamed in v0.7.0rc31: the previous ``catalog-site serve`` / ``catalog-site
deploy`` group was flattened to the top level as the ``catalog-site`` wrapper
added a level of nesting that no longer served a purpose (only one site type
exists). The mkdocs subprocess now uses ``sys.executable -m mkdocs`` so it
inherits the active Python environment regardless of which venv invokes the
``standard-names`` CLI.

This is intended for use in external catalog repositories, not for building
documentation for the imas-standard-names project itself.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import click

from ..rendering.catalog import CatalogRenderer

# Minimal mkdocs.yml template for versioned deployment (with mike plugin)
MKDOCS_DEPLOY_TEMPLATE = """\
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
        "mike is required for versioned documentation deployment.\n"
        "Install with: uv add --group docs mike\n"
        "Or: pip install mike"
    )


def _generate_site_content(
    catalog_path: Path,
    docs_dir: Path,
    site_name: str,
    mkdocs_template: str,
    site_url: str = "",
) -> int:
    """Generate mkdocs site content from catalog YAML files.

    Returns the number of standard names found.
    """
    renderer = CatalogRenderer(catalog_path)
    stats = renderer.get_stats()

    # Create docs structure
    docs_content_dir = docs_dir / "docs"
    docs_content_dir.mkdir(exist_ok=True)
    stylesheets_dir = docs_content_dir / "stylesheets"
    stylesheets_dir.mkdir(exist_ok=True)

    # Generate mkdocs.yml
    mkdocs_config = mkdocs_template.format(
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

    return stats["total_names"]


@click.command("serve")
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
    help="Host to bind to (default: 127.0.0.1; pass 0.0.0.0 to expose over an SSH tunnel)",
)
def serve_cmd(
    catalog_path: Path,
    site_name: str,
    port: int,
    host: str,
):
    """Serve catalog site locally for preview.

    CATALOG_PATH: Path to directory containing standard name YAML files.

    Generates a temporary mkdocs site and serves it locally. Does not
    require mike or a git repository. Use for previewing changes before
    deploying.
    """
    # Set up temporary docs directory
    temp_dir = tempfile.mkdtemp(prefix="sn-catalog-site-")
    docs_dir = Path(temp_dir)

    try:
        total_names = _generate_site_content(
            catalog_path=catalog_path,
            docs_dir=docs_dir,
            site_name=site_name,
            mkdocs_template=MKDOCS_SERVE_TEMPLATE,
            site_url=f"http://{host}:{port}/",
        )

        if total_names == 0:
            click.echo("Warning: No standard names found in catalog", err=True)

        click.echo(f"Generated site for {total_names} standard names")
        click.echo(f"Serving at http://{host}:{port}/")
        click.echo("Press Ctrl+C to stop...")

        # Serve via the active Python's mkdocs (handles venvs without mkdocs on PATH).
        result = subprocess.run(
            [sys.executable, "-m", "mkdocs", "serve", "--dev-addr", f"{host}:{port}"],
            cwd=docs_dir,
        )

        if result.returncode != 0:
            raise SystemExit(result.returncode)

    finally:
        shutil.rmtree(docs_dir, ignore_errors=True)


@click.command("site-deploy")
@click.argument(
    "catalog_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--version",
    "doc_version",
    required=True,
    help="Version string for deployment (e.g., 'v1.0', 'main', 'pr-123')",
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
    help="Push to gh-pages branch after deployment",
)
@click.option(
    "--set-default",
    is_flag=True,
    help="Set this version as the default (latest)",
)
def deploy_cmd(
    catalog_path: Path,
    doc_version: str,
    site_name: str,
    site_url: str,
    push: bool,
    set_default: bool,
):
    """Deploy versioned catalog site using mike.

    CATALOG_PATH: Path to directory containing standard name YAML files.

    Generates a mkdocs site and deploys it as a versioned documentation
    using mike. Requires a git repository and mike to be installed.

    Typical CI workflow:

        standard-names site-deploy ./standard_names --version v1.0 --push
    """
    if not _check_mike_available():
        click.echo(f"Error: {_mike_error_message()}", err=True)
        raise SystemExit(1)

    # Set up temporary docs directory
    temp_dir = tempfile.mkdtemp(prefix="sn-catalog-site-")
    docs_dir = Path(temp_dir)

    try:
        total_names = _generate_site_content(
            catalog_path=catalog_path,
            docs_dir=docs_dir,
            site_name=site_name,
            mkdocs_template=MKDOCS_DEPLOY_TEMPLATE,
            site_url=site_url,
        )

        if total_names == 0:
            click.echo("Warning: No standard names found in catalog", err=True)

        click.echo(f"Generated site for {total_names} standard names")

        # Deploy with mike (use sys.executable -m to inherit active venv).
        mike_args = [sys.executable, "-m", "mike", "deploy", doc_version]
        if set_default:
            mike_args.extend(["--update-aliases", "latest"])
        if push:
            mike_args.append("--push")

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

        click.echo(f"✓ Deployed version '{doc_version}'")
        if set_default:
            click.echo("✓ Set as default version (latest)")
        if push:
            click.echo("✓ Pushed to gh-pages")

    finally:
        shutil.rmtree(docs_dir, ignore_errors=True)


__all__ = ["serve_cmd", "deploy_cmd"]
