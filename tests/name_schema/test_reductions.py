import pytest

from imas_standard_names.schema import (
    StandardNameDerivedScalar,
    create_standard_name,
)


def test_time_average_reduction_scalar():
    sn = create_standard_name(
        {
            "kind": "derived_scalar",
            "name": "time_average_of_electron_temperature",
            "description": "Time average",
            "unit": "eV",
            "status": "active",
            "provenance": {
                "mode": "reduction",
                "reduction": "mean",
                "domain": "time",
                "base": "electron_temperature",
            },
        }
    )
    assert isinstance(sn, StandardNameDerivedScalar)
    assert sn.provenance.reduction == "mean"


def test_rms_reduction_scalar():
    sn = create_standard_name(
        {
            "kind": "derived_scalar",
            "name": "root_mean_square_of_electron_temperature",
            "description": "RMS",
            "unit": "eV",
            "status": "active",
            "provenance": {
                "mode": "reduction",
                "reduction": "rms",
                "domain": "none",
                "base": "electron_temperature",
            },
        }
    )
    assert sn.provenance.reduction == "rms"


def test_volume_integral_scalar():
    sn = create_standard_name(
        {
            "kind": "derived_scalar",
            "name": "volume_integral_of_pressure",
            "description": "Volume integral",
            "unit": "Pa.m^3",
            "status": "active",
            "provenance": {
                "mode": "reduction",
                "reduction": "integral",
                "domain": "volume",
                "base": "pressure",
            },
        }
    )
    assert sn.provenance.domain == "volume"


def test_magnitude_vector():
    sn = create_standard_name(
        {
            "kind": "derived_scalar",
            "name": "magnitude_of_plasma_velocity",
            "description": "Speed",
            "unit": "m.s^-1",
            "status": "active",
            "provenance": {
                "mode": "reduction",
                "reduction": "magnitude",
                "domain": "none",
                "base": "plasma_velocity",
            },
        }
    )
    assert sn.provenance.reduction == "magnitude"


def test_reduction_mismatch_error():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "derived_scalar",
                "name": "time_average_of_electron_temperature",
                "description": "Mismatch",
                "unit": "eV",
                "status": "active",
                "provenance": {
                    "mode": "reduction",
                    "reduction": "rms",  # mismatch with name prefix
                    "domain": "time",
                    "base": "electron_temperature",
                },
            }
        )


def test_domain_mismatch_error():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "derived_scalar",
                "name": "time_average_of_electron_temperature",
                "description": "Mismatch domain",
                "unit": "eV",
                "status": "active",
                "provenance": {
                    "mode": "reduction",
                    "reduction": "mean",
                    "domain": "volume",  # mismatch
                    "base": "electron_temperature",
                },
            }
        )


def test_base_mismatch_error():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "derived_scalar",
                "name": "time_average_of_electron_temperature",
                "description": "Base mismatch",
                "unit": "eV",
                "status": "active",
                "provenance": {
                    "mode": "reduction",
                    "reduction": "mean",
                    "domain": "time",
                    "base": "ion_temperature",  # mismatch
                },
            }
        )
