import pytest

from imas_standard_names.models import create_standard_name_entry


def test_component_scalar_now_minimal():
    # Scalar components no longer require explicit axis/parent_vector fields.
    # Validation only enforces vector component naming indirectly via vector definitions.
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "r_component_of_plasma_velocity",
            "description": "Radial component",
            "unit": "m.s^-1",
            "status": "active",
        }
    )
    assert sn.name.startswith("r_component_of_")


def test_vector_invalid_component_prefix():
    with pytest.raises(ValueError):
        create_standard_name_entry(
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
        create_standard_name_entry(
            {
                "kind": "vector",
                "name": "flow",
                "description": "Flow",
                "unit": "m.s^-1",
                "status": "active",
                "frame": "cylindrical_r_tor_z",
                "components": {
                    "R": "R_component_of_flow",
                    "tor": "tor_component_of_flow",
                },
            }
        )


def test_valid_vector_with_magnitude():
    sn = create_standard_name_entry(
        {
            "kind": "vector",
            "name": "plasma_velocity",
            "description": "Velocity",
            "unit": "m.s^-1",
            "status": "active",
        }
    )
    # Magnitude is a computed property on vector models
    assert sn.magnitude == "magnitude_of_plasma_velocity"
