from imas_standard_names.issues.cli import (
    has_standardname,
    is_genericname,
    get_standardname,
)


def test_has_standardname(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    result = runner.invoke(has_standardname, (standardnames_dir, "plasma_current"))
    assert result.exit_code == 0
    assert result.output == "True\n"


def test_has_not_standardname(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    result = runner.invoke(has_standardname, (standardnames_dir, "PlasmaCurrent"))
    assert result.exit_code == 0
    assert result.output == "False\n"


def test_is_genericname(genericnames_file_only):
    runner, genericnames_file = genericnames_file_only
    result = runner.invoke(is_genericname, (genericnames_file, "current"))
    assert result.exit_code == 0
    assert result.output == "True\n"


def test_is_not_genericname(genericnames_file_only):
    runner, genericnames_file = genericnames_file_only
    result = runner.invoke(is_genericname, (genericnames_file, "plasma_current"))
    assert result.exit_code == 0
    assert result.output == "False\n"


def test_get_standardname(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    result = runner.invoke(
        get_standardname, (standardnames_dir, "plasma_current_density")
    )
    assert result.exit_code == 0
    # Expect YAML with name field present
    assert "plasma_current_density" in result.output


def test_get_standardname_error(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    result = runner.invoke(get_standardname, (standardnames_dir, "plasma current"))
    assert result.exit_code == 0
    assert "not valid" in result.output.lower() or "keyerror" in result.output.lower()
