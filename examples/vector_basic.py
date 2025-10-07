"""Vector standard name example.

Demonstrates creating a base vector with components using metadata convention.
Highlights:
  * Components are specified at runtime via vector_axes metadata attribute.
  * Component standard names follow <axis>_component_of_<vector> pattern.
  * Magnitude standard name is conventional: magnitude_of_<vector>.
  * Component scalars are separate catalog entries.
"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.schema import create_standard_name


@contextmanager
def tmp_root():
    with tempfile.TemporaryDirectory(prefix="stdnames_vec_") as d:
        root = Path(d) / "standard_names" / "magnetic_field"
        root.mkdir(parents=True, exist_ok=True)
        yield root


def main():
    with tmp_root() as root:
        repo = StandardNameCatalog(root)
        uow = repo.start_uow()

        # Stage component scalars first (required before vector insert)
        for axis in ("radial", "toroidal", "vertical"):
            uow.add(
                create_standard_name(
                    {
                        "name": f"{axis}_component_of_magnetic_field",
                        "kind": "scalar",
                        "unit": "T",
                        "description": f"{axis.capitalize()} component of magnetic_field.",
                        "status": "draft",
                    }
                )
            )

        # Vector definition - components specified via metadata at runtime
        vector = create_standard_name(
            {
                "name": "magnetic_field",
                "kind": "vector",
                "unit": "T",
                "description": "Magnetic field vector.",
                "status": "draft",
            }
        )
        uow.add(vector)

        print("Staged names:", sorted(repo.list_names()))
        print("Implicit magnitude name:", vector.magnitude)
        uow.commit()
        print("Committed. Vector exists?", repo.exists("magnetic_field"))


if __name__ == "__main__":  # pragma: no cover
    main()
