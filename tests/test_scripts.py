from contextlib import contextmanager

from click.testing import CliRunner
import pandas
import json
from pathlib import Path
import pytest
import strictyaml as syaml

from imas_standard_names.scripts import (
    get_standardname,
    has_standardname,
    is_genericname,
    update_standardnames,
)


github_input = {
    "name": "ion_temperature",
    "units": "A",
    "documentation": "multi-line\ndoc string",
    "tags": "",
    "alias": "",
    "options": [],
}

standardnames = syaml.as_document(
    {
        name: {"units": units, "documentation": "docs"}
        for name, units in zip(
            ["plasma_current", "plasma_current_density", "electron_temperature"],
            ["A", "A/m^2", "eV"],
        )
    }
)

genericnames = pandas.DataFrame(
    [("m^2", "area"), ("A", "current"), ("J", "energy")],
    columns=["Unit", "Generic Name"],
)


@contextmanager
def launch_cli(
    standardnames: syaml.representation.YAML,
    genericnames: pandas.DataFrame,
    github_input: dict[str, str],
    path: str | Path,
):
    """Lanuch CLI to update a temporary standard names file with input data."""
    with (
        click_runner(path) as (runner, temp_dir),
        write_standardnames(standardnames, temp_dir) as standardnames_file,
        write_genericnames(genericnames, temp_dir) as genericnames_file,
        write_submission(github_input, temp_dir) as submission_file,
    ):
        yield runner, (standardnames_file, genericnames_file, submission_file)


@contextmanager
def click_runner(path: str | Path):
    """Lanuch click runner within isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=path) as temp_dir:
        yield runner, temp_dir


@contextmanager
def write_standardnames(standardnames: syaml.representation.YAML, temp_dir):
    """Write yaml standardnames to a temporary file."""
    standardnames_file = Path(temp_dir) / "standardnames.yml"
    with open(standardnames_file, "w") as f:
        f.write(standardnames.as_yaml())
    yield standardnames_file.as_posix()


@contextmanager
def write_genericnames(genericnames: pandas.DataFrame, temp_dir):
    """Write csv genericnames to a temporary file."""
    genericnames_file = Path(temp_dir) / "generic_names.csv"
    with open(genericnames_file, "w", newline="") as f:
        genericnames.to_csv(f, index=False)
    yield genericnames_file.as_posix()


@contextmanager
def write_submission(github_input: dict[str, str], temp_dir):
    """Write json submission to a temporary file."""
    submission_file = Path(temp_dir) / "submission.json"
    with open(submission_file, "w") as f:
        f.write(json.dumps(github_input))
    yield submission_file.as_posix()


def test_add_standard_name(tmp_path):
    assert not github_input["options"]
    with launch_cli(standardnames, genericnames, github_input, tmp_path) as (
        runner,
        args,
    ):
        result = runner.invoke(update_standardnames, args)
    assert (
        f"The proposed Standard Name **{github_input['name']}** is valid."
        in result.output
    )


def test_overwrite(tmp_path):
    _github_input = github_input.copy()
    _github_input["name"] = "plasma_current"
    _github_input["options"] = "overwrite"
    with launch_cli(standardnames, genericnames, _github_input, tmp_path) as (
        runner,
        args,
    ):
        result = runner.invoke(update_standardnames, args)
    assert "The proposed Standard Name **plasma_current** is valid." in result.output


def test_overwrite_error(tmp_path):
    _github_input = github_input.copy()
    _github_input["name"] = "plasma_current"
    with launch_cli(standardnames, genericnames, _github_input, tmp_path) as (
        runner,
        args,
    ):
        result = runner.invoke(update_standardnames, args)
    assert "Error" in result.output
    assert "**plasma_current** is already present" in result.output


def test_standard_name_error(tmp_path):
    _github_input = github_input.copy()
    _github_input["name"] = "1st_plasma_current"
    with launch_cli(standardnames, genericnames, _github_input, tmp_path) as (
        runner,
        args,
    ):
        result = runner.invoke(update_standardnames, args)
    assert "Error" in result.output
    assert f"**{_github_input['name']}** is *not* valid" in result.output


def test_standard_name_alias(tmp_path):
    _github_input = github_input.copy()
    _github_input |= {"name": "second_plasma_current", "alias": "plasma_current"}
    with launch_cli(standardnames, genericnames, _github_input, tmp_path) as (
        runner,
        args,
    ):
        result = runner.invoke(update_standardnames, args)
    assert (
        f"The proposed Standard Name **{_github_input['name']}** is valid."
        in result.output
    )


def test_standard_name_alias_error(tmp_path):
    _github_input = github_input.copy()
    _github_input |= {"name": "second_plasma_current", "alias": "1st_plasma_current"}
    with launch_cli(standardnames, genericnames, _github_input, tmp_path) as (
        runner,
        args,
    ):
        result = runner.invoke(update_standardnames, args)
    assert "Error" in result.output
    assert f"**{_github_input['alias']}** is not present" in result.output


def test_standard_name_generic_error(tmp_path):
    _github_input = github_input.copy()
    _github_input["name"] = "area"
    with launch_cli(standardnames, genericnames, _github_input, tmp_path) as (
        runner,
        args,
    ):
        result = runner.invoke(update_standardnames, args)
    assert "Error" in result.output
    assert f"**{_github_input['name']}** is a generic name" in result.output


def test_has_standardname(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames(standardnames, temp_dir) as standardnames_file,
    ):
        result = runner.invoke(has_standardname, (standardnames_file, "plasma_current"))
    assert result.exit_code == 0
    assert result.output == "True\n"


def test_has_not_standardname(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames(standardnames, temp_dir) as standardnames_file,
    ):
        result = runner.invoke(has_standardname, (standardnames_file, "PlasmaCurrent"))
    assert result.exit_code == 0
    assert result.output == "False\n"


def test_is_genericname(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_genericnames(genericnames, temp_dir) as genericnames_file,
    ):
        result = runner.invoke(is_genericname, (genericnames_file, "current"))
    assert result.exit_code == 0
    assert result.output == "True\n"


def test_is_not_genericname(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_genericnames(genericnames, temp_dir) as genericnames_file,
    ):
        result = runner.invoke(is_genericname, (genericnames_file, "plasma_current"))
    assert result.exit_code == 0
    assert result.output == "False\n"


def test_standardname_whitespace(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames(standardnames, temp_dir) as standardnames_file,
    ):
        result = runner.invoke(has_standardname, (standardnames_file, "Plasma Current"))
    assert result.exit_code == 0
    assert result.output == "False\n"


def test_get_standardname(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames(standardnames, temp_dir) as standardnames_file,
    ):
        result = runner.invoke(
            get_standardname,
            (standardnames_file, "plasma_current_density", "--unit-format", "~P"),
        )
    assert result.exit_code == 0
    assert "units: A/m²" in result.output


def test_get_standardname_default_unit_format(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames(standardnames, temp_dir) as standardnames_file,
    ):
        result = runner.invoke(
            get_standardname,
            (standardnames_file, "plasma_current_density"),
        )
    assert result.exit_code == 0
    assert "$`\\frac{\\mathrm{ampere}}{\\mathrm{meter}^{2}}`$" in result.output


def test_get_standardname_error(tmp_path):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames(standardnames, temp_dir) as standardnames_file,
    ):
        result = runner.invoke(get_standardname, (standardnames_file, "plasma current"))
    assert result.exit_code == 0
    assert "KeyError" in result.output


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
