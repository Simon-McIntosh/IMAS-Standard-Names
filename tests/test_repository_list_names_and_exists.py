from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.yaml_store import YamlStore


def test_list_names_and_exists(tmp_path: Path, example_scalars):
    # Use examples from catalog
    store = YamlStore(tmp_path)
    for example in example_scalars[:3]:
        store.write(example)

    repo = StandardNameCatalog(tmp_path)

    # exists() checks
    assert repo.exists(example_scalars[0].name) is True
    assert repo.exists(example_scalars[1].name) is True
    assert repo.exists("does_not_exist") is False

    # list_names should return sorted list of names (alphabetical)
    names = repo.list_names()
    assert names == sorted(names)
    expected_names = {ex.name for ex in example_scalars[:3]}
    assert set(names) >= expected_names

    # list() still returns hydrated models matching names
    hydrated = repo.list()
    hydrated_names = {m.name for m in hydrated}
    assert expected_names.issubset(hydrated_names)


def test_exists_after_uow_add_remove(tmp_path: Path):
    repo = StandardNameCatalog(tmp_path)
    assert not repo.exists("dynamic_entry")
    uow = repo.start_uow()
    model = create_standard_name_entry(
        {
            "name": "dynamic_entry",
            "kind": "scalar",
            "status": "active",
            "unit": "m",
            "description": "Dynamic entry.",
            "documentation": "Dynamic entry for repository list and exists testing.",
            "tags": ["fundamental"],
        }
    )
    uow.add(model)
    uow.commit()
    assert repo.exists("dynamic_entry")
    uow2 = repo.start_uow()
    uow2.remove("dynamic_entry")
    uow2.commit()
    assert not repo.exists("dynamic_entry")
