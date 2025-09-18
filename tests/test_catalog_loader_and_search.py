from __future__ import annotations
from pathlib import Path
import time
from click.testing import CliRunner

from imas_standard_names.catalog.catalog import load_catalog, StandardNameCatalog
from imas_standard_names.cli.build_catalog import build_catalog_cli
from imas_standard_names.validation.cli import validate_catalog_cli
from imas_standard_names.cli.search_catalog import search_catalog_cli


def _write_minimal_yaml(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "temperature.yml").write_text(
        """name: electron_temperature\nkind: scalar\nstatus: active\nunit: keV\ndescription: Electron temperature.\n""",
        encoding="utf-8",
    )
    (root / "density.yml").write_text(
        """name: electron_density\nkind: scalar\nstatus: active\nunit: m^-3\ndescription: Electron density profile.\n""",
        encoding="utf-8",
    )


def test_load_catalog_smart_yaml_fallback(tmp_path: Path):
    # No DB yet -> YAML load
    _write_minimal_yaml(tmp_path)
    cat = load_catalog(tmp_path, prefer_db=True)
    assert cat.source == "yaml"
    assert "electron_temperature" in cat.entries


def test_build_and_load_sqlite_artifact_then_prefer_db(tmp_path: Path):
    _write_minimal_yaml(tmp_path)
    artifacts = tmp_path / "artifacts"
    db_path = artifacts / "catalog.db"
    runner = CliRunner()
    result = runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    assert result.exit_code == 0, result.output
    # Smart loader should now pick sqlite
    cat = load_catalog(tmp_path, db_path=db_path)
    assert cat.source.startswith("sqlite")
    assert "electron_density" in cat.entries


def test_rebuild_if_stale_skip(tmp_path: Path):
    _write_minimal_yaml(tmp_path)
    artifacts = tmp_path / "artifacts"
    db_path = artifacts / "catalog.db"
    runner = CliRunner()
    res1 = runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    assert res1.exit_code == 0
    mtime_before = db_path.stat().st_mtime
    # Invoke again: should skip rebuild (exit 0, unchanged mtime)
    time.sleep(0.05)  # ensure timestamp resolution window
    res2 = runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    assert res2.exit_code == 0
    assert db_path.stat().st_mtime == mtime_before


def test_rebuild_if_stale_detect_change(tmp_path: Path):
    _write_minimal_yaml(tmp_path)
    artifacts = tmp_path / "artifacts"
    db_path = artifacts / "catalog.db"
    runner = CliRunner()
    runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    mtime_before = db_path.stat().st_mtime
    # Modify a YAML file -> mtime update -> rebuild triggers
    time.sleep(0.05)
    (tmp_path / "temperature.yml").write_text(
        """name: electron_temperature\nkind: scalar\nstatus: active\nunit: keV\ndescription: Electron temperature updated.\n""",
        encoding="utf-8",
    )
    res = runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    assert res.exit_code == 0
    assert db_path.stat().st_mtime >= mtime_before


def test_validate_catalog_cli_uses_sqlite_when_available(tmp_path: Path):
    _write_minimal_yaml(tmp_path)
    artifacts = tmp_path / "artifacts"
    db_path = artifacts / "catalog.db"
    runner = CliRunner()
    runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    # Validation should succeed using dispatcher (prefers db by default)
    res = runner.invoke(validate_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    assert res.exit_code == 0, res.output


def test_search_catalog_cli_ranked(tmp_path: Path):
    _write_minimal_yaml(tmp_path)
    artifacts = tmp_path / "artifacts"
    db_path = artifacts / "catalog.db"
    runner = CliRunner()
    runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    res = runner.invoke(
        search_catalog_cli, [str(tmp_path), "electron", "--db", str(db_path), "--meta"]
    )
    assert res.exit_code == 0, res.output
    out = res.output.strip()
    assert "electron_temperature" in out
    assert "score" in out  # meta JSON contains score field


def test_from_yaml_and_from_sqlite_factories(tmp_path: Path):
    _write_minimal_yaml(tmp_path)
    # Build artifact
    artifacts = tmp_path / "artifacts"
    db_path = artifacts / "catalog.db"
    runner = CliRunner()
    runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    yaml_cat = StandardNameCatalog.from_yaml(tmp_path)
    assert yaml_cat.source == "yaml"
    sql_cat = StandardNameCatalog.from_sqlite(
        tmp_path, db_path=db_path, revalidate=False
    )
    assert sql_cat.source == "sqlite"
    # Ensure fast path objects still provide attributes
    temp = sql_cat.get("electron_temperature")
    assert temp is not None
    assert hasattr(temp, "unit") and temp.unit == "keV"


def test_fast_path_load_catalog_revalidate_false(tmp_path: Path):
    _write_minimal_yaml(tmp_path)
    artifacts = tmp_path / "artifacts"
    db_path = artifacts / "catalog.db"
    runner = CliRunner()
    runner.invoke(build_catalog_cli, [str(tmp_path), "--db", str(db_path)])
    cat = load_catalog(tmp_path, db_path=db_path, revalidate=False)
    obj = cat.get("electron_density")
    assert obj is not None
    # SimpleNamespace instance (fast path) should expose attributes
    assert hasattr(obj, "description")
    assert getattr(obj, "description").startswith("Electron density")
