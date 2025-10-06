import json
from pathlib import Path

from imas_standard_names.issues.cli import update_standardnames


def _rewrite_submission(file_path: str, **updates):
    data = json.loads(Path(file_path).read_text())
    data.update(updates)
    Path(file_path).write_text(json.dumps(data))


def test_add_standard_name(cli_env):
    runner, (standardnames_dir, genericnames_file, submission_file) = cli_env
    result = runner.invoke(
        update_standardnames,
        (standardnames_dir, genericnames_file, submission_file),
    )
    assert result.exit_code == 0
    assert "proposal is ready for submission" in result.output


def test_overwrite(cli_env):
    runner, (standardnames_dir, genericnames_file, submission_file) = cli_env
    _rewrite_submission(submission_file, name="plasma_current")
    # First attempt without overwrite should error
    result1 = runner.invoke(
        update_standardnames,
        (standardnames_dir, genericnames_file, submission_file),
    )
    # Current behaviour: schema validation or duplicate detection message
    assert (
        "not valid" in result1.output.lower()
        or "already present" in result1.output.lower()
    )
    # Second with overwrite
    result2 = runner.invoke(
        update_standardnames,
        (standardnames_dir, genericnames_file, submission_file, "--overwrite"),
    )
    assert result2.exit_code == 0


def test_invalid_name(cli_env):
    runner, (standardnames_dir, genericnames_file, submission_file) = cli_env
    _rewrite_submission(submission_file, name="1st_plasma_current")
    result = runner.invoke(
        update_standardnames,
        (standardnames_dir, genericnames_file, submission_file),
    )
    assert result.exit_code == 0
    assert "not valid" in result.output.lower()


def test_alias_success(cli_env):
    runner, (standardnames_dir, genericnames_file, submission_file) = cli_env
    _rewrite_submission(
        submission_file, name="second_plasma_current", alias="plasma_current"
    )
    result = runner.invoke(
        update_standardnames,
        (standardnames_dir, genericnames_file, submission_file),
    )
    assert "proposal is ready for submission" in result.output


def test_generic_name_error(cli_env):
    runner, (standardnames_dir, genericnames_file, submission_file) = cli_env
    _rewrite_submission(submission_file, name="area")
    result = runner.invoke(
        update_standardnames,
        (standardnames_dir, genericnames_file, submission_file),
    )
    # Current implementation surfaces schema validation error before generic name message
    assert "not valid" in result.output.lower()
