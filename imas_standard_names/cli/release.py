"""Release command: semantic versioning and tag-based publishing.

Two-state release workflow (Stable ↔ RC mode):
  --bump major|minor|patch   Start a new RC series (or direct release with --final)
  --final                    Finalize current RC to stable release
  release status             Show current state and available commands

Pipeline steps:
1. Pre-flight checks (on main, clean tree, synced with upstream)
2. Compute next version from state machine
3. Create and push git tag to upstream (triggers CI → PyPI publish)
"""

import json
import re
import shutil
import subprocess

import click

# ============================================================================
# Version computation
# ============================================================================

_SEMVER_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?$")


def _run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def _get_latest_tag() -> str | None:
    """Get the most recent semver tag from git."""
    result = _run_git("tag", "--sort=-v:refname")
    if result.returncode != 0:
        return None
    for line in result.stdout.strip().splitlines():
        tag = line.strip()
        if re.match(r"^v\d+\.\d+\.\d+", tag):
            return tag
    return None


def _get_latest_stable_tag() -> str | None:
    """Get the most recent stable (non-RC) semver tag from git."""
    result = _run_git("tag", "--sort=-v:refname")
    if result.returncode != 0:
        return None
    for line in result.stdout.strip().splitlines():
        tag = line.strip()
        if re.match(r"^v\d+\.\d+\.\d+$", tag):
            return tag
    return None


def _parse_version(tag: str) -> tuple[int, int, int, int | None]:
    """Parse a version tag into (major, minor, patch, rc_number|None).

    Handles: v0.7.0, v0.7.0rc1
    """
    tag = tag.lstrip("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?$", tag)
    if not match:
        raise click.ClickException(f"Cannot parse version: {tag}")
    major, minor, patch = int(match[1]), int(match[2]), int(match[3])
    rc = int(match[4]) if match[4] else None
    return major, minor, patch, rc


def _format_tag(major: int, minor: int, patch: int, rc: int | None) -> str:
    """Format version components as a git tag (v0.7.0 or v0.7.0rc1)."""
    base = f"v{major}.{minor}.{patch}"
    return f"{base}rc{rc}" if rc else base


def _tag_exists(tag: str) -> bool:
    result = _run_git("tag", "-l", tag)
    return bool(result.stdout.strip())


def _commits_since_tag(tag: str) -> int:
    result = _run_git("rev-list", f"{tag}..HEAD", "--count")
    return int(result.stdout.strip()) if result.returncode == 0 else 0


# ============================================================================
# State detection
# ============================================================================


def _detect_state() -> dict:
    """Detect current release state from latest git tag."""
    tag = _get_latest_tag()
    if tag is None:
        return {
            "state": None,
            "tag": None,
            "major": 0,
            "minor": 0,
            "patch": 0,
            "rc": None,
        }
    major, minor, patch, rc = _parse_version(tag)
    state = "rc" if rc is not None else "stable"
    return {
        "state": state,
        "tag": tag,
        "major": major,
        "minor": minor,
        "patch": patch,
        "rc": rc,
    }


