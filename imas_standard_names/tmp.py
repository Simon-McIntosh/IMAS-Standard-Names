from imas_standard_names.repository import StandardNameRepository
from imas_standard_names.schema import create_standard_name

repo = StandardNameRepository()

ion_density = create_standard_name(
    {
        "name": "ion_density",
        "kind": "scalar",
        "unit": "m^-3",
        "description": "Ion number density.",
        "status": "draft",
    }
)

# uow.add(ion_density)
