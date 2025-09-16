import pytest
from imas_standard_names.schema import create_standard_name


def test_component_scalar_requires_axis_and_parent():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "scalar",
                "name": "r_component_of_plasma_velocity",
                "description": "A component missing parent",
                "unit": "m/s",
                "status": "active",
                "axis": "r",
                # parent_vector omitted
            }
        )
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "scalar",
                "name": "r_component_of_plasma_velocity",
                "description": "A component missing axis",
                "unit": "m/s",
                "status": "active",
                "parent_vector": "plasma_velocity",
            }
        )


def test_component_scalar_prefix_enforced():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "scalar",
                "name": "wrong_component_of_plasma_velocity",
                "description": "Bad prefix",
                "unit": "m/s",
                "status": "draft",
                "axis": "r",
                "parent_vector": "plasma_velocity",
            }
        )


def test_valid_component_scalar():
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "r_component_of_plasma_velocity",
            "description": "Radial component",
            "unit": "m/s",
            "status": "active",
            "axis": "r",
            "parent_vector": "plasma_velocity",
        }
    )
    assert sn.axis == "r" and sn.parent_vector == "plasma_velocity"


def test_vector_invalid_component_prefix():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "vector",
                "name": "magnetic_field",
                "description": "B field",
                "unit": "T",
                "status": "active",
                "frame": "cylindrical_r_tor_z",
                "components": {
                    "r": "radial_component_of_magnetic_field",
                    "tor": "tor_component_of_magnetic_field",
                },
            }
        )


def test_vector_invalid_axis_token():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "vector",
                "name": "flow",
                "description": "Flow",
                "unit": "m/s",
                "status": "active",
                "frame": "cylindrical_r_tor_z",
                "components": {
                    "R": "R_component_of_flow",
                    "tor": "tor_component_of_flow",
                },
            }
        )


def test_valid_vector_with_magnitude():
    sn = create_standard_name(
        {
            "kind": "vector",
            "name": "plasma_velocity",
            "description": "Velocity",
            "unit": "m/s",
            "status": "active",
            "frame": "cylindrical_r_tor_z",
            "components": {
                "r": "r_component_of_plasma_velocity",
                "tor": "tor_component_of_plasma_velocity",
            },
            "magnitude": "magnitude_of_plasma_velocity",
        }
    )
    assert sn.magnitude == "magnitude_of_plasma_velocity"
