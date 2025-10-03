from __future__ import annotations

from pathlib import Path

from imas_standard_names import schema
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.unit_of_work import UnitOfWork


def _make_simple(tmp: Path):
    (tmp / "a.yml").write_text(
        "name: a\nkind: scalar\nstatus: active\nunit: keV\ndescription: A.\n"
    )
    (tmp / "b.yml").write_text(
        "name: b\nkind: scalar\nstatus: active\nunit: keV\ndescription: B.\n"
    )


def test_repository_uow_writable_ops(tmp_path: Path):
    _make_simple(tmp_path)
    repo = StandardNameCatalog(tmp_path)
    # Add new entry via UoW
    uow = UnitOfWork(repo)
    new_model = schema.create_standard_name(
        {
            "name": "c",
            "kind": "scalar",
            "status": "draft",
            "unit": "keV",
            "description": "C entry.",
        }
    )
    uow.add(new_model)
    uow.commit()
    assert repo.get("c") is not None
    # Update existing
    uow.update(
        "a",
        schema.create_standard_name(
            {
                "name": "a",
                "kind": "scalar",
                "status": "active",
                "unit": "keV",
                "description": "A updated.",
            }
        ),
    )
    uow.commit()
    a_obj = repo.get("a")
    assert a_obj is not None and "updated" in a_obj.description.lower()
    # Delete b
    uow.remove("b")
    uow.commit()
    assert repo.get("b") is None
