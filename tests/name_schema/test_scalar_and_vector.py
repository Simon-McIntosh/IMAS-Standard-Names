import pytest
from imas_standard_names.schema import (
    create_standard_name,
    StandardNameScalar,
    StandardNameVector,
)


def test_scalar_creation(scalar_data):
    sn = create_standard_name(scalar_data)
    assert isinstance(sn, StandardNameScalar)
    assert sn.name == scalar_data["name"]
    assert sn.formatted_unit() != ""  # eV formatted


def test_vector_creation(vector_data):
    sn = create_standard_name(vector_data)
    assert isinstance(sn, StandardNameVector)
    assert sorted(sn.components.keys()) == ["r", "tor", "z"]
    assert sn.magnitude == "magnitude_of_plasma_velocity"


@pytest.mark.parametrize("bad_name", ["ElectronTemp", "1temp", "temp__double"])
def test_invalid_name_rejected(scalar_data, bad_name):
    data = scalar_data | {"name": bad_name}
    with pytest.raises(Exception):
        create_standard_name(data)


def test_dimensionless_unit_blank():
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "beta_pol",
            "description": "Dimensionless plasma beta",
            "unit": "1",
            "status": "active",
        }
    )
    assert sn.unit == ""  # normalized
    assert sn.is_dimensionless
