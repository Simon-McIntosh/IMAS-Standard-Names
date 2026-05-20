"""Catalog site CLI — Vite SPA build + gh-pages deploy.

Replaces the previous MkDocs-based pipeline with a Vite + React SPA.
The CLI signature is unchanged for backwards compatibility with ISNC's
CI workflow:

    standard-names site-deploy <catalog-dir> --version V [--push] [--set-default] [--site-name NAME] [--site-url URL]
    standard-names serve <catalog-dir> [--port 8000] [--host 127.0.0.1] [--site-name NAME]

The ``--site-name`` and ``--site-url`` options are retained as no-ops
with deprecation warnings; the SPA carries a fixed title and does not
need a configured ``site_url``.

Two subprocesses are involved:

* ``npm ci && npm run build`` inside ``site/`` — builds the SPA bundle
  into ``site/dist`` (CI-style reproducible install).
* ``npm run dev`` for ``serve`` — Vite's dev server.

Node 20+ is required. If ``node`` / ``npm`` are missing, the CLI fails
fast with a clear error message rather than after running the dataset
builder.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import click

from ..catalog.dataset import write_site_dataset
from ..catalog.gh_pages import deploy as deploy_to_gh_pages

# ``site/`` is checked into the repo at the same level as
# ``imas_standard_names/``. ``__file__`` is
# ``imas_standard_names/cli/catalog_site.py`` so two ``parents`` up
# lands at the repo root. This path is only valid in a source checkout;
# when installed as a package, callers must pass ``--site-dir`` explicitly.
_DEFAULT_SITE_DIR = Path(__file__).resolve().parents[2] / "site"

__all__ = ["deploy_cmd", "serve_cmd"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_node_available() -> bool:
    return shutil.which("npm") is not None and shutil.which("node") is not None


def _resolve_site_dir(site_dir: Path | None) -> Path:
    """Return the validated site directory path.

    If ``site_dir`` is provided explicitly (e.g. via ``--site-dir``),
    use it directly. Otherwise fall back to the default source-checkout
    relative path.
    """
    resolved = (site_dir or _DEFAULT_SITE_DIR).resolve()
    if not (resolved / "package.json").exists():
        raise click.ClickException(
            f"site/ scaffold missing at {resolved}. "
            "Pass --site-dir pointing to the imas-standard-names site/ directory, "
            "or run from a source checkout."
        )
    return resolved


def _ensure_node_toolchain() -> None:
    if not _check_node_available():
        raise click.ClickException(
            "Node.js + npm required to build the catalog SPA. "
            "Install Node 20+ and ensure both `node` and `npm` are on PATH."
        )


def _run(cmd: list[str], *, cwd: Path) -> None:
    """Run a subprocess, raising a ``ClickException`` on non-zero exit."""
    result = subprocess.run(cmd, cwd=cwd, check=False)
    if result.returncode != 0:
        raise click.ClickException(
            f"{' '.join(cmd)} (cwd={cwd}) exited with code {result.returncode}"
        )


def _build_spa(dist_dir: Path, site_dir: Path) -> None:
    """Build the Vite SPA into ``dist_dir``.

    Runs ``npm ci`` (lockfile-driven, reproducible) followed by
    ``npm run build`` inside ``site_dir``. The Vite build output lives
    in ``site_dir/dist`` by convention; we copy it into ``dist_dir`` so
    callers can place it anywhere (e.g. a tempdir for deployment).
    """
    _ensure_node_toolchain()
    _run(["npm", "ci"], cwd=site_dir)
    _run(["npm", "run", "build"], cwd=site_dir)

    vite_dist = site_dir / "dist"
    if not vite_dist.exists():
        raise click.ClickException(f"Vite build produced no output at {vite_dist}")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    shutil.copytree(vite_dist, dist_dir)


def _build_site(
    catalog_path: Path,
    dist_dir: Path,
    site_dir: Path,
    *,
    include_draft: bool = False,
) -> int:
    """Build the SPA and write the dataset JSON next to ``index.html``.

    Returns the number of standard names written so callers can surface
    the count to the user.
    """
    _build_spa(dist_dir, site_dir)
    return write_site_dataset(
        catalog_path, dist_dir / "data.json", include_draft=include_draft
    )


def _find_git_root(catalog_path: Path) -> Path:
    """Walk up from ``catalog_path`` to find the nearest ``.git`` directory.

    Matches the previous CLI's behaviour. If no ``.git`` is found, we
    fail loudly: deployment without a host git repo cannot work and
    silently falling back to ``cwd`` would be a footgun in CI.
    """
    current = Path(catalog_path).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    raise click.ClickException(
        f"No git repository found at or above {catalog_path}; "
        "site-deploy needs a git repo so it can publish to gh-pages."
    )


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@click.command("serve")
@click.argument(
    "catalog_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    help="Port to serve on.",
)
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host to bind to (pass 0.0.0.0 to expose over an SSH tunnel).",
)
@click.option(
    "--site-name",
    default=None,
    help="Deprecated; retained for backwards compatibility (no-op).",
)
@click.option(
    "--site-dir",
    "site_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to the imas-standard-names site/ directory (Vite SPA source).",
)
@click.option(
    "--include-draft",
    is_flag=True,
    default=False,
    help="Include draft / deprecated / superseded entries (active-only by default).",
)
def serve_cmd(
    catalog_path: Path,
    port: int,
    host: str,
    site_name: str | None,
    site_dir: Path | None,
    include_draft: bool,
) -> None:
    """Serve the catalog SPA locally for preview.

    CATALOG_PATH: Path to directory containing standard name YAML files.

    Writes the catalog dataset to ``site/public/data.json`` then launches
    ``npm run dev``. Vite serves the SPA with hot-reload from ``site/``.
    """
    if site_name:
        click.echo("warning: --site-name is now a no-op", err=True)

    _ensure_node_toolchain()
    resolved_site_dir = _resolve_site_dir(site_dir)

    # Vite serves anything in ``public/`` at the site root, so writing
    # ``data.json`` here means the dev server sees it without any extra
    # plugin configuration.
    public = resolved_site_dir / "public"
    public.mkdir(exist_ok=True)
    n = write_site_dataset(
        catalog_path, public / "data.json", include_draft=include_draft
    )
    if n == 0:
        click.echo("Warning: No standard names found in catalog", err=True)
    click.echo(f"Generated dataset for {n} standard names")
    click.echo(f"Starting dev server at http://{host}:{port}/")
    click.echo("Press Ctrl+C to stop...")

    _run(
        ["npm", "run", "dev", "--", "--port", str(port), "--host", host],
        cwd=resolved_site_dir,
    )


@click.command("site-deploy")
@click.argument(
    "catalog_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--version",
    "doc_version",
    required=True,
    help="Version string for deployment (e.g. 'v1.0', 'main', 'pr-123').",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push the gh-pages branch to the remote after deployment.",
)
@click.option(
    "--set-default",
    is_flag=True,
    help="Mark this version as the default (alias 'latest').",
)
@click.option(
    "--site-name",
    default=None,
    help="Deprecated; retained for backwards compatibility (no-op).",
)
@click.option(
    "--site-url",
    default=None,
    help="Deprecated; retained for backwards compatibility (no-op).",
)
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote to push the gh-pages branch to.",
)
@click.option(
    "--branch",
    default="gh-pages",
    show_default=True,
    help="Deploy branch name.",
)
@click.option(
    "--site-dir",
    "site_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to the imas-standard-names site/ directory (Vite SPA source).",
)
@click.option(
    "--include-draft",
    is_flag=True,
    default=False,
    help="Include draft / deprecated / superseded entries (active-only by default).",
)
def deploy_cmd(
    catalog_path: Path,
    doc_version: str,
    push: bool,
    set_default: bool,
    site_name: str | None,
    site_url: str | None,
    remote: str,
    branch: str,
    site_dir: Path | None,
    include_draft: bool,
) -> None:
    """Build the SPA and deploy it to gh-pages/<version>/.

    CATALOG_PATH: Path to directory containing standard name YAML files.

    Backwards-compatible signature: ISNC's CI workflow calls this
    command verbatim. The Vite SPA is built from ``site/`` and copied
    under the deploy branch's ``<version>/`` directory. ``versions.json``
    is updated in mike-compatible format so any existing tooling that
    reads it continues to work.

    Typical CI workflow:

        standard-names site-deploy ./standard_names --version v1.0 --push --set-default
    """
    if site_name or site_url:
        click.echo(
            "warning: --site-name / --site-url are now no-ops",
            err=True,
        )

    resolved_site_dir = _resolve_site_dir(site_dir)
    repo_root = _find_git_root(catalog_path)

    with tempfile.TemporaryDirectory(prefix="sn-site-") as tmp:
        dist_dir = Path(tmp) / "dist"
        n = _build_site(
            catalog_path,
            dist_dir,
            resolved_site_dir,
            include_draft=include_draft,
        )
        if n == 0:
            click.echo("Warning: No standard names found in catalog", err=True)
        click.echo(f"Built SPA for {n} standard names")

        deploy_to_gh_pages(
            repo_root=repo_root,
            src_dir=dist_dir,
            version=doc_version,
            alias_latest=set_default,
            push=push,
            remote=remote,
            branch=branch,
        )

    click.echo(f"✓ Deployed version '{doc_version}'")
    if set_default:
        click.echo("✓ Set as default version (latest)")
    if push:
        click.echo(f"✓ Pushed to {remote}/{branch}")
