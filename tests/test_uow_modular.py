from pathlib import Path

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.schema import create_standard_name


def test_uow_add_update_remove(tmp_path: Path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    a = create_standard_name(
        {
            "name": "ion_density",
            "kind": "scalar",
            "description": "Ion density.",
            "unit": "m^-3".replace("^-", "^-"),
        }
    )
    uow.add(a)
    # update description
    a2 = create_standard_name(
        {
            "name": "ion_density",
            "kind": "scalar",
            "description": "Updated ion density.",
            "unit": "m^-3".replace("^-", "^-"),
        }
    )
    uow.update("ion_density", a2)
    uow.commit()
    assert repo.get("ion_density").description.startswith("Updated")

    # Remove via new UoW
    uow2 = repo.start_uow()
    uow2.remove("ion_density")
    uow2.commit()
    assert repo.get("ion_density") is None


def test_uow_rollback(tmp_path: Path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    a = create_standard_name(
        {
            "name": "electron_pressure",
            "kind": "scalar",
            "description": "Electron pressure.",
            "unit": "Pa",
        }
    )
    uow.add(a)
    uow.rollback()
    assert repo.get("electron_pressure") is None
