from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog


def write_scalar(tmp: Path, name: str):
    (tmp / f"{name}.yml").write_text(
        f"""name: {name}\nkind: scalar\nstatus: active\nunit: m\ndescription: {name} description.""",
        encoding="utf-8",
    )


def test_repository_load_and_search(tmp_path: Path):
    write_scalar(tmp_path, "electron_temperature")
    write_scalar(tmp_path, "ion_temperature")
    repo = StandardNameCatalog(tmp_path)
    assert repo.get("electron_temperature") is not None
    results = repo.search("temperature")
    assert "electron_temperature" in results


def test_repository_uow_add_update_remove(tmp_path: Path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    model = create_standard_name_entry(
        {
            "name": "plasma_density",
            "kind": "scalar",
            "status": "active",
            "unit": "m^-3",
            "description": "Density.",
        }
    )
    uow.add(model)
    uow.commit()
    assert repo.get("plasma_density") is not None
    uow2 = repo.start_uow()
    updated = create_standard_name_entry(
        {
            "name": "plasma_density",
            "kind": "scalar",
            "status": "active",
            "unit": "m^-3",
            "description": "Updated density.",
        }
    )
    uow2.update("plasma_density", updated)
    uow2.commit()
    assert repo.get("plasma_density").description.startswith("Updated")
    uow3 = repo.start_uow()
    uow3.remove("plasma_density")
    uow3.commit()
    assert repo.get("plasma_density") is None
