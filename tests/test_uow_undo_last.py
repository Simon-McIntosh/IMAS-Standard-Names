import pytest

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.schema import create_standard_name


def make_scalar(name, unit="eV"):
    return create_standard_name(
        {
            "name": name,
            "kind": "scalar",
            "unit": unit,
            "description": f"Desc for {name}",
            "status": "draft",
        }
    )


def test_undo_last_add(tmp_path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    uow.add(make_scalar("a"))
    assert repo.exists("a")
    assert uow.undo_last() is True
    assert not repo.exists("a")
    assert uow.undo_last() is False  # nothing left


def test_undo_last_update(tmp_path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    uow.add(make_scalar("x"))
    # update x with new unit (simulate change)
    new_x = make_scalar("x", unit="keV")
    uow.update("x", new_x)
    # undo update restores old version (unit eV)
    assert uow.undo_last() is True
    model = repo.get("x")
    assert model.unit == "eV"


def test_undo_last_rename(tmp_path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    uow.add(make_scalar("orig"))
    renamed = make_scalar("new_name")
    uow.rename("orig", renamed)
    assert repo.exists("new_name") and not repo.exists("orig")
    uow.undo_last()
    assert repo.exists("orig") and not repo.exists("new_name")


def test_undo_last_chain(tmp_path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    uow.add(make_scalar("a"))
    uow.add(make_scalar("b"))
    uow.remove("a")
    assert repo.exists("b") and not repo.exists("a")
    # undo remove (restores a)
    uow.undo_last()
    assert repo.exists("a")
    # undo add of b (removes b)
    uow.undo_last()
    assert not repo.exists("b") and repo.exists("a")
    # undo add of a (removes a)
    uow.undo_last()
    assert not repo.exists("a")


def test_undo_last_closed(tmp_path):
    repo = StandardNameCatalog(tmp_path)
    uow = repo.start_uow()
    uow.add(make_scalar("a"))
    uow.commit()
    with pytest.raises(RuntimeError):
        uow.undo_last()