def _apply_bump(major: int, minor: int, patch: int, bump: str) -> tuple[int, int, int]:
    if bump == "major":
        return major + 1, 0, 0
    if bump == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def compute_next_version(bump: str | None, *, final: bool = False) -> tuple[str, str]:
    """Compute next version tag from current state.

    Returns (git_tag, version_string) e.g. ("v0.7.0rc1", "0.7.0rc1").
    """
    info = _detect_state()
    state = info["state"]
    major, minor, patch = info["major"], info["minor"], info["patch"]

    if state is None:
        if bump:
            m, n, p = _apply_bump(0, 0, 0, bump)
        else:
            m, n, p = 0, 1, 0
        rc = None if final else 1
        tag = _format_tag(m, n, p, rc)
        return tag, tag.lstrip("v")

    if state == "stable":
        if not bump:
            raise click.ClickException(
                f"On stable release {info['tag']}. "
                "Specify --bump (major|minor|patch) to start a new release."
            )
        m, n, p = _apply_bump(major, minor, patch, bump)
        rc = None if final else 1
        tag = _format_tag(m, n, p, rc)
        return tag, tag.lstrip("v")

    # RC mode
    if bump:
        stable = _get_latest_stable_tag()
        if stable:
            s_maj, s_min, s_pat, _ = _parse_version(stable)
        else:
            s_maj, s_min, s_pat = major, minor, patch
        m, n, p = _apply_bump(s_maj, s_min, s_pat, bump)
        rc = None if final else 1
        tag = _format_tag(m, n, p, rc)
        return tag, tag.lstrip("v")

    if final:
        tag = _format_tag(major, minor, patch, None)
        return tag, tag.lstrip("v")

    # Increment RC
    next_rc = info["rc"] + 1
    tag = _format_tag(major, minor, patch, next_rc)
    return tag, tag.lstrip("v")


# ============================================================================
# Pre-flight checks
# ============================================================================


def _check_on_main() -> None:
    result = _run_git("branch", "--show-current")
    branch = result.stdout.strip()
    if branch != "main":
        raise click.ClickException(
            f"Not on main branch (current: {branch}). Switch first: git checkout main"
        )
    click.echo("  ✓ On main branch")


def _check_clean_tree(dry_run: bool) -> None:
    result = _run_git("status", "--porcelain")
    if result.stdout.strip():
        msg = "Working tree has uncommitted changes. Commit or stash first."
        if dry_run:
            click.echo(f"  ⚠ {msg}", err=True)
        else:
            raise click.ClickException(msg)
    else:
        click.echo("  ✓ Working tree is clean")


def _check_synced(remote: str, dry_run: bool) -> None:
    _run_git("fetch", remote, "main")
    result = _run_git("rev-list", "--left-right", "--count", f"main...{remote}/main")
    if result.returncode != 0:
        click.echo(f"  ⚠ Could not check sync with {remote}/main", err=True)
        return

    parts = result.stdout.strip().split()
    if len(parts) != 2:
        return

    ahead, behind = int(parts[0]), int(parts[1])
    if behind > 0:
        msg = (
            f"Local is {behind} commits behind {remote}/main. "
            f"Pull first: git pull {remote} main"
        )
        if dry_run:
            click.echo(f"  ⚠ {msg}", err=True)
        else:
            raise click.ClickException(msg)
    if ahead > 0:
        msg = (
            f"Local is {ahead} commits ahead of {remote}/main. "
            f"Push first: git push {remote} main"
        )
        if dry_run:
            click.echo(f"  ⚠ {msg}", err=True)
        else:
            raise click.ClickException(msg)
    if ahead == 0 and behind == 0:
        click.echo(f"  ✓ Synced with {remote}/main")


