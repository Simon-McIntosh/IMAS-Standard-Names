from pathlib import Path
import json
from click.testing import CliRunner

from imas_standard_names.cli.search_catalog import search_catalog_cli
from imas_standard_names.cli.build_catalog import build_catalog_cli


def _seed(root: Path):
    (root / "a.yml").write_text(
        "name: electron_temperature\nkind: scalar\nstatus: active\nunit: keV\ndescription: Electron temperature.\n"
    )
    (root / "b.yml").write_text(
        "name: ion_temperature\nkind: scalar\nstatus: draft\nunit: keV\ndescription: Ion temperature.\n"
    )


def test_search_mode_memory(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    res = runner.invoke(
        search_catalog_cli, [str(tmp_path), "electron", "--mode", "memory", "--meta"]
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert any(r["name"] == "electron_temperature" for r in payload)
    assert all(r["source"] == "memory" for r in payload)


def test_search_mode_file(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    # Build file-backed catalog
    build_res = runner.invoke(build_catalog_cli, [str(tmp_path)])
    assert build_res.exit_code == 0, build_res.output
    res = runner.invoke(
        search_catalog_cli, [str(tmp_path), "ion", "--mode", "file", "--meta"]
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert any(r["name"] == "ion_temperature" for r in payload)
    assert all(r["source"] == "file" for r in payload)


def test_search_mode_auto_prefers_file(tmp_path: Path):
    _seed(tmp_path)
    runner = CliRunner()
    # Build file-backed catalog
    runner.invoke(build_catalog_cli, [str(tmp_path)])
    res = runner.invoke(
        search_catalog_cli, [str(tmp_path), "temperature", "--mode", "auto", "--meta"]
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    # Should include both names and mark file as source
    names = {r["name"] for r in payload}
    assert {"electron_temperature", "ion_temperature"}.issubset(names)
    assert all(r["source"] == "file" for r in payload)
