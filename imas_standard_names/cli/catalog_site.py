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

# Shared markdown / theme / extras for both the served and deployed sites.
# Mermaid is wired through ``pymdownx.superfences`` — the Material theme
# automatically includes the mermaid.js runtime when this custom_fence is
# configured, so ```mermaid blocks render inline without an extra plugin.
_THEME_BLOCK = """\
theme:
  name: material
  features:
    - navigation.tracking
    - navigation.tabs
    - navigation.tabs.sticky
    - navigation.top
    - search.highlight
    - search.suggest
    - toc.follow
    - content.code.copy
  palette:
    - scheme: default
      primary: white
      accent: grey
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: black
      accent: grey
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
"""

_MARKDOWN_BLOCK = """\
markdown_extensions:
  - pymdownx.arithmatex:
      generic: true
  - pymdownx.details
  - pymdownx.tabbed:
      alternate_style: true
  - footnotes
  - attr_list
  - md_in_html
  - toc:
      permalink: true
      toc_depth: 2
"""

_EXTRAS_BLOCK = """\
extra_css:
  - stylesheets/catalog.css

extra_javascript:
  - javascripts/mathjax.js
  - https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js
"""

# Minimal mkdocs.yml template for versioned deployment (with mike plugin)
# The nav: section is injected dynamically from the catalog structure.
MKDOCS_DEPLOY_TEMPLATE = (
    """\
site_name: "{site_name}"
site_url: "{site_url}"

plugins:
  - search
  - mermaid2
  - mike:
      canonical_version: latest
      version_selector: true
      css_dir: stylesheets
      javascript_dir: javascripts

{nav_section}

"""
    + _THEME_BLOCK
    + """
extra:
  version:
    provider: mike

"""
    + _MARKDOWN_BLOCK
    + "\n"
    + _EXTRAS_BLOCK
)

# Simpler mkdocs.yml template for local preview (no mike plugin)
MKDOCS_SERVE_TEMPLATE = (
    """\
site_name: "{site_name}"
site_url: "{site_url}"

plugins:
  - search
  - mermaid2

{nav_section}

"""
    + _THEME_BLOCK
    + "\n"
    + _MARKDOWN_BLOCK
    + "\n"
    + _EXTRAS_BLOCK
)

