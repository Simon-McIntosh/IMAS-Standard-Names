from imas_standard_names.schema import create_standard_name
from imas_standard_names.repositories import YamlStandardNameRepository
from imas_standard_names.unit_of_work import UnitOfWork


def test_unit_of_work_add_update_remove_commit(tmp_path):
    root = tmp_path / "standard_names"
    root.mkdir()
    repo = YamlStandardNameRepository(root)
    uow = UnitOfWork(repo)

    # Add new entry
    a = create_standard_name(
        {
            "kind": "scalar",
            "name": "electron_density",
            "description": "Electron density",
            "unit": "m^-3",
            "status": "draft",
        }
    )
    uow.add(a)
    uow.commit()
    assert repo.exists("electron_density")
    file_path = root / "electron_density.yml"
    assert file_path.exists()

    # Update (change description)
    updated = create_standard_name(
        {
            "kind": "scalar",
            "name": "electron_density",
            "description": "Electron density (updated)",
            "unit": "m^-3",
            "status": "active",
        }
    )
    uow.update("electron_density", updated)
    uow.commit()
    # Reload via repo
    model = repo.get("electron_density")
    assert model is not None
    assert model.description.startswith("Electron density (updated)")
    # Remove
    uow.remove("electron_density")
    uow.commit()
    assert not repo.exists("electron_density")
    assert not file_path.exists()