def _check_ci_passed(remote: str, dry_run: bool) -> None:
    """Verify CI checks passed for HEAD on the target remote."""
    if not shutil.which("gh"):
        click.echo("  ⚠ gh CLI not found — skipping CI status check", err=True)
        return

    url_result = _run_git("remote", "get-url", remote)
    if url_result.returncode != 0:
        click.echo("  ⚠ Could not read remote URL — skipping CI check", err=True)
        return

    url = url_result.stdout.strip()
    # Extract owner/repo from SSH or HTTPS URL
    if url.startswith("git@"):
        nwo = url.split(":")[-1].replace(".git", "")
    else:
        nwo = "/".join(url.replace(".git", "").split("/")[-2:])

    sha = _run_git("rev-parse", "HEAD").stdout.strip()

    api_result = subprocess.run(
        ["gh", "api", f"repos/{nwo}/commits/{sha}/check-runs"],
        capture_output=True,
        text=True,
    )
    if api_result.returncode != 0:
        click.echo("  ⚠ Could not query CI status — skipping CI check", err=True)
        return

    try:
        data = json.loads(api_result.stdout)
    except json.JSONDecodeError:
        click.echo("  ⚠ Could not parse CI response — skipping CI check", err=True)
        return

    check_runs = data.get("check_runs", [])
    if not check_runs:
        click.echo(f"  ⚠ No CI check runs found for {sha[:8]}", err=True)
        return

    pending = [cr["name"] for cr in check_runs if cr.get("status") != "completed"]
    failed = [
        cr["name"]
        for cr in check_runs
        if cr.get("status") == "completed"
        and cr.get("conclusion") not in ("success", "skipped", "neutral")
    ]

    if not pending and not failed:
        click.echo(f"  ✓ CI checks passed for {sha[:8]}")
        return

    details = []
    if failed:
        names = ", ".join(failed[:3])
        if len(failed) > 3:
            names += f" (+{len(failed) - 3} more)"
        details.append(f"failed: {names}")
    if pending:
        names = ", ".join(pending[:3])
        if len(pending) > 3:
            names += f" (+{len(pending) - 3} more)"
        details.append(f"pending: {names}")

    msg = (
        f"CI checks not passed for {sha[:8]}: "
        f"{'; '.join(details)}. "
        "Wait for CI before releasing."
    )
    if dry_run:
        click.echo(f"  ⚠ {msg}", err=True)
    else:
        raise click.ClickException(msg)


# ============================================================================
# Status display
# ============================================================================


def _show_release_status() -> None:
    """Show current release state and available commands."""
    info = _detect_state()
    cmd = "standard-names release"

    if info["state"] is None:
        click.echo("Release state: No tags found")
        click.echo(f"  {cmd} --bump minor -m 'Initial release'")
        return

    tag = info["tag"]
    major, minor, patch = info["major"], info["minor"], info["patch"]
    commits = _commits_since_tag(tag)
    commits_str = f" ({commits} commits since tag)" if commits else ""

    if info["state"] == "rc":
        target = _format_tag(major, minor, patch, None)
        next_rc = info["rc"] + 1
        stable_tag = _get_latest_stable_tag()
        s_maj, s_min, s_pat = (
            _parse_version(stable_tag)[:3] if stable_tag else (major, minor, patch)
        )

        click.echo("Release state: RC mode")
        click.echo(f"  Current:  {tag}{commits_str}")
        click.echo(f"  Target:   {target}")
        if stable_tag:
            click.echo(f"  Stable:   {stable_tag}")
        click.echo()
        click.echo("Available commands:")
        click.echo(
            f"  {cmd} -m '...'               "
            f"→ {_format_tag(major, minor, patch, next_rc)}  (next RC)"
        )
        click.echo(f"  {cmd} --final -m '...'       → {target}  (finalize)")
        click.echo(
            f"  {cmd} --bump patch -m '...'  "
            f"→ {_format_tag(s_maj, s_min, s_pat + 1, 1)}  (abandon RC)"
        )
    else:
        click.echo("Release state: Stable")
        click.echo(f"  Current:  {tag}{commits_str}")
        click.echo()
        click.echo("Available commands:")
        click.echo(
            f"  {cmd} --bump patch -m '...'  "
            f"→ {_format_tag(major, minor, patch + 1, 1)}"
        )
        click.echo(
            f"  {cmd} --bump minor -m '...'  → {_format_tag(major, minor + 1, 0, 1)}"
        )
        click.echo(
            f"  {cmd} --bump major -m '...'  → {_format_tag(major + 1, 0, 0, 1)}"
        )
        click.echo(
            f"  {cmd} --bump patch --final -m '...'  "
            f"→ {_format_tag(major, minor, patch + 1, None)}  (skip RC)"
        )


# ============================================================================
# Click command
# ============================================================================

REMOTE = "upstream"


