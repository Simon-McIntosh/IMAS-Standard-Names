from pathlib import Path
from click.testing import CliRunner

from imas_standard_names.validation.cli import validate_catalog_cli
from imas_standard_names.cli import standard_names


def _make_minimal_vector(tmp_path: Path):  # now simplified to scalars
    (tmp_path / "electron_temperature.yml").write_text(
        """name: electron_temperature
kind: scalar
status: active
unit: eV
description: Electron temperature.
""",
        encoding="utf-8",
    )
    (tmp_path / "ion_temperature.yml").write_text(
        """name: ion_temperature
kind: scalar
status: active
unit: eV
description: Ion temperature.
""",
        encoding="utf-8",
    )


def test_catalog_build_subcommand(tmp_path: Path):
    _make_minimal_vector(tmp_path)
    runner = CliRunner()
    result = runner.invoke(standard_names, ["build", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Built catalog" in result.output


def test_validate_catalog_cli(tmp_path: Path):
    _make_minimal_vector(tmp_path)
    runner = CliRunner()
    result = runner.invoke(validate_catalog_cli, [str(tmp_path)])
    assert result.exit_code == 0, result.output
