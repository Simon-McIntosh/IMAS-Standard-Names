"""Derived scalar example (operator provenance).

Creates a time derivative of electron_temperature. Requirements:
  * Base scalar (electron_temperature) must exist first.
  * Derived scalar name must follow operator pattern: time_derivative_of_<base>.
  * Provenance specifies operators, base, and operator_id.
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

from imas_standard_names.repository import StandardNameRepository
from imas_standard_names.schema import create_standard_name


@contextmanager
def tmp_root():
    with tempfile.TemporaryDirectory(prefix="stdnames_dscalar_") as d:
        root = Path(d) / "standard_names"
        root.mkdir(parents=True, exist_ok=True)
        yield root


def main():
    with tmp_root() as root:
        repo = StandardNameRepository(root)
        uow = repo.start_uow()

        base = create_standard_name(
            {
                "name": "electron_temperature",
                "kind": "scalar",
                "unit": "eV",
                "description": "Electron temperature.",
                "status": "draft",
            }
        )
        uow.add(base)

        derived = create_standard_name(
            {
                "name": "time_derivative_of_electron_temperature",
                "kind": "derived_scalar",
                "unit": "eV.s^-1",
                "description": "Temporal derivative of electron_temperature.",
                "status": "draft",
                "provenance": {
                    "mode": "operator",
                    "operators": ["time_derivative"],
                    "base": "electron_temperature",
                    "operator_id": "time_derivative",
                },
            }
        )
        uow.add(derived)

        print("Staged names:", sorted(repo.list_names()))
        uow.commit()
        print(
            "Committed. Derived exists?",
            repo.exists("time_derivative_of_electron_temperature"),
        )


if __name__ == "__main__":  # pragma: no cover
    main()