@click.command("release")
@click.argument(
    "action",
    required=False,
    default=None,
    type=click.Choice(["status"]),
)
@click.option(
    "--bump",
    type=click.Choice(["major", "minor", "patch"]),
    default=None,
    help="Version bump type. Starts a new RC series (or direct release with --final).",
)
@click.option(
    "-m",
    "--message",
    default=None,
    help="Release message (used for git tag annotation).",
)
@click.option(
    "--final",
    "final",
    is_flag=True,
    help="Finalize: promote current RC to stable, or skip RC with --bump.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making changes.",
)
def release_cmd(
    action: str | None,
    bump: str | None,
    message: str | None,
    final: bool,
    dry_run: bool,
) -> None:
    """Semantic version release with pre-flight safety checks.

    Detects current state (Stable or RC mode) from the latest git tag and
    computes the next version automatically. Tags are always pushed to
    upstream (iterorganization) to trigger the PyPI publish workflow.

    \b
    Examples:
        # Show current state and available commands
        standard-names release status

        # Start RC series (v0.6.0 → v0.7.0rc1)
        standard-names release --bump minor -m 'Add release CLI'

        # Increment RC (v0.7.0rc1 → v0.7.0rc2)
        standard-names release -m 'Fix CI issues'

        # Finalize RC (v0.7.0rc2 → v0.7.0)
        standard-names release --final -m 'Production release'

        # Direct release, skip RC (v0.6.0 → v0.6.1)
        standard-names release --bump patch --final -m 'Hotfix'

        # Dry run (validate without tagging)
        standard-names release --bump minor --dry-run -m 'Test'
    """
    if action == "status":
        _show_release_status()
        return

    if message is None:
        raise click.ClickException(
            "Missing required option '-m' / '--message'. "
            "Example: standard-names release --bump minor -m 'description'"
        )

    # --- Pre-flight checks ---
    click.echo("Pre-flight checks:")
    _check_on_main()
    _check_clean_tree(dry_run)
    _check_synced(REMOTE, dry_run)
    _check_ci_passed(REMOTE, dry_run)

    # --- Compute version ---
    info = _detect_state()

    if not bump and not final:
        if info["state"] == "rc":
            git_tag, version = compute_next_version(None)
        else:
            raise click.ClickException(
                f"On stable release {info['tag'] or '(none)'}. "
                "Specify --bump (major|minor|patch) to start a new release."
            )
    else:
        git_tag, version = compute_next_version(bump, final=final)

    if _tag_exists(git_tag):
        raise click.ClickException(f"Tag {git_tag} already exists.")

    # Warn when abandoning an active RC series
    if bump and info["state"] == "rc":
        stable_tag = _get_latest_stable_tag()
        base_ref = stable_tag or "(none)"
        if final:
            click.echo(
                f"  ⚠ Abandoning {info['tag']} "
                f"— releasing {git_tag} directly (bumped from {base_ref})",
                err=True,
            )
        else:
            click.echo(
                f"  ⚠ Abandoning {info['tag']} "
                f"— new RC series at {git_tag} (bumped from {base_ref})",
                err=True,
            )

    # --- Create and push tag ---
    click.echo()
    click.echo(f"Version: {version}")
    click.echo(f"Tag:     {git_tag}")
    click.echo(f"Remote:  {REMOTE}")

    if dry_run:
        click.echo()
        click.echo("Dry run — no changes made.")
        return

    click.echo()
    result = _run_git("tag", "-a", git_tag, "-m", message)
    if result.returncode != 0:
        raise click.ClickException(f"Failed to create tag: {result.stderr}")
    click.echo(f"  ✓ Created tag {git_tag}")

    result = _run_git("push", REMOTE, git_tag)
    if result.returncode != 0:
        # Clean up the local tag on push failure
        _run_git("tag", "-d", git_tag)
        raise click.ClickException(f"Failed to push tag to {REMOTE}: {result.stderr}")
    click.echo(f"  ✓ Pushed {git_tag} to {REMOTE}")
    click.echo()
    click.echo(
        "Release pipeline triggered. Monitor at: "
        "https://github.com/iterorganization/IMAS-Standard-Names/actions"
    )
