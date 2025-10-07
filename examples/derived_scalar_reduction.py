"""Derived scalar (reduction) example.

Demonstrates a time average reduction of a base scalar.
Highlights:
  * Base scalar must exist first.
  * Reduction naming pattern: time_average_of_<base>
  * Provenance.mode = reduction with fields: reduction, domain, base.
  * Validation enforces name ↔ provenance consistency.
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.schema import create_standard_name


@contextmanager
def tmp_root():
    with tempfile.TemporaryDirectory(prefix="stdnames_redscalar_") as d:
        root = Path(d) / "standard_names"
        root.mkdir(parents=True, exist_ok=True)
        yield root


def main():
    with tmp_root() as root:
        repo = StandardNameCatalog(root)
        uow = repo.start_uow()

        base = create_standard_name(
            {
                "name": "ion_temperature",
                "kind": "scalar",
                "unit": "eV",
                "description": "Ion temperature.",
                "status": "draft",
            }
        )
        uow.add(base)

        reduction = create_standard_name(
            {
                "name": "time_average_of_ion_temperature",
                "kind": "scalar",
                "unit": "eV",
                "description": "Time average of ion_temperature.",
                "status": "draft",
                "provenance": {
                    "mode": "reduction",
                    "reduction": "mean",
                    "domain": "time",
                    "base": "ion_temperature",
                },
            }
        )
        uow.add(reduction)

        print("Staged names:", sorted(repo.list_names()))
        uow.commit()
        print(
            "Committed. Reduction exists?",
            repo.exists("time_average_of_ion_temperature"),
        )


if __name__ == "__main__":  # pragma: no cover
    main()
