"""Tests for the release CLI state machine.

Uses a real local git repository in tmp_path — no network, no PyPI.
All git operations (tag, push) are exercised against a local bare remote.
"""

from __future__ import annotations

import os
import subprocess

import pytest
from click.testing import CliRunner

from imas_standard_names.cli.release import (
    _apply_bump,
    _detect_state,
    _format_tag,
    _parse_version,
    compute_next_version,
    release_cmd,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_repo(tmp_path, monkeypatch):
    """Create a local git repo with a bare 'origin' remote for tag pushes.

    Returns a helper object with convenience methods.
    """
    repo_dir = tmp_path / "repo"
    bare_dir = tmp_path / "origin.git"
    repo_dir.mkdir()
    bare_dir.mkdir()

    def run_git(*args: str, cwd=None):
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or repo_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 and "fatal" in (result.stderr or ""):
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result

    # Init bare remote
    run_git("init", "--bare", str(bare_dir), cwd=tmp_path)

    # Init working repo
    run_git("init")
    run_git("config", "user.email", "test@test.com")
    run_git("config", "user.name", "Test")
    run_git("checkout", "-b", "main")

    # Initial commit so HEAD exists
    (repo_dir / "README.md").write_text("# Test\n")
    run_git("add", "README.md")
    run_git("commit", "-m", "Initial commit")

    # Add bare remote as 'origin'
    run_git("remote", "add", "origin", str(bare_dir))
    run_git("push", "-u", "origin", "main")

    # Also add as 'upstream' (same bare, for final release tests)
    run_git("remote", "add", "upstream", str(bare_dir))

    monkeypatch.chdir(repo_dir)

    class Repo:
        dir = repo_dir
        bare = bare_dir

        @staticmethod
        def git(*args):
            return run_git(*args)

        @staticmethod
        def tag(name: str, message: str = "test"):
            run_git("tag", "-a", name, "-m", message)

        @staticmethod
        def push_tag(name: str, remote: str = "origin"):
            run_git("push", remote, name)

        @staticmethod
        def commit(msg: str = "change"):
            f = repo_dir / f"file-{msg.replace(' ', '-')}.txt"
            f.write_text(msg)
            run_git("add", str(f))
            run_git("commit", "-m", msg)

        @staticmethod
        def dirty():
            (repo_dir / "dirty.txt").write_text("dirty")

    return Repo()


@pytest.fixture()
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# Unit tests: version parsing and formatting
# ---------------------------------------------------------------------------


class TestParseVersion:
    def test_stable(self):
        assert _parse_version("v1.2.3") == (1, 2, 3, None)

    def test_rc(self):
        assert _parse_version("v0.7.0rc25") == (0, 7, 0, 25)

    def test_strip_v(self):
        assert _parse_version("1.0.0") == (1, 0, 0, None)

    def test_invalid(self):
        with pytest.raises(Exception, match="Cannot parse"):
            _parse_version("not-a-version")


class TestFormatTag:
    def test_stable(self):
        assert _format_tag(1, 2, 3, None) == "v1.2.3"

    def test_rc(self):
        assert _format_tag(0, 7, 0, 25) == "v0.7.0rc25"


class TestApplyBump:
    def test_major(self):
        assert _apply_bump(1, 2, 3, "major") == (2, 0, 0)

    def test_minor(self):
        assert _apply_bump(1, 2, 3, "minor") == (1, 3, 0)

    def test_patch(self):
        assert _apply_bump(1, 2, 3, "patch") == (1, 2, 4)


# ---------------------------------------------------------------------------
# State machine: compute_next_version
# ---------------------------------------------------------------------------


class TestStableToPatchRC:
    """stable v1.0.0 + --bump patch → v1.0.1rc1"""

    def test_transition(self, git_repo):
        git_repo.tag("v1.0.0")
        tag, ver = compute_next_version("patch")
        assert tag == "v1.0.1rc1"
        assert ver == "1.0.1rc1"


class TestStableToMinorRC:
    """stable v1.0.0 + --bump minor → v1.1.0rc1"""

    def test_transition(self, git_repo):
        git_repo.tag("v1.0.0")
        tag, ver = compute_next_version("minor")
        assert tag == "v1.1.0rc1"
        assert ver == "1.1.0rc1"


class TestStableToMajorRC:
    """stable v1.0.0 + --bump major → v2.0.0rc1"""

    def test_transition(self, git_repo):
        git_repo.tag("v1.0.0")
        tag, ver = compute_next_version("major")
        assert tag == "v2.0.0rc1"
        assert ver == "2.0.0rc1"


class TestRCIterate:
    """RC v1.0.0rc1 + no flags → v1.0.0rc2"""

    def test_transition(self, git_repo):
        git_repo.tag("v1.0.0rc1")
        tag, ver = compute_next_version(None)
        assert tag == "v1.0.0rc2"
        assert ver == "1.0.0rc2"


class TestRCToFinal:
    """RC v1.0.0rc3 + --final → v1.0.0"""

    def test_transition(self, git_repo):
        git_repo.tag("v1.0.0rc3")
        tag, ver = compute_next_version(None, final=True)
        assert tag == "v1.0.0"
        assert ver == "1.0.0"


class TestFinalFromStableRejected:
    """stable v1.0.0 + --final (no bump) → error"""

    def test_rejection(self, git_repo):
        git_repo.tag("v1.0.0")
        with pytest.raises(Exception, match="--bump"):
            compute_next_version(None, final=True)


class TestStableNoBumpRejected:
    """stable v1.0.0 + no flags → error"""

    def test_rejection(self, git_repo):
        git_repo.tag("v1.0.0")
        with pytest.raises(Exception, match="--bump"):
            compute_next_version(None)


class TestDirectRelease:
    """stable v1.0.0 + --bump patch + --final → v1.0.1 (skip RC)"""

    def test_transition(self, git_repo):
        git_repo.tag("v1.0.0")
        tag, ver = compute_next_version("patch", final=True)
        assert tag == "v1.0.1"
        assert ver == "1.0.1"


class TestRCAbandonWithBump:
    """RC v2.0.0rc5 + --bump minor (stable=v1.0.0) → v1.1.0rc1"""

    def test_transition(self, git_repo):
        git_repo.tag("v1.0.0")
        git_repo.commit("wip")
        git_repo.tag("v2.0.0rc5")
        tag, ver = compute_next_version("minor")
        assert tag == "v1.1.0rc1"
        assert ver == "1.1.0rc1"


# ---------------------------------------------------------------------------
# State detection
# ---------------------------------------------------------------------------


class TestDetectState:
    def test_no_tags(self, git_repo):
        info = _detect_state()
        assert info["state"] is None

    def test_stable(self, git_repo):
        git_repo.tag("v2.0.0")
        info = _detect_state()
        assert info["state"] == "stable"
        assert info["tag"] == "v2.0.0"
        assert info["major"] == 2

    def test_rc(self, git_repo):
        git_repo.tag("v3.0.0rc7")
        info = _detect_state()
        assert info["state"] == "rc"
        assert info["rc"] == 7


# ---------------------------------------------------------------------------
# CLI integration tests (via CliRunner)
# ---------------------------------------------------------------------------


class TestDuplicateTagRejected:
    """Attempting to create a tag that already exists must fail."""

    def test_rejection(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.commit("next")
        git_repo.git("push", "origin", "main")
        git_repo.tag("v1.0.1rc1")
        git_repo.push_tag("v1.0.1rc1")
        # Now try to create v1.0.1rc1 again via --version override
        result = runner.invoke(
            release_cmd,
            ["--version", "v1.0.1rc1", "-m", "dup"],
        )
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestDryRunNoOp:
    """--dry-run must print version info but not create tags."""

    def test_no_tag_created(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.push_tag("v1.0.0")
        result = runner.invoke(
            release_cmd,
            ["--bump", "patch", "--dry-run", "-m", "test dry run"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "v1.0.1rc1" in result.output
        # Tag should NOT exist
        check = git_repo.git("tag", "-l", "v1.0.1rc1")
        assert check.stdout.strip() == ""


class TestSkipGitNoOp:
    """--skip-git must not create tags."""

    def test_no_tag_created(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.push_tag("v1.0.0")
        result = runner.invoke(
            release_cmd,
            ["--bump", "patch", "--skip-git", "-m", "test skip-git"],
        )
        assert result.exit_code == 0
        assert "Git operations skipped" in result.output
        # Tag should NOT exist
        check = git_repo.git("tag", "-l", "v1.0.1rc1")
        assert check.stdout.strip() == ""


class TestExplicitVersion:
    """--version overrides bump computation."""

    def test_override(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.push_tag("v1.0.0")
        result = runner.invoke(
            release_cmd,
            ["--version", "v9.9.9rc1", "--dry-run", "-m", "explicit"],
        )
        assert result.exit_code == 0
        assert "v9.9.9rc1" in result.output

    def test_invalid_format(self, git_repo, runner):
        result = runner.invoke(
            release_cmd,
            ["--version", "bad-version", "-m", "invalid"],
        )
        assert result.exit_code != 0
        assert "Invalid version format" in result.output


class TestStatusDisplay:
    """release status shows current state."""

    def test_stable_status(self, git_repo, runner):
        git_repo.tag("v2.0.0")
        result = runner.invoke(release_cmd, ["status"])
        assert result.exit_code == 0
        assert "Stable" in result.output
        assert "v2.0.0" in result.output

    def test_rc_status(self, git_repo, runner):
        git_repo.tag("v2.0.0rc3")
        result = runner.invoke(release_cmd, ["status"])
        assert result.exit_code == 0
        assert "RC mode" in result.output
        assert "v2.0.0rc3" in result.output

    def test_no_tags_status(self, git_repo, runner):
        result = runner.invoke(release_cmd, ["status"])
        assert result.exit_code == 0
        assert "No tags found" in result.output


class TestMessageRequired:
    """Release without -m must fail."""

    def test_missing_message(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        result = runner.invoke(release_cmd, ["--bump", "patch"])
        assert result.exit_code != 0
        assert "message" in result.output.lower()


class TestRCReleasePushesToOrigin:
    """RC release with --skip-git reports correct remote."""

    def test_default_remote_rc(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.push_tag("v1.0.0")
        result = runner.invoke(
            release_cmd,
            ["--bump", "patch", "--dry-run", "-m", "rc test"],
        )
        assert result.exit_code == 0
        assert "Remote:  origin" in result.output


class TestFinalReleasePushesToUpstream:
    """Final release reports upstream as target remote."""

    def test_default_remote_final(self, git_repo, runner):
        git_repo.tag("v1.0.0rc1")
        git_repo.push_tag("v1.0.0rc1")
        result = runner.invoke(
            release_cmd,
            ["--final", "--dry-run", "-m", "final test"],
        )
        assert result.exit_code == 0
        assert "Remote:  upstream" in result.output


class TestRemoteOverride:
    """--remote overrides the default target."""

    def test_override(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.push_tag("v1.0.0")
        result = runner.invoke(
            release_cmd,
            ["--bump", "patch", "--remote", "upstream", "--dry-run", "-m", "override"],
        )
        assert result.exit_code == 0
        assert "Remote:  upstream" in result.output


class TestDirtyWorktreePolicy:
    """RC releases warn on dirty tree; final releases abort."""

    def test_rc_allows_dirty(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.push_tag("v1.0.0")
        git_repo.dirty()
        result = runner.invoke(
            release_cmd,
            ["--bump", "patch", "--dry-run", "-m", "dirty rc"],
        )
        assert result.exit_code == 0
        assert "uncommitted" in result.output

    def test_final_rejects_dirty(self, git_repo, runner):
        git_repo.tag("v1.0.0rc1")
        git_repo.push_tag("v1.0.0rc1")
        git_repo.dirty()
        result = runner.invoke(
            release_cmd,
            ["--final", "-m", "dirty final"],
        )
        assert result.exit_code != 0
        assert "uncommitted" in result.output.lower()


class TestEndToEndTagCreation:
    """Full release (no dry-run, no skip-git) creates and pushes tag."""

    def test_rc_tag_created(self, git_repo, runner):
        git_repo.tag("v1.0.0")
        git_repo.push_tag("v1.0.0")
        result = runner.invoke(
            release_cmd,
            ["--bump", "patch", "-m", "RC release test"],
        )
        assert result.exit_code == 0
        assert "Created tag v1.0.1rc1" in result.output
        assert "Pushed v1.0.1rc1" in result.output
        # Verify tag exists locally
        check = git_repo.git("tag", "-l", "v1.0.1rc1")
        assert "v1.0.1rc1" in check.stdout
