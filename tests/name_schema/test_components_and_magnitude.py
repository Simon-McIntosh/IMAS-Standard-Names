import pytest

from imas_standard_names.models import create_standard_name_entry


def test_component_scalar_now_minimal():
    # Scalar components are minimal entries.
    # Component relationships are inferred from naming patterns.
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "radial_component_of_plasma_velocity",
            "description": "Radial component",
            "documentation": "Radial component of plasma velocity.",
            "unit": "m.s^-1",
            "status": "active",
            "tags": ["fundamental"],
        }
    )
    assert sn.name.startswith("radial_component_of_")


def test_invalid_component_token_rejected():
    """Test that names with invalid component tokens are rejected by grammar validator."""
    with pytest.raises(
        ValueError,
        match="Token 'r' used with 'component_of' template is missing from Component vocabulary",
    ):
        create_standard_name_entry(
            {
                "kind": "scalar",
                "name": "r_component_of_plasma_velocity",
                "description": "Invalid radial component using 'r' instead of 'radial'",
                "documentation": "Test entry for grammar validation.",
                "unit": "m.s^-1",
                "status": "draft",
                "tags": ["fundamental"],
            }
        )

    # Test another invalid component token
    with pytest.raises(
        ValueError,
        match="Token 'tor' used with 'component_of' template is missing from Component vocabulary",
    ):
        create_standard_name_entry(
            {
                "kind": "scalar",
                "name": "tor_component_of_magnetic_field",
                "description": "Invalid toroidal component using 'tor' instead of 'toroidal'",
                "documentation": "Test entry for grammar validation.",
                "unit": "T",
                "status": "draft",
                "tags": ["fundamental"],
            }
        )


def test_valid_component_tokens_accepted():
    """Test that names with valid component tokens are accepted."""
    # Test valid radial component
    sn1 = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "radial_component_of_plasma_velocity",
            "description": "Valid radial component",
            "documentation": "Radial component of plasma velocity.",
            "unit": "m.s^-1",
            "status": "draft",
            "tags": ["fundamental"],
        }
    )
    assert sn1.name == "radial_component_of_plasma_velocity"

    # Test valid toroidal component
    sn2 = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "toroidal_component_of_magnetic_field",
            "description": "Valid toroidal component",
            "documentation": "Toroidal component of magnetic field.",
            "unit": "T",
            "status": "draft",
            "tags": ["fundamental"],
        }
    )
    assert sn2.name == "toroidal_component_of_magnetic_field"


def test_vector_invalid_component_prefix():
    with pytest.raises(ValueError):
        create_standard_name_entry(
            {
                "kind": "vector",
                "name": "magnetic_field",
                "description": "B field",
                "documentation": "Magnetic field vector.",
                "unit": "T",
                "status": "active",
                "tags": ["fundamental"],
                "frame": "cylindrical_r_tor_z",
                "components": {
                    "r": "radial_component_of_magnetic_field",
                    "toroidal": "toroidal_component_of_magnetic_field",
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
                "documentation": "Flow vector.",
                "unit": "m.s^-1",
                "status": "active",
                "tags": ["fundamental"],
                "frame": "cylindrical_r_tor_z",
                "components": {
                    "radial": "radial_component_of_flow",
                    "toroidal": "toroidal_component_of_flow",
                },
            }
        )


def test_valid_vector_with_magnitude():
    sn = create_standard_name_entry(
        {
            "kind": "vector",
            "name": "plasma_velocity",
            "description": "Velocity",
            "documentation": "Plasma velocity vector.",
            "unit": "m.s^-1",
            "status": "active",
            "tags": ["fundamental"],
        }
    )
    # Magnitude is a computed property on vector models
    assert sn.magnitude == "magnitude_of_plasma_velocity"
