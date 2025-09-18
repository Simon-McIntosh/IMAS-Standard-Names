"""Derived vector example (gradient operator).

Requirements:
  * Base scalar (electron_temperature) must exist.
  * Derived vector name: gradient_of_<scalar>.
  * Each component scalar must exist (axis_component_of_gradient_of_<scalar>). Stage them first.
  * Provenance operator chain lists 'gradient'; base points to original scalar.
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from contextlib import contextmanager
from imas_standard_names.repository import StandardNameRepository
from imas_standard_names.schema import create_standard_name

AXES = ["radial", "toroidal", "vertical"]


@contextmanager
def tmp_root():
    with tempfile.TemporaryDirectory(prefix="stdnames_dvector_") as d:
        root = Path(d) / "standard_names"
        root.mkdir(parents=True, exist_ok=True)
        yield root


def main():
    with tmp_root() as root:
        repo = StandardNameRepository(root)
        uow = repo.start_uow()

        # Base scalar
        uow.add(
            create_standard_name(
                {
                    "name": "electron_temperature",
                    "kind": "scalar",
                    "unit": "eV",
                    "description": "Electron temperature.",
                    "status": "draft",
                }
            )
        )

        # Component scalars of gradient (must precede derived vector insert)
        for axis in AXES:
            uow.add(
                create_standard_name(
                    {
                        "name": f"{axis}_component_of_gradient_of_electron_temperature",
                        "kind": "derived_scalar",
                        "unit": "eV.m^-1",
                        "description": f"{axis.capitalize()} component of gradient_of_electron_temperature.",
                        "status": "draft",
                        "provenance": {
                            "mode": "operator",
                            "operators": ["gradient"],
                            "base": "electron_temperature",
                            "operator_id": "gradient",
                        },
                    }
                )
            )

        derived_vec = create_standard_name(
            {
                "name": "gradient_of_electron_temperature",
                "kind": "derived_vector",
                "unit": "eV.m^-1",
                "frame": "cylindrical_r_tor_z",
                "components": {
                    "radial": "radial_component_of_gradient_of_electron_temperature",
                    "toroidal": "toroidal_component_of_gradient_of_electron_temperature",
                    "vertical": "vertical_component_of_gradient_of_electron_temperature",
                },
                "description": "Gradient of electron_temperature as a vector.",
                "status": "draft",
                "provenance": {
                    "mode": "operator",
                    "operators": ["gradient"],
                    "base": "electron_temperature",
                    "operator_id": "gradient",
                },
            }
        )
        uow.add(derived_vec)

        print(
            "Staged names (subset):",
            [n for n in repo.list_names() if "electron_temperature" in n][:6],
            "...",
        )
        uow.commit()
        print(
            "Committed. Derived vector exists?",
            repo.exists("gradient_of_electron_temperature"),
        )


if __name__ == "__main__":  # pragma: no cover
    main()
