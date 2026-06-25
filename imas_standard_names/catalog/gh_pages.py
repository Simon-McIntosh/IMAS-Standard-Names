"""Versioned gh-pages deployer (mike-compatible ``versions.json``).

This module replaces our previous use of `mike <https://github.com/jimporter/mike>`_
for publishing the Standard Names catalog. ``mike`` is tightly coupled to
``mkdocs``: it expects an ``mkdocs.yml`` and shells out to ``mkdocs build``.
Our catalog site is now a Vite-built static SPA, so we only need ``mike``'s
gh-pages bookkeeping. This module implements just that — versioned subdirs,
a ``versions.json`` selector file in mike's shape, optional ``latest``
alias with redirects, and an idempotent worktree-based commit/push.

Layout produced on the ``gh-pages`` branch::

    /
    ├── index.html              (redirect to ``latest/``)
    ├── versions.json           (mike-compatible)
    ├── latest/
    │   └── index.html          (redirect to the version aliased ``latest``)
    ├── v1.0.0/
    │   ├── index.html          (SPA entry)
    │   ├── assets/...
    │   └── data.json           (catalog dataset emitted by the builder)
    └── v0.9.0/
        └── ...

``versions.json`` shape (matches ``mike``)::

    [
      {"version": "v1.0.0", "title": "v1.0.0", "aliases": ["latest"]},
      {"version": "v0.9.0", "title": "v0.9.0", "aliases": []}
    ]

The module is deliberately self-contained: pure ``subprocess`` git calls
and stdlib filesystem operations. No third-party dependencies. Tests
exercise it against a real ephemeral git repo in ``tmp_path``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "VersionEntry",
    "deploy",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VersionEntry:
    """One entry in ``versions.json``.

    Matches the shape mike emits so its version selector (and any tooling
    that parses ``versions.json``) keeps working.
    """

    version: str
    title: str
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "title": self.title,
            "aliases": list(self.aliases),
        }

    @classmethod
    def from_dict(cls, data: dict) -> VersionEntry:
        return cls(
            version=str(data["version"]),
            title=str(data.get("title", data["version"])),
            aliases=tuple(str(a) for a in data.get("aliases", [])),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def deploy(
    *,
    repo_root: Path,
    src_dir: Path,
    version: str,
    title: str | None = None,
    alias_latest: bool = False,
    push: bool = False,
    remote: str = "origin",
    branch: str = "gh-pages",
    message: str | None = None,
) -> None:
    """Deploy ``src_dir`` to ``<branch>/<version>/`` in ``repo_root``.

    Updates ``versions.json`` at the branch root in mike-compatible
    format. If ``alias_latest`` is true, also writes ``latest/`` and
    ``index.html`` redirects and ensures only this version carries the
    ``latest`` alias. Idempotent: redeploying the same version replaces
    the version directory without duplicating ``versions.json`` entries.

    Args:
        repo_root: Working copy that hosts the gh-pages branch. Must be
            a git repository.
        src_dir: Directory containing the static site to deploy. Must
            contain ``index.html``.
        version: Version label, e.g. ``v1.2.3``. Used as the subdirectory
            name on the deploy branch.
        title: Human-readable label for the version selector. Defaults
            to ``version``.
        alias_latest: When true, mark this version with the ``latest``
            alias and write the ``/latest/`` + ``/`` redirect pages.
            Any other version carrying ``latest`` has the alias removed.
        push: When true, ``git push <remote> <branch>`` after the commit.
        remote: Remote name to push to.
        branch: Deploy branch.
        message: Commit message override. Defaults to ``Deploy <version>``.

    Raises:
        FileNotFoundError: If ``src_dir`` is missing or has no
            ``index.html``.
        NotADirectoryError: If ``repo_root`` is not a git working copy.
        subprocess.CalledProcessError: If a git command fails.
    """
    repo_root = Path(repo_root).resolve()
    src_dir = Path(src_dir).resolve()

    if not (repo_root / ".git").exists():
        raise NotADirectoryError(f"{repo_root} is not a git repository")
    if not src_dir.is_dir():
        raise FileNotFoundError(f"src_dir {src_dir} does not exist")
    if not (src_dir / "index.html").exists():
        raise FileNotFoundError(
            f"{src_dir}/index.html missing — SPA build is incomplete"
        )

    _ensure_branch_exists(repo_root, branch, remote=remote)

    worktree_parent = Path(tempfile.mkdtemp(prefix="sn-gh-pages-"))
    worktree = worktree_parent / "wt"
    try:
        _run_git(["worktree", "add", "--force", str(worktree), branch], cwd=repo_root)

        # Replace the version directory wholesale.
        version_dir = worktree / version
        if version_dir.exists():
            shutil.rmtree(version_dir)
        shutil.copytree(src_dir, version_dir)

        # Update versions.json — add or replace the entry.
        versions = _load_versions(worktree)
        existing_aliases = _aliases_for(versions, version)
        if alias_latest:
            versions = _strip_alias_from_others(versions, "latest", current=version)
            new_aliases = tuple(sorted(set(existing_aliases) | {"latest"}))
        else:
            new_aliases = existing_aliases
        versions = _upsert_version(
            versions,
            VersionEntry(version=version, title=title or version, aliases=new_aliases),
        )
        _save_versions(worktree, versions)

        # Write redirects when this is (or becomes) the latest.
        if alias_latest:
            # A legacy mike-based deploy may have left ``latest`` as a SYMLINK
            # to a version directory. GitHub Pages does not serve symlinks (it
            # would show stale/no content), and writing ``latest/index.html``
            # through the symlink would corrupt the target version's index.
            # Replace any non-directory ``latest`` with a real redirect dir.
            latest_path = worktree / "latest"
            if latest_path.is_symlink() or (
                latest_path.exists() and not latest_path.is_dir()
            ):
                latest_path.unlink()
            _write_redirect(latest_path / "index.html", f"../{version}/")
            _write_redirect(worktree / "index.html", "latest/")

        # Stage changes: only the files we touched.
        paths_to_stage: list[str] = [
            str(version_dir.relative_to(worktree)),
            "versions.json",
        ]
        if alias_latest:
            paths_to_stage.extend(["latest", "index.html"])
        _run_git(["add", "--", *paths_to_stage], cwd=worktree)

        commit_message = message or f"Deploy {version}"
        # Allow an empty commit so re-deploys with no file changes still
        # produce a commit (matches mike's behavior; useful for CI logs).
        _run_git(
            ["commit", "--allow-empty", "-m", commit_message],
            cwd=worktree,
        )

        if push:
            # Force-push is safe for the gh-pages deploy branch — it's a
            # build artifact, not collaborative history. This handles the
            # common CI scenario where a shallow fetch + concurrent deploy
            # leaves the local branch behind the remote.
            _run_git(["push", "--force", remote, branch], cwd=worktree)
    finally:
        # Best-effort cleanup. ``git worktree remove`` is the canonical
        # path; fall back to a plain rmtree if git's remove fails.
        try:
            _run_git(
                ["worktree", "remove", "--force", str(worktree)],
                cwd=repo_root,
                check=False,
            )
        except Exception:
            pass
        shutil.rmtree(worktree_parent, ignore_errors=True)


# ---------------------------------------------------------------------------
# Branch / worktree helpers
# ---------------------------------------------------------------------------


def _ensure_branch_exists(
    repo_root: Path, branch: str, *, remote: str = "origin"
) -> None:
    """Ensure a local ``branch`` ref exists, preserving any remote history.

    Order of operations:

    1. If ``refs/heads/<branch>`` already exists locally, nothing to do.
    2. Otherwise, if ``refs/remotes/<remote>/<branch>`` exists (the CI
       case: the branch was fetched but never checked out), create a
       local branch pointing at the remote ref. This is what stops a
       fresh ``deploy()`` in CI from clobbering published history.
    3. Otherwise the branch genuinely does not exist anywhere — seed an
       empty orphan in a temporary worktree.

    Without step 2, every CI run on a shallow / fresh clone would land
    in the orphan path, force-push, and wipe every prior version on the
    remote.
    """
    if _branch_exists(repo_root, branch):
        return

    if _remote_branch_exists(repo_root, remote, branch):
        # Materialise the local ref from the remote tracking ref. We do
        # not check it out — ``deploy()`` will create a worktree pointed
        # at this ref in the next step.
        _run_git(
            ["branch", branch, f"refs/remotes/{remote}/{branch}"],
            cwd=repo_root,
        )
        return

    seed_parent = Path(tempfile.mkdtemp(prefix="sn-gh-pages-seed-"))
    seed = seed_parent / "wt"
    try:
        # Create a detached worktree, then build the orphan history there.
        _run_git(["worktree", "add", "--detach", str(seed)], cwd=repo_root)
        _run_git(["checkout", "--orphan", branch], cwd=seed)
        # Drop any inherited index entries from the orphan checkout.
        _run_git(["rm", "-rf", "--quiet", "--ignore-unmatch", "."], cwd=seed)
        # Add a tiny .gitignore so the branch root is non-empty.
        (seed / ".gitignore").write_text("\n", encoding="utf-8")
        _run_git(["add", ".gitignore"], cwd=seed)
        _run_git(
            ["commit", "--allow-empty", "-m", f"Initialize {branch} branch"],
            cwd=seed,
        )
    finally:
        try:
            _run_git(
                ["worktree", "remove", "--force", str(seed)],
                cwd=repo_root,
                check=False,
            )
        except Exception:
            pass
        shutil.rmtree(seed_parent, ignore_errors=True)


def _branch_exists(repo_root: Path, branch: str) -> bool:
    """Return True if ``branch`` exists locally."""
    proc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo_root,
        check=False,
    )
    return proc.returncode == 0


def _remote_branch_exists(repo_root: Path, remote: str, branch: str) -> bool:
    """Return True if ``refs/remotes/<remote>/<branch>`` exists locally.

    A True result means we have a fetched copy of the remote branch
    (e.g. after a CI ``git fetch <remote> <branch>`` step) even though
    no local working branch has been created from it yet.
    """
    proc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}"],
        cwd=repo_root,
        check=False,
    )
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# versions.json helpers
# ---------------------------------------------------------------------------


def _load_versions(worktree: Path) -> list[VersionEntry]:
    """Read ``versions.json``; return ``[]`` if missing or empty."""
    path = worktree / "versions.json"
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    return [VersionEntry.from_dict(d) for d in data]


def _save_versions(worktree: Path, versions: Sequence[VersionEntry]) -> None:
    """Serialise ``versions`` to ``versions.json``.

    Sort order: ``latest`` first (so it sorts to the top of any version
    selector dropdown), then entries in descending semver-ish order; any
    entry that does not parse as semver falls back to a string-descending
    sort and lands after the parseable ones. This mirrors mike's
    default behaviour closely enough for the selector UI.
    """
    sorted_versions = sorted(versions, key=_version_sort_key, reverse=True)
    serialised = [v.to_dict() for v in sorted_versions]
    (worktree / "versions.json").write_text(
        json.dumps(serialised, indent=2) + "\n",
        encoding="utf-8",
    )


_SEMVER_RE = re.compile(
    r"""^
    v?
    (?P<major>\d+)
    \.
    (?P<minor>\d+)
    (?:\.(?P<patch>\d+))?
    (?P<pre>[-+].*)?
    $""",
    re.VERBOSE,
)


def _version_sort_key(entry: VersionEntry) -> tuple:
    """Stable sort key that puts ``latest`` on top and orders semver desc.

    Non-semver versions sort by their string after the semver block, so
    branch-style labels (``main``, ``pr-123``) still land predictably.
    """
    has_latest = "latest" in entry.aliases
    match = _SEMVER_RE.match(entry.version)
    if match:
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch = int(match.group("patch") or 0)
        # An empty ``pre`` (final release) outranks any pre-release of
        # the same numeric tuple, so represent it as empty-string-greater
        # than any tagged pre suffix by giving final releases an empty
        # high-order sentinel.
        pre = match.group("pre") or ""
        # We want "no pre-release" to sort AFTER pre-releases of the
        # same numeric tuple — invert by treating empty as a large value.
        pre_key = (0 if pre == "" else 1, pre)
        return (1 if has_latest else 0, 1, major, minor, patch, pre_key)
    # Non-semver: still rank below semver entries, but stable string sort.
    return (1 if has_latest else 0, 0, 0, 0, 0, (0, entry.version))


def _aliases_for(versions: Iterable[VersionEntry], version: str) -> tuple[str, ...]:
    """Return the alias tuple currently recorded for ``version``."""
    for v in versions:
        if v.version == version:
            return v.aliases
    return ()


def _upsert_version(
    versions: Sequence[VersionEntry], entry: VersionEntry
) -> list[VersionEntry]:
    """Return a new list with ``entry`` replacing any existing same-version entry."""
    return [v for v in versions if v.version != entry.version] + [entry]


def _strip_alias_from_others(
    versions: Sequence[VersionEntry], alias: str, *, current: str
) -> list[VersionEntry]:
    """Remove ``alias`` from every entry that is not ``current``.

    Used to keep aliases like ``latest`` unique. The ``current`` version
    is left untouched here because the caller will add the alias to it
    in a subsequent ``_upsert_version`` step.
    """
    result: list[VersionEntry] = []
    for v in versions:
        if v.version == current:
            result.append(v)
            continue
        if alias in v.aliases:
            new_aliases = tuple(a for a in v.aliases if a != alias)
            result.append(VersionEntry(v.version, v.title, new_aliases))
        else:
            result.append(v)
    return result


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def _write_redirect(path: Path, target: str) -> None:
    """Write an HTML meta-refresh redirect to ``target`` at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    html = (
        "<!doctype html>\n"
        f'<meta http-equiv="refresh" content="0; url={target}">\n'
        f'<link rel="canonical" href="{target}">\n'
        f"<title>Redirecting to {target}…</title>\n"
    )
    path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# Git wrapper
# ---------------------------------------------------------------------------


def _run_git(
    args: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run ``git`` with ``args`` in ``cwd``. Captures output for diagnostics."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )
