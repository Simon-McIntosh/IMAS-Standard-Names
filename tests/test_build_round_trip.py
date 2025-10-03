from pathlib import Path

from imas_standard_names.catalog.sqlite_build import build_catalog
from imas_standard_names.catalog.sqlite_read import CatalogRead
from imas_standard_names.repository import StandardNameCatalog


def _write_example(root: Path):
    (root / "electron_temperature.yml").write_text(
        "name: electron_temperature\nkind: scalar\nstatus: active\nunit: keV\ndescription: Electron temperature.\n"
    )
    (root / "ion_temperature.yml").write_text(
        "name: ion_temperature\nkind: scalar\nstatus: draft\nunit: keV\ndescription: Ion temperature.\n"
    )


def test_build_catalog_round_trip(tmp_path: Path):
    yaml_root = tmp_path / "standard_names"
    yaml_root.mkdir()
    _write_example(yaml_root)
    # Load via repository (in-memory) baseline
    repo = StandardNameCatalog(yaml_root)
    baseline = {m.name: m.description for m in repo.list()}
    # Build file-backed catalog
    db_path = tmp_path / "artifacts" / "catalog.db"
    build_catalog(yaml_root, db_path, overwrite=True)
    assert db_path.exists()
    # Open read-only
    ro = CatalogRead(db_path)
    rebuilt = {m.name: m.description for m in ro.list()}
    assert baseline == rebuilt
    # Ensure FTS search works identically
    results = ro.search("electron_temperature")
    assert "electron_temperature" in results
