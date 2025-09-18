from pathlib import Path
import sqlite3
from click.testing import CliRunner

from imas_standard_names.cli.build_catalog import build_catalog_cli
from imas_standard_names.validation.cli import validate_catalog_cli


def _make_minimal_vector(tmp_path: Path):
    (tmp_path / "v.yml").write_text(
        """name: velocity
kind: vector
status: active
unit: m.s^-1
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
unit: m.s^-1
description: Radial component.
""",
        encoding="utf-8",
    )
    (tmp_path / "tor_component_of_velocity.yml").write_text(
        """name: tor_component_of_velocity
kind: scalar
status: active
unit: m.s^-1
description: Toroidal component.
""",
        encoding="utf-8",
    )


def test_build_catalog_cli(tmp_path: Path):
    _make_minimal_vector(tmp_path)
    artifacts = tmp_path / "artifacts"
    runner = CliRunner()
    # build with explicit db path
    db_path = artifacts / "catalog.db"
    result = runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM standard_name WHERE name='velocity'")
    assert cur.fetchone() is not None
    conn.close()


def test_validate_catalog_cli(tmp_path: Path):
    _make_minimal_vector(tmp_path)
    runner = CliRunner()
    result = runner.invoke(validate_catalog_cli, [str(tmp_path)])
    assert result.exit_code == 0, result.output
