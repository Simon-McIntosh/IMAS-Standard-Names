from pathlib import Path

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.schema import create_standard_name


def write_scalar(tmp: Path, name: str):
    (tmp / f"{name}.yml").write_text(
        f"""name: {name}\nkind: scalar\nstatus: active\nunit: m\ndescription: {name} description.""",
        encoding="utf-8",
    )


def test_list_names_and_exists(tmp_path: Path):
    # Create a few scalar standard name YAML entries
    write_scalar(tmp_path, "a_density")
    write_scalar(tmp_path, "z_temperature")
    write_scalar(tmp_path, "m_pressure")
    repo = StandardNameCatalog(tmp_path)

    # exists() checks
    assert repo.exists("a_density") is True
    assert repo.exists("z_temperature") is True
    assert repo.exists("does_not_exist") is False

    # list_names should return sorted list of names (alphabetical)
    names = repo.list_names()
    assert names == sorted(names)
    assert set(names) >= {"a_density", "z_temperature", "m_pressure"}

    # list() still returns hydrated models matching names
    hydrated = repo.list()
    hydrated_names = {m.name for m in hydrated}
    assert {"a_density", "z_temperature", "m_pressure"}.issubset(hydrated_names)


def test_exists_after_uow_add_remove(tmp_path: Path):
    repo = StandardNameCatalog(tmp_path)
    assert not repo.exists("dynamic_entry")
    uow = repo.start_uow()
    model = create_standard_name(
        {
            "name": "dynamic_entry",
            "kind": "scalar",
            "status": "active",
            "unit": "m",
            "description": "Dynamic entry.",
        }
    )
    uow.add(model)
    uow.commit()
    assert repo.exists("dynamic_entry")
    uow2 = repo.start_uow()
    uow2.remove("dynamic_entry")
    uow2.commit()
    assert not repo.exists("dynamic_entry")
