from copy import deepcopy
import json

import pytest
from click.testing import CliRunner

from imas_standard_names.issues.cli import update_standardnames
from imas_standard_names import schema


@pytest.fixture
def submission_base(
    github_input,
):  # reuse github_input style but map to new schema keys
    # Map legacy keys to new per-file schema field names
    return {
        "name": github_input["name"],
        "kind": "scalar",
        "status": "draft",
        "unit": github_input["units"],
        "description": github_input["documentation"],
        "tags": github_input["tags"],
    }


def _write_submission(path, data):
    path.write_text(json.dumps(data))
    return path


def _catalog_entries(directory):
    return {p.stem for p in directory.glob("*.yml")}


@pytest.fixture
def work_env(tmp_path, base_names_data, base_genericnames, submission_base):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        temp_dir_path = tmp_path  # because isolated_filesystem copies into tmp_path
        standard_dir = temp_dir_path / "standard_names"
        standard_dir.mkdir(exist_ok=True)
        for e in base_names_data:
            schema.save_standard_name(schema.create_standard_name(e), standard_dir)
        generic_file = temp_dir_path / "generic_names.csv"
        base_genericnames.to_csv(generic_file, index=False)
        submission_file = temp_dir_path / "submission.json"
        _write_submission(submission_file, submission_base)
        yield runner, standard_dir, generic_file, submission_file


def test_update_standardnames_success(work_env, submission_base):
    runner, standard_dir, generic_file, submission_file = work_env
    result = runner.invoke(
        update_standardnames,
        (standard_dir.as_posix(), generic_file.as_posix(), submission_file.as_posix()),
    )
    assert result.exit_code == 0, result.output
    assert "proposal is ready for submission" in result.output.lower()
    assert submission_base["name"] in _catalog_entries(standard_dir)


def test_update_standardnames_overwrite(work_env, submission_base):
    runner, standard_dir, generic_file, submission_file = work_env
    # First insert a new name
    result = runner.invoke(
        update_standardnames,
        (standard_dir.as_posix(), generic_file.as_posix(), submission_file.as_posix()),
    )
    assert result.exit_code == 0
    # Overwrite by reusing same submission with overwrite flag
    result2 = runner.invoke(
        update_standardnames,
        (
            standard_dir.as_posix(),
            generic_file.as_posix(),
            submission_file.as_posix(),
            "--overwrite",
        ),
    )
    assert result2.exit_code == 0
    assert "proposal is ready for submission" in result2.output.lower()


def test_update_standardnames_duplicate_error(work_env, submission_base):
    runner, standard_dir, generic_file, submission_file = work_env
    # Insert once
    result = runner.invoke(
        update_standardnames,
        (standard_dir.as_posix(), generic_file.as_posix(), submission_file.as_posix()),
    )
    assert result.exit_code == 0
    # Attempt second without overwrite
    result2 = runner.invoke(
        update_standardnames,
        (standard_dir.as_posix(), generic_file.as_posix(), submission_file.as_posix()),
    )
    assert result2.exit_code == 0  # command handles error internally
    assert "already present" in result2.output.lower()


def test_update_standardnames_generic_name_error(work_env, submission_base):
    runner, standard_dir, generic_file, submission_file = work_env
    # Use a generic name from the generic file
    generic_submission = deepcopy(submission_base)
    generic_submission["name"] = "area"
    _write_submission(submission_file, generic_submission)
    result = runner.invoke(
        update_standardnames,
        (standard_dir.as_posix(), generic_file.as_posix(), submission_file.as_posix()),
    )
    assert result.exit_code == 0
    assert "generic name" in result.output.lower()
