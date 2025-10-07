import pytest

from imas_standard_names.models import (
    StandardNameScalarEntry,
    create_standard_name_entry,
)


def test_expression_provenance(expression_scalar_data):
    sn = create_standard_name_entry(expression_scalar_data)
    assert isinstance(sn, StandardNameScalarEntry)
    assert sn.provenance is not None
    assert sn.provenance.mode == "expression"
    assert "electron_temperature" in sn.provenance.dependencies


def test_expression_invalid_dependency(expression_scalar_data):
    bad = expression_scalar_data | {
        "provenance": expression_scalar_data["provenance"]
        | {"dependencies": ["BadName"]}
    }
    with pytest.raises((ValueError, KeyError, TypeError)):
        create_standard_name_entry(bad)
