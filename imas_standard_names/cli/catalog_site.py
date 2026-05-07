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
# The nav: section is injected dynamically from the catalog structure.
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

{nav_section}

theme:
  name: material
  features:
    - navigation.tracking
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - search.suggest
    - toc.integrate

extra:
  version:
    provider: mike

markdown_extensions:
  - pymdownx.arithmatex:
      generic: true
  - pymdownx.details
  - footnotes
  - attr_list
  - md_in_html
  - toc:
      permalink: true
      toc_depth: 3

extra_css:
  - stylesheets/catalog.css

extra_javascript:
  - javascripts/mathjax.js
  - https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js
"""

# Simpler mkdocs.yml template for local preview (no mike plugin)
MKDOCS_SERVE_TEMPLATE = """\
site_name: "{site_name}"
site_url: "{site_url}"

plugins:
  - search

{nav_section}

theme:
  name: material
  features:
    - navigation.tracking
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - search.suggest
    - toc.integrate

markdown_extensions:
  - pymdownx.arithmatex:
      generic: true
  - pymdownx.details
  - footnotes
  - attr_list
  - md_in_html
  - toc:
      permalink: true
      toc_depth: 3

extra_css:
  - stylesheets/catalog.css

extra_javascript:
  - javascripts/mathjax.js
  - https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js
"""

CATALOG_CSS = """\
/* Standard Names Catalog — Multi-page Design */

/* Entry cards */
.sn-card {
    margin: 0.75rem 0 1.25rem;
    padding: 1rem 1.25rem;
    border-left: 3px solid var(--md-primary-fg-color);
    border-radius: 0 6px 6px 0;
    background: var(--md-code-bg-color);
    transition: border-color 0.2s;
}

.sn-card:target {
    border-left-color: var(--md-accent-fg-color);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.sn-card .sn-title {
    margin: 0 0 0.5rem;
    font-size: 1rem;
    overflow-wrap: anywhere;
    line-height: 1.4;
}

.sn-card p {
    margin: 0.4rem 0;
    font-size: 0.92rem;
    line-height: 1.5;
}

/* Compact metadata inline after title */
.sn-card .sn-title code {
    font-size: 0.82em;
    padding: 0.12em 0.3em;
    border-radius: 3px;
    background: var(--md-default-bg-color);
}

/* Collapsible documentation sections */
.sn-card details {
    margin: 0.6rem 0;
    border: 1px solid var(--md-default-fg-color--lightest);
    border-radius: 4px;
    padding: 0.5rem 0.75rem;
}

.sn-card details summary {
    cursor: pointer;
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--md-primary-fg-color);
}

.sn-card details[open] summary {
    margin-bottom: 0.5rem;
    border-bottom: 1px solid var(--md-default-fg-color--lightest);
    padding-bottom: 0.4rem;
}

/* See-also and sibling nav links */
.sn-card a[href^=\\"#\\"] {
    overflow-wrap: anywhere;
    font-size: 0.9rem;
}

/* Base group headings */
h2 {
    border-bottom: 2px solid var(--md-primary-fg-color--light);
    padding-bottom: 0.4rem;
    margin-top: 2rem;
}

/* Mermaid overflow */
.sn-card .mermaid {
    overflow-x: auto;
    max-width: 100%;
}

/* Domain overview table */
.md-typeset table:not([class]) {
    font-size: 0.88rem;
}

.md-typeset table:not([class]) td,
.md-typeset table:not([class]) th {
    padding: 0.5rem 0.75rem;
}
"""


def _check_mike_available() -> bool:
    """Check if mike is available in the environment."""
    return shutil.which("mike") is not None


def _find_git_root(catalog_path: Path) -> Path:
    """Walk up from *catalog_path* to find the nearest ``.git`` directory."""
    current = catalog_path.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


def _mike_error_message() -> str:
    """Return error message with installation instructions."""
    return (
        "mike is required for versioned documentation deployment.\n"
        "Install with: uv add --group docs mike\n"
        "Or: pip install mike"
    )


def _generate_nav_yaml(nav_structure: dict) -> str:
    """Convert nav structure dict to YAML nav: section for mkdocs.yml."""
    import yaml as _yaml  # noqa: PLC0415

    nav_list = [{"Home": "index.md"}]
    # Add catalog section from the renderer
    catalog_section = nav_structure.get("Catalog", [])
    if catalog_section:
        nav_list.append({"Catalog": list(catalog_section)})
    return "nav:\n" + _yaml.dump(nav_list, default_flow_style=False, indent=2)


def _generate_site_content(
    catalog_path: Path,
    docs_dir: Path,
    site_name: str,
    mkdocs_template: str,
    site_url: str = "",
) -> int:
    """Generate mkdocs site content from catalog YAML files.

    Uses multi-page layout: one page per physics domain for proper
    left-sidebar navigation in the Material theme.

    Returns the number of standard names found.
    """
    renderer = CatalogRenderer(catalog_path)
    stats = renderer.get_stats()

    # Create docs structure
    docs_content_dir = docs_dir / "docs"
    docs_content_dir.mkdir(exist_ok=True)
    stylesheets_dir = docs_content_dir / "stylesheets"
    stylesheets_dir.mkdir(exist_ok=True)

    # Generate multi-page catalog structure
    nav_structure = renderer.generate_site(docs_content_dir)

    # Generate nav YAML for mkdocs config
    nav_yaml = _generate_nav_yaml(nav_structure)

    # Generate mkdocs.yml
    mkdocs_config = mkdocs_template.format(
        site_name=site_name,
        site_url=site_url,
        nav_section=nav_yaml,
    )
    (docs_dir / "mkdocs.yml").write_text(mkdocs_config)

    # Generate CSS
    (stylesheets_dir / "catalog.css").write_text(CATALOG_CSS)

    # Generate deferred MathJax config
    js_dir = docs_content_dir / "javascripts"
    js_dir.mkdir(exist_ok=True)
    (js_dir / "mathjax.js").write_text(
        "window.MathJax = {\n"
        "  tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] },\n"
        "  options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'] },\n"
        "  startup: { typeset: true }\n"
        "};\n"
    )

    # Generate index.md from README or create default
    readme_path = catalog_path / "README.md"
    if readme_path.exists():
        index_content = readme_path.read_text(encoding="utf-8")
    else:
        index_content = f"# {site_name}\n\n"
        index_content += renderer.render_overview(link_prefix="catalog/")

    (docs_content_dir / "index.md").write_text(index_content)

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

        # Deploy with mike (use entry point script, not -m which requires __main__.py).
        mike_cmd = shutil.which("mike")
        if mike_cmd is None:
            click.echo(f"Error: {_mike_error_message()}", err=True)
            raise SystemExit(1)

        # mike needs to run inside the git repository (not the temp docs dir)
        # so it can commit to gh-pages. Point it to the mkdocs.yml via -F.
        git_root = _find_git_root(catalog_path)
        mkdocs_config = docs_dir / "mkdocs.yml"

        mike_args = [mike_cmd, "deploy", "-F", str(mkdocs_config), doc_version]
        if set_default:
            mike_args.extend(["--update-aliases", "latest"])
        if push:
            mike_args.append("--push")

        env = os.environ.copy()
        result = subprocess.run(
            mike_args,
            cwd=git_root,
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
