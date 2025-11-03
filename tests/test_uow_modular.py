from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog


def test_uow_add_update_remove(tmp_path: Path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    a = create_standard_name_entry(
        {
            "name": "ion_density",
            "kind": "scalar",
            "description": "Ion density.",
            "documentation": "Number density of ions in the plasma.",
            "unit": "m^-3".replace("^-", "^-"),
            "tags": ["fundamental"],
        }
    )
    uow.add(a)
    # update description
    a2 = create_standard_name_entry(
        {
            "name": "ion_density",
            "kind": "scalar",
            "description": "Updated ion density.",
            "documentation": "Number density of ions in the plasma (updated).",
            "unit": "m^-3".replace("^-", "^-"),
            "tags": ["fundamental"],
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
    a = create_standard_name_entry(
        {
            "name": "electron_pressure",
            "kind": "scalar",
            "description": "Electron pressure.",
            "documentation": "Pressure of electrons in the plasma.",
            "unit": "Pa",
            "tags": ["fundamental"],
        }
    )
    uow.add(a)
    uow.rollback()
    assert repo.get("electron_pressure") is None
