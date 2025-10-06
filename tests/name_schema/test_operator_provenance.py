import pytest

from imas_standard_names.schema import (
    StandardNameDerivedScalar,
    StandardNameDerivedVector,
    create_standard_name,
)


def test_divergence_scalar(operator_scalar_data):
    sn = create_standard_name(operator_scalar_data)
    assert isinstance(sn, StandardNameDerivedScalar)
    assert sn.provenance.operators == ["divergence"]


def test_gradient_vector(gradient_vector_data):
    sn = create_standard_name(gradient_vector_data)
    assert isinstance(sn, StandardNameDerivedVector)
    assert sn.provenance.operators == ["gradient"]


def test_operator_chain_mismatch(operator_scalar_data):
    # Tamper with operators list to force mismatch
    bad = operator_scalar_data | {
        "provenance": operator_scalar_data["provenance"] | {"operators": ["gradient"]}
    }
    with pytest.raises((ValueError, KeyError, TypeError)):
        create_standard_name(bad)


def test_operator_base_mismatch(operator_scalar_data):
    bad = operator_scalar_data | {
        "provenance": operator_scalar_data["provenance"]
        | {"base": "electron_temperature"}
    }
    with pytest.raises((ValueError, KeyError, TypeError)):
        create_standard_name(bad)


def test_operator_id_mismatch(operator_scalar_data):
    bad = operator_scalar_data | {
        "provenance": operator_scalar_data["provenance"] | {"operator_id": "curl"}
    }
    with pytest.raises((ValueError, KeyError, TypeError)):
        create_standard_name(bad)
