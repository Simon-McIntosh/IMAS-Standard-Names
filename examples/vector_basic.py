"""Vector standard name example.

Demonstrates creating a base vector with components and its implicit magnitude.
Highlights:
  * Components must exist (or be staged) as scalar entries.
  * Component names must follow <axis>_component_of_<vector> pattern.
  * Frame must be specified.
  * Magnitude standard name is conventional: magnitude_of_<vector> (optional to define explicitly).
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from contextlib import contextmanager
from imas_standard_names.repository import StandardNameRepository
from imas_standard_names.schema import create_standard_name


@contextmanager
def tmp_root():
    with tempfile.TemporaryDirectory(prefix="stdnames_vec_") as d:
        root = Path(d) / "standard_names" / "magnetic_field"
        root.mkdir(parents=True, exist_ok=True)
        yield root


def main():
    with tmp_root() as root:
        repo = StandardNameRepository(root)
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

        # Vector references components by axis token mapping
        vector = create_standard_name(
            {
                "name": "magnetic_field",
                "kind": "vector",
                "unit": "T",
                "frame": "cylindrical_r_tor_z",
                "components": {
                    "radial": "radial_component_of_magnetic_field",
                    "toroidal": "toroidal_component_of_magnetic_field",
                    "vertical": "vertical_component_of_magnetic_field",
                },
                "description": "Magnetic field vector (laboratory cylindrical frame).",
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
