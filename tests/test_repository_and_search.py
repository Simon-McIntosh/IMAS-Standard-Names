from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.yaml_store import YamlStore


def test_repository_load_and_search(tmp_path: Path, example_scalars):
    # Use examples from catalog instead of hardcoded data
    store = YamlStore(tmp_path)
    for entry in example_scalars[:2]:
        store.write(entry)

    repo = StandardNameCatalog(tmp_path)
    # Use first example name for assertions
    first_name = example_scalars[0].name
    assert repo.get(first_name) is not None
    # Search using part of the name
    search_term = first_name.split("_")[0]
    results = repo.search(search_term)
    assert first_name in results


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
            "documentation": "Density for repository and search testing.",
            "tags": ["fundamental"],
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
            "documentation": "Updated density for repository and search testing.",
            "tags": ["fundamental"],
        }
    )
    uow2.update("plasma_density", updated)
    uow2.commit()
    assert repo.get("plasma_density").description.startswith("Updated")
    uow3 = repo.start_uow()
    uow3.remove("plasma_density")
    uow3.commit()
    assert repo.get("plasma_density") is None