CATALOG_CSS = """\
/* Standard Names Catalog — name-as-heading reference design.
   Goal: the canonical name is the most prominent element on every
   entry, with no chromed accents or coloured rules that compete for
   attention. Mermaid diagrams render inline. */

/* ---------- Layout & rhythm ---------- */
.md-typeset .sn-domain-summary {
    color: var(--md-default-fg-color--light);
    font-size: 0.9rem;
    margin: 0.2rem 0 1.6rem;
}

/* Canonical name heading — monospace, prominent, no blue underline. */
.md-typeset h2.sn-name,
.md-typeset h2[id].sn-name {
    font-family: var(--md-code-font, "Roboto Mono", monospace);
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: 0;
    color: var(--md-default-fg-color);
    border-bottom: none !important;
    margin: 2.2rem 0 0.35rem;
    padding-top: 0.35rem;
    border-top: 1px solid var(--md-default-fg-color--lightest);
    line-height: 1.35;
    overflow-wrap: anywhere;
}

.md-typeset h2.sn-name:target {
    color: var(--md-default-fg-color);
    background: linear-gradient(
        to right,
        rgba(0, 0, 0, 0.04),
        rgba(0, 0, 0, 0)
    );
    padding-left: 0.4rem;
}

[data-md-color-scheme="slate"] .md-typeset h2.sn-name:target {
    background: linear-gradient(
        to right,
        rgba(255, 255, 255, 0.06),
        rgba(255, 255, 255, 0)
    );
}

/* First entry on the page sits flush with the summary line. */
.md-typeset .sn-domain-summary + h2.sn-name {
    border-top: none;
    margin-top: 0.5rem;
    padding-top: 0;
}

/* ---------- Meta line beneath name ---------- */
.md-typeset .sn-meta-line {
    margin: 0 0 0.5rem;
    font-size: 0.78rem;
    color: var(--md-default-fg-color--light);
    letter-spacing: 0.01em;
}

.md-typeset .sn-unit {
    font-family: var(--md-code-font, "Roboto Mono", monospace);
    background: var(--md-code-bg-color);
    color: var(--md-default-fg-color);
    padding: 0.05rem 0.4rem;
    border-radius: 0.25rem;
    font-size: 0.78rem;
}

.md-typeset .sn-kind,
.md-typeset .sn-sources {
    font-size: 0.74rem;
    color: var(--md-default-fg-color--light);
}

/* ---------- Description (one-line italic blurb) ---------- */
.md-typeset h2.sn-name + .sn-meta-line + p em,
.md-typeset h2.sn-name + p em {
    font-style: italic;
}

/* ---------- Documentation block ---------- */
.md-typeset .sn-docs {
    font-size: 0.86rem;
    line-height: 1.55;
    color: var(--md-default-fg-color);
    margin: 0.4rem 0 0.6rem;
}

.md-typeset .sn-docs p {
    margin: 0.4rem 0;
}

/* ---------- Mermaid container — prominent and visible by default. */
.md-typeset .sn-mermaid {
    margin: 0.7rem 0 0.6rem;
    padding: 0.5rem 0.6rem;
    background: var(--md-code-bg-color);
    border-radius: 0.3rem;
    overflow-x: auto;
}

.md-typeset .sn-mermaid .mermaid {
    text-align: center;
}

/* Make node click affordance discoverable. */
.md-typeset .sn-mermaid .clickable {
    cursor: pointer;
}

/* ---------- See also / sibling nav ---------- */
.md-typeset .sn-see-also,
.md-typeset .sn-meta {
    margin: 0.25rem 0;
    font-size: 0.82rem;
    color: var(--md-default-fg-color--light);
}

.md-typeset .sn-meta-label {
    font-weight: 600;
    color: var(--md-default-fg-color);
    margin-right: 0.2rem;
}

.md-typeset .sn-see-also a,
.md-typeset .sn-meta a {
    color: var(--md-typeset-a-color);
    overflow-wrap: anywhere;
}

/* ---------- Badges ---------- */
.md-typeset .sn-badge {
    display: inline-block;
    font-size: 0.7rem;
    padding: 0.05rem 0.4rem;
    border-radius: 0.6rem;
    font-weight: 500;
    vertical-align: middle;
}

.md-typeset .sn-badge-pending {
    background: var(--md-default-fg-color--lightest);
    color: var(--md-default-fg-color--light);
}

/* ---------- Domain overview ---------- */
.md-typeset .sn-domain-grid table {
    font-size: 0.9rem;
}

.md-typeset .sn-domain-grid td,
.md-typeset .sn-domain-grid th {
    padding: 0.4rem 0.8rem;
}

/* Tone down the default H1 underline on domain pages. */
.md-typeset h1 {
    border-bottom: none;
    padding-bottom: 0;
    color: var(--md-default-fg-color);
}

/* Generic group headings (overview, indexes) — quiet underline. */
.md-typeset h2 {
    border-bottom: 1px solid var(--md-default-fg-color--lightest);
    padding-bottom: 0.2rem;
    margin-top: 1.6rem;
}

/* Permalink anchors — keep them but make them quiet until hover. */
.md-typeset .headerlink {
    color: var(--md-default-fg-color--lightest);
    opacity: 0;
    transition: opacity 0.1s;
}

.md-typeset h2:hover .headerlink {
    opacity: 1;
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
    # Flatten catalog domains directly into the top-level nav
    catalog_section = nav_structure.get("Catalog", [])
    for entry in catalog_section:
        nav_list.append(entry)
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
