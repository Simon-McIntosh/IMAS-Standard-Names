import subprocess

from click.testing import CliRunner

from imas_standard_names.issues.cli import update_links


def test_update_links(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        temp_dir_path = tmp_path
        filename = temp_dir_path / "README.md"
        filename.write_text(
            """
[![coverage](https://github.com/iterorganization/IMAS-Standard-Names/badges/coverage.svg)](https://github.com/Simon-McIntosh/IMAS-Standard-Names/actions)
[![docs](https://img.shields.io/badge/docs-online-brightgreen)](https://github.com/iterorganization/IMAS-Standard-Names/actions)
"""
        )
        # Initialize a git repository
        subprocess.run(["git", "init"], cwd=temp_dir_path, check=True)
        subprocess.run(
            [
                "git",
                "remote",
                "add",
                "origin",
                "https://github.com/forked-username/IMAS-Standard-Names.git",
            ],
            cwd=temp_dir_path,
            check=True,
        )
        result = runner.invoke(
            update_links, ("origin", "--filename", filename.as_posix())
        )
        assert result.exit_code == 0
        text = filename.read_text()
        assert "forked-username" in text
        assert "iterorganization" not in text
        # Second invocation should be idempotent
        result2 = runner.invoke(
            update_links, ("origin", "--filename", filename.as_posix())
        )
        assert "No changes needed" in result2.output
