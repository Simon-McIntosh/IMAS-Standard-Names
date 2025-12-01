import importlib.resources as ir

from click.testing import CliRunner

from imas_standard_names.issues.cli import (
    get_standardname,
    has_standardname,
    is_genericname,
)
from imas_standard_names.repository import StandardNameCatalog


def _get_example_names():
    """Get actual example names from catalog for testing."""
    files_obj = ir.files("imas_standard_names") / "resources" / "standard_name_examples"
    with ir.as_file(files_obj) as examples_path:
        catalog = StandardNameCatalog(root=examples_path, permissive=True)
        scalars = catalog.list(kind="scalar")
        return [s.name for s in scalars[:3]]


def test_has_standardname(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    # Use first example name from catalog
    example_names = _get_example_names()
    result = runner.invoke(has_standardname, (standardnames_dir, example_names[0]))
    assert result.exit_code == 0
    assert result.output == "True\n"


def test_has_not_standardname(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    result = runner.invoke(has_standardname, (standardnames_dir, "NonExistentName"))
    assert result.exit_code == 0
    assert result.output == "False\n"


def test_is_genericname():
    """Test is_genericname uses grammar vocabulary."""
    runner = CliRunner()
    result = runner.invoke(is_genericname, ("current",))
    assert result.exit_code == 0
    assert result.output == "True\n"


def test_is_not_genericname():
    """Test non-generic names return False."""
    runner = CliRunner()
    # Use actual example name which is not a generic name
    example_names = _get_example_names()
    result = runner.invoke(is_genericname, (example_names[0],))
    assert result.exit_code == 0
    assert result.output == "False\n"


def test_get_standardname(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    # Use second example name from catalog
    example_names = _get_example_names()
    result = runner.invoke(get_standardname, (standardnames_dir, example_names[1]))
    assert result.exit_code == 0
    # Expect YAML with name field present
    assert example_names[1] in result.output


def test_get_standardname_error(standardnames_dir_only):
    runner, standardnames_dir = standardnames_dir_only
    result = runner.invoke(
        get_standardname, (standardnames_dir, "invalid name with spaces")
    )
    assert result.exit_code == 0
    assert "not valid" in result.output.lower() or "keyerror" in result.output.lower()
