"""Tests for the gh-pages versioned deployer.

Each test stands up a real ephemeral git repository in ``tmp_path``,
populates it with a minimal commit on ``main``, and exercises the
``deploy()`` entry point. Results are verified by reading the worktree
state directly — never by re-invoking ``deploy()`` to inspect itself.

These tests do not invoke ``git push`` against any real remote; the
``--push`` path is exercised against a bare repository configured as
the ``origin`` of the working repo.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from imas_standard_names.catalog.gh_pages import (
    VersionEntry,
    _strip_alias_from_others,
    _upsert_version,
    _version_sort_key,
    deploy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force a known committer identity so ``git commit`` succeeds in CI."""
    # Disable any chance of GPG signing on shared machines (we never opt in).
    monkeypatch.setenv("GIT_AUTHOR_NAME", "test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.invalid")
    # Remove environment-level git config overrides that may prevent
    # bare repositories from working (e.g. safe.bareRepository=explicit).
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    monkeypatch.delenv("GIT_CONFIG_KEY_0", raising=False)
    monkeypatch.delenv("GIT_CONFIG_VALUE_0", raising=False)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Initialise a git repo with a single empty commit on ``main``."""
    root = tmp_path / "repo"
    root.mkdir()
    _run(["git", "init", "-b", "main"], cwd=root)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=root)
    _run(["git", "config", "tag.gpgsign", "false"], cwd=root)
    (root / "README.md").write_text("# repo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=root)
    _run(["git", "commit", "-m", "init"], cwd=root)
    return root


@pytest.fixture
def site_v1(tmp_path: Path) -> Path:
    """Minimal Vite-style dist directory for the first deploy."""
    src = tmp_path / "site_v1"
    src.mkdir()
    (src / "index.html").write_text(
        "<!doctype html><title>v1</title>", encoding="utf-8"
    )
    (src / "data.json").write_text('{"version": "v1"}', encoding="utf-8")
    assets = src / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("// v1", encoding="utf-8")
    return src


@pytest.fixture
def site_v2(tmp_path: Path) -> Path:
    """Minimal Vite-style dist directory for the second deploy."""
    src = tmp_path / "site_v2"
    src.mkdir()
    (src / "index.html").write_text(
        "<!doctype html><title>v2</title>", encoding="utf-8"
    )
    (src / "data.json").write_text('{"version": "v2"}', encoding="utf-8")
    assets = src / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("// v2", encoding="utf-8")
    return src


@pytest.fixture
def gh_pages_files(repo: Path) -> Iterator[callable]:
    """Helper to materialize and inspect the gh-pages branch in a temp worktree."""
    worktrees: list[Path] = []

    def _checkout(tmp_path: Path = repo.parent) -> Path:
        wt = tmp_path / f"gh-pages-wt-{len(worktrees)}"
        _run(["git", "worktree", "add", "--force", str(wt), "gh-pages"], cwd=repo)
        worktrees.append(wt)
        return wt

    yield _checkout

    for wt in worktrees:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt)],
            cwd=repo,
            check=False,
            capture_output=True,
        )


# ---------------------------------------------------------------------------
# Pure-function tests (no git involved)
# ---------------------------------------------------------------------------


def test_version_entry_round_trip() -> None:
    entry = VersionEntry("v1.0.0", "v1.0.0", ("latest",))
    assert VersionEntry.from_dict(entry.to_dict()) == entry


def test_strip_alias_from_others_leaves_current_alone() -> None:
    versions = [
        VersionEntry("v1.0.0", "v1.0.0", ("latest",)),
        VersionEntry("v2.0.0", "v2.0.0", ("latest", "stable")),
    ]
    result = _strip_alias_from_others(versions, "latest", current="v2.0.0")
    assert result[0].aliases == ()
    assert result[1].aliases == ("latest", "stable")


def test_upsert_version_replaces_existing() -> None:
    versions = [VersionEntry("v1.0.0", "v1", ())]
    result = _upsert_version(versions, VersionEntry("v1.0.0", "v1 (rebuilt)", ()))
    assert len(result) == 1
    assert result[0].title == "v1 (rebuilt)"


def test_version_sort_key_prioritises_latest_alias() -> None:
    older = VersionEntry("v1.0.0", "v1.0.0", ("latest",))
    newer = VersionEntry("v2.0.0", "v2.0.0", ())
    # Sort descending by key -> v1.0.0 should come first because it carries 'latest'.
    items = sorted([newer, older], key=_version_sort_key, reverse=True)
    assert items[0].version == "v1.0.0"


def test_version_sort_key_semver_descending() -> None:
    items = [
        VersionEntry("v1.0.0", "v1.0.0", ()),
        VersionEntry("v2.0.0", "v2.0.0", ()),
        VersionEntry("v1.1.0", "v1.1.0", ()),
    ]
    items_sorted = sorted(items, key=_version_sort_key, reverse=True)
    assert [v.version for v in items_sorted] == ["v2.0.0", "v1.1.0", "v1.0.0"]


# ---------------------------------------------------------------------------
# Integration tests (real git, real worktrees)
# ---------------------------------------------------------------------------


def test_fresh_deploy_creates_branch_and_writes_files(
    repo: Path, site_v1: Path, gh_pages_files
) -> None:
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0")

    # gh-pages branch now exists.
    proc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", "refs/heads/gh-pages"],
        cwd=repo,
        check=False,
    )
    assert proc.returncode == 0, "gh-pages branch was not created"

    wt = gh_pages_files()
    assert (wt / "v0.1.0" / "index.html").exists()
    assert (wt / "v0.1.0" / "assets" / "app.js").exists()

    versions = json.loads((wt / "versions.json").read_text(encoding="utf-8"))
    assert isinstance(versions, list)
    assert len(versions) == 1
    assert versions[0]["version"] == "v0.1.0"
    assert versions[0]["title"] == "v0.1.0"
    assert versions[0]["aliases"] == []


def test_redeploy_replaces_version_dir(
    repo: Path, site_v1: Path, site_v2: Path, gh_pages_files
) -> None:
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0")
    deploy(repo_root=repo, src_dir=site_v2, version="v0.1.0")

    wt = gh_pages_files()
    content = (wt / "v0.1.0" / "index.html").read_text(encoding="utf-8")
    assert "v2" in content, "Redeploy did not replace version directory"

    versions = json.loads((wt / "versions.json").read_text(encoding="utf-8"))
    assert len(versions) == 1, "Redeploy duplicated versions.json entry"


def test_alias_latest_strips_from_others(
    repo: Path, site_v1: Path, site_v2: Path, gh_pages_files
) -> None:
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0", alias_latest=True)
    deploy(repo_root=repo, src_dir=site_v2, version="v0.2.0", alias_latest=True)

    wt = gh_pages_files()
    versions = json.loads((wt / "versions.json").read_text(encoding="utf-8"))

    by_version = {v["version"]: v for v in versions}
    assert "latest" not in by_version["v0.1.0"]["aliases"]
    assert "latest" in by_version["v0.2.0"]["aliases"]

    # Redirect under /latest/ points at v0.2.0
    latest_index = (wt / "latest" / "index.html").read_text(encoding="utf-8")
    assert "../v0.2.0/" in latest_index


def test_root_index_redirects_to_latest(
    repo: Path, site_v1: Path, gh_pages_files
) -> None:
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0", alias_latest=True)

    wt = gh_pages_files()
    root_index = (wt / "index.html").read_text(encoding="utf-8")
    assert "latest/" in root_index
    assert 'http-equiv="refresh"' in root_index


def test_versions_json_format_mike_compatible(
    repo: Path, site_v1: Path, gh_pages_files
) -> None:
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0", alias_latest=True)

    wt = gh_pages_files()
    data = json.loads((wt / "versions.json").read_text(encoding="utf-8"))
    # Must be a list[dict] with the documented keys.
    assert isinstance(data, list)
    for entry in data:
        assert set(entry.keys()) == {"version", "title", "aliases"}
        assert isinstance(entry["aliases"], list)


def test_push_skipped_when_flag_off(
    repo: Path, site_v1: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Capture every git call to ensure ``git push`` is never invoked.
    seen: list[list[str]] = []
    real_run = subprocess.run

    def _spy(args, *a, **kw):
        if isinstance(args, list) and args and args[0] == "git":
            seen.append(args)
        return real_run(args, *a, **kw)

    monkeypatch.setattr(subprocess, "run", _spy)
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0", push=False)
    assert not any("push" in args for args in seen), f"Unexpected push: {seen}"


def test_push_invoked_when_flag_on(repo: Path, site_v1: Path, tmp_path: Path) -> None:
    # Set up a bare repo as the remote so push can actually succeed.
    bare = tmp_path / "remote.git"
    _run(["git", "init", "--bare", str(bare)], cwd=tmp_path)
    _run(["git", "remote", "add", "origin", str(bare)], cwd=repo)

    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0", push=True)

    # The bare repo now has a gh-pages ref.
    proc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", "refs/heads/gh-pages"],
        cwd=bare,
        check=False,
    )
    assert proc.returncode == 0, "Push did not create gh-pages on remote"


def test_orphan_branch_initial_commit(repo: Path, site_v1: Path) -> None:
    """The gh-pages branch must be an orphan, not a child of main."""
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0")

    # Find the merge-base between main and gh-pages; orphan branches have none.
    proc = subprocess.run(
        ["git", "merge-base", "main", "gh-pages"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0, (
        f"gh-pages is not orphaned (merge-base returned: {proc.stdout.strip()})"
    )


def test_missing_src_index_raises(repo: Path, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="index.html"):
        deploy(repo_root=repo, src_dir=empty, version="v0.1.0")


def test_non_git_repo_root_raises(tmp_path: Path, site_v1: Path) -> None:
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    with pytest.raises(NotADirectoryError, match="not a git repository"):
        deploy(repo_root=plain, src_dir=site_v1, version="v0.1.0")


def test_custom_title_used_when_provided(
    repo: Path, site_v1: Path, gh_pages_files
) -> None:
    deploy(
        repo_root=repo,
        src_dir=site_v1,
        version="v0.1.0",
        title="Spring 2026 release",
    )
    wt = gh_pages_files()
    versions = json.loads((wt / "versions.json").read_text(encoding="utf-8"))
    assert versions[0]["title"] == "Spring 2026 release"


def test_commit_message_override(repo: Path, site_v1: Path) -> None:
    deploy(
        repo_root=repo,
        src_dir=site_v1,
        version="v0.1.0",
        message="Custom: ship v0.1.0",
    )
    log = subprocess.run(
        ["git", "log", "--oneline", "-1", "gh-pages"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Custom: ship v0.1.0" in log


def test_deploy_from_fresh_clone_preserves_remote_history(
    repo: Path, site_v1: Path, site_v2: Path, tmp_path: Path
) -> None:
    """A fresh CI-style clone must not clobber a populated gh-pages remote.

    Reproduces the production bug where each CI run created a brand new
    orphan ``gh-pages`` branch (because ``_branch_exists`` only looked
    at ``refs/heads/``) and force-pushed it over the remote, wiping
    every previously-published version.
    """
    # Set up a bare remote that already has a v0.1.0 deploy on gh-pages.
    bare = tmp_path / "remote.git"
    _run(["git", "init", "--bare", str(bare)], cwd=tmp_path)
    _run(["git", "remote", "add", "origin", str(bare)], cwd=repo)
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0", push=True)

    # Simulate a fresh CI clone: clone the bare repo into a new dir,
    # fetch gh-pages as a remote tracking ref only (no local branch).
    fresh = tmp_path / "fresh"
    _run(["git", "clone", str(bare), str(fresh)], cwd=tmp_path)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=fresh)
    _run(["git", "fetch", "origin", "gh-pages", "--depth=1"], cwd=fresh)
    # Confirm the precondition: no local gh-pages ref, only a remote one.
    local_check = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", "refs/heads/gh-pages"],
        cwd=fresh,
        check=False,
    )
    assert local_check.returncode != 0, "test precondition: no local gh-pages"

    # Deploy v0.2.0 from this fresh clone, then push.
    deploy(repo_root=fresh, src_dir=site_v2, version="v0.2.0", push=True)

    # Inspect the remote's gh-pages: BOTH versions must be present.
    inspect = tmp_path / "inspect"
    _run(["git", "clone", str(bare), str(inspect)], cwd=tmp_path)
    _run(["git", "checkout", "gh-pages"], cwd=inspect)
    versions = json.loads((inspect / "versions.json").read_text(encoding="utf-8"))
    versions_by_name = {v["version"] for v in versions}
    assert versions_by_name == {"v0.1.0", "v0.2.0"}, (
        f"Fresh-clone deploy wiped remote history: {versions_by_name}"
    )
    assert (inspect / "v0.1.0" / "index.html").exists()
    assert (inspect / "v0.2.0" / "index.html").exists()


def test_subsequent_deploys_versions_sorted_latest_first(
    repo: Path, site_v1: Path, site_v2: Path, gh_pages_files
) -> None:
    deploy(repo_root=repo, src_dir=site_v1, version="v0.1.0")
    deploy(repo_root=repo, src_dir=site_v2, version="v0.2.0", alias_latest=True)

    wt = gh_pages_files()
    versions = json.loads((wt / "versions.json").read_text(encoding="utf-8"))
    # The 'latest'-aliased version should be first.
    assert versions[0]["version"] == "v0.2.0"
    assert "latest" in versions[0]["aliases"]
