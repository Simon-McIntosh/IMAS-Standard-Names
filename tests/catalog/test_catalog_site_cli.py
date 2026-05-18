"""Tests for the rewritten ``catalog_site`` CLI commands.

These tests pin the CLI contract that ISNC's CI workflow depends on:

* ``standard-names site-deploy`` and ``standard-names serve`` both
  accept the same options they accepted in the MkDocs era.
* ``--site-name`` and ``--site-url`` are deprecated no-ops; passing
  them emits a warning rather than raising.
* Missing Node toolchain or missing ``site/`` scaffold produces a clear
  error before any expensive work.

The tests deliberately avoid invoking ``npm`` for real — they
exercise the validation and routing layers via monkeypatched
``shutil.which`` and either fake module attributes or fake catalog
fixtures. The npm path itself is well-trodden by Vite's own test
suite and by manual smoke tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from imas_standard_names.cli import catalog_site
from imas_standard_names.cli.catalog_site import deploy_cmd, serve_cmd

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def empty_catalog_dir(tmp_path: Path) -> Path:
    """A minimal-but-valid catalog directory layout.

    The dataset builder doesn't strictly require any YAML files to be
    present — an empty directory yields an empty dataset. That's fine
    for CLI signature tests.
    """
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    # Add one trivial domain so the dataset builder has something to
    # walk; we don't assert on its contents in these tests.
    domain = catalog / "general"
    domain.mkdir()
    entry = {
        "name": "test_quantity",
        "kind": "base",
        "description": "Test description.",
        "unit": "1",
        "physics_domain": "general",
        "status": "draft",
    }
    (domain / "test_quantity.yml").write_text(yaml.safe_dump(entry), encoding="utf-8")
    return catalog


# ---------------------------------------------------------------------------
# Signature / contract tests
# ---------------------------------------------------------------------------


def test_site_deploy_help_signature_unchanged(runner: CliRunner) -> None:
    """ISNC's CI calls ``standard-names site-deploy`` with this exact set
    of options. Removing any of them is a breaking change."""
    result = runner.invoke(deploy_cmd, ["--help"])
    assert result.exit_code == 0, result.output
    help_text = result.output
    for option in (
        "--version",
        "--push",
        "--set-default",
        "--site-name",
        "--site-url",
    ):
        assert option in help_text, f"option {option} disappeared from --help"


def test_serve_help_signature_unchanged(runner: CliRunner) -> None:
    """``serve`` keeps its existing options."""
    result = runner.invoke(serve_cmd, ["--help"])
    assert result.exit_code == 0, result.output
    for option in ("--port", "--host", "--site-name"):
        assert option in result.output, f"option {option} disappeared from --help"


# ---------------------------------------------------------------------------
# Deprecation warning tests
# ---------------------------------------------------------------------------


def test_site_deploy_emits_deprecation_for_site_name(
    runner: CliRunner,
    empty_catalog_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--site-name`` is now a no-op but must still be accepted; passing
    it emits a deprecation warning to stderr."""
    # Short-circuit before any real build / git work.
    monkeypatch.setattr(catalog_site, "_find_git_root", lambda _p: empty_catalog_dir)
    monkeypatch.setattr(
        catalog_site,
        "_build_site",
        lambda _c, _d: (_ for _ in ()).throw(SystemExit("stop here")),
    )
    result = runner.invoke(
        deploy_cmd,
        [
            str(empty_catalog_dir),
            "--version",
            "v0.1.0",
            "--site-name",
            "Some Name",
        ],
    )
    # ClickException would surface as exit code 1; SystemExit propagates differently.
    assert "no-op" in result.stderr


def test_site_deploy_emits_deprecation_for_site_url(
    runner: CliRunner,
    empty_catalog_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(catalog_site, "_find_git_root", lambda _p: empty_catalog_dir)
    monkeypatch.setattr(
        catalog_site,
        "_build_site",
        lambda _c, _d: (_ for _ in ()).throw(SystemExit("stop here")),
    )
    result = runner.invoke(
        deploy_cmd,
        [
            str(empty_catalog_dir),
            "--version",
            "v0.1.0",
            "--site-url",
            "https://example.com",
        ],
    )
    assert "no-op" in result.stderr


def test_serve_emits_deprecation_for_site_name(
    runner: CliRunner,
    empty_catalog_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force the Node check to pass so we get past the toolchain guard,
    # then short-circuit the dataset write to avoid touching site/public.
    monkeypatch.setattr(catalog_site, "_check_node_available", lambda: True)
    monkeypatch.setattr(catalog_site, "_resolve_site_dir", lambda _d: empty_catalog_dir)
    monkeypatch.setattr(
        catalog_site,
        "write_site_dataset",
        lambda _c, _o: (_ for _ in ()).throw(SystemExit("stop here")),
    )
    result = runner.invoke(
        serve_cmd,
        [
            str(empty_catalog_dir),
            "--site-name",
            "ignored",
        ],
    )
    assert "no-op" in result.stderr


# ---------------------------------------------------------------------------
# Toolchain / scaffold validation
# ---------------------------------------------------------------------------


def test_site_deploy_fails_clearly_without_node(
    runner: CliRunner,
    empty_catalog_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Node is missing, the CLI must emit a friendly message rather
    than a raw OSError from subprocess."""
    monkeypatch.setattr(catalog_site, "_check_node_available", lambda: False)
    monkeypatch.setattr(catalog_site, "_find_git_root", lambda _p: empty_catalog_dir)
    result = runner.invoke(
        deploy_cmd,
        [str(empty_catalog_dir), "--version", "v0.1.0"],
    )
    assert result.exit_code != 0
    assert "Node.js + npm required" in result.output


def test_serve_fails_clearly_without_node(
    runner: CliRunner,
    empty_catalog_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(catalog_site, "_check_node_available", lambda: False)
    result = runner.invoke(serve_cmd, [str(empty_catalog_dir)])
    assert result.exit_code != 0
    assert "Node.js + npm required" in result.output


def test_site_deploy_fails_clearly_without_site_dir(
    runner: CliRunner,
    empty_catalog_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``site/`` is missing or has no ``package.json``, fail loudly."""
    fake_site = tmp_path / "no-such-site"
    monkeypatch.setattr(catalog_site, "_check_node_available", lambda: True)
    monkeypatch.setattr(catalog_site, "_DEFAULT_SITE_DIR", fake_site)
    monkeypatch.setattr(catalog_site, "_find_git_root", lambda _p: empty_catalog_dir)
    result = runner.invoke(
        deploy_cmd,
        [str(empty_catalog_dir), "--version", "v0.1.0"],
    )
    assert result.exit_code != 0
    assert "site/ scaffold missing" in result.output


# ---------------------------------------------------------------------------
# Git-root resolution
# ---------------------------------------------------------------------------


def test_find_git_root_walks_upward(tmp_path: Path) -> None:
    """``_find_git_root`` matches the previous CLI's behaviour: walk up
    from the catalog path to the nearest ``.git`` directory."""
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True)

    found = catalog_site._find_git_root(deep)
    assert found == root.resolve()


def test_find_git_root_raises_when_no_repo(tmp_path: Path) -> None:
    """When no git repo is found, ``_find_git_root`` raises a
    ``ClickException`` rather than silently falling back to ``cwd``."""
    plain = tmp_path / "no-repo"
    plain.mkdir()
    with pytest.raises(Exception) as excinfo:
        catalog_site._find_git_root(plain)
    assert "No git repository found" in str(excinfo.value)
