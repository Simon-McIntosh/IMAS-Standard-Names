from pathlib import Path
import json
from click.testing import CliRunner

from imas_standard_names.cli.build_catalog import build_catalog_cli
from imas_standard_names.validation.cli import validate_catalog_cli


def _make_minimal_vector(tmp_path: Path):
    (tmp_path / "v.yml").write_text(
        """name: velocity
kind: vector
status: active
unit: m/s
description: Velocity.
frame: cylindrical_r_tor_z
components:
  r: r_component_of_velocity
  tor: tor_component_of_velocity
""",
        encoding="utf-8",
    )
    (tmp_path / "r_component_of_velocity.yml").write_text(
        """name: r_component_of_velocity
kind: scalar
status: active
unit: m/s
description: Radial component.
axis: r
parent_vector: velocity
""",
        encoding="utf-8",
    )
    (tmp_path / "tor_component_of_velocity.yml").write_text(
        """name: tor_component_of_velocity
kind: scalar
status: active
unit: m/s
description: Toroidal component.
axis: tor
parent_vector: velocity
""",
        encoding="utf-8",
    )


def test_build_catalog_cli(tmp_path: Path):
    _make_minimal_vector(tmp_path)
    out_dir = tmp_path / "artifacts"
    runner = CliRunner()
    result = runner.invoke(build_catalog_cli, [str(tmp_path), str(out_dir)])
    assert result.exit_code == 0, result.output
    assert (out_dir / "catalog.json").exists()
    data = json.loads((out_dir / "catalog.json").read_text())
    assert "velocity" in data


def test_validate_catalog_cli(tmp_path: Path):
    _make_minimal_vector(tmp_path)
    runner = CliRunner()
    result = runner.invoke(validate_catalog_cli, [str(tmp_path)])
    assert result.exit_code == 0, result.output
