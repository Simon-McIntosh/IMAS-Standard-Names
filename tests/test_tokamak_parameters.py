"""Tests for tokamak parameters database and tool."""

import pytest

from imas_standard_names.tokamak_parameters import TokamakParametersDB
from imas_standard_names.tools.tokamak_parameters import TokamakParametersTool


def test_load_iter_parameters():
    """Test loading ITER parameters."""
    db = TokamakParametersDB()
    params = db.get("ITER")

    assert params.machine == "ITER"
    assert params.geometry.major_radius.value == 6.2
    assert params.geometry.minor_radius.value == 2.0
    assert params.physics.plasma_current.value == 15


def test_list_machines():
    """Test listing available machines."""
    db = TokamakParametersDB()
    machines = db.list_machines()

    assert "iter" in machines
    assert "jet" in machines
    assert len(machines) >= 8


def test_get_many_machines():
    """Test loading multiple machines."""
    db = TokamakParametersDB()
    params_dict = db.get_many(["iter", "jet", "diii-d"])

    assert len(params_dict) == 3
    assert "iter" in params_dict
    assert "jet" in params_dict
    assert "diii-d" in params_dict
    assert params_dict["iter"].machine == "ITER"


def test_get_all_machines():
    """Test loading all machines."""
    db = TokamakParametersDB()
    all_params = db.get_all()

    assert len(all_params) >= 8
    assert "iter" in all_params
    assert "jet" in all_params


def test_compute_statistics():
    """Test statistics computation across machines."""
    db = TokamakParametersDB()
    machines = ["iter", "jet", "diii-d"]
    stats = db.compute_statistics(machines)

    assert "geometry" in stats
    assert "physics" in stats
    assert "major_radius" in stats["geometry"]
    assert stats["geometry"]["major_radius"].machine_count == 3
    assert stats["geometry"]["major_radius"].min < stats["geometry"]["major_radius"].max
    assert stats["geometry"]["major_radius"].unit == "m"


def test_statistics_handles_missing_parameters():
    """Test that statistics handles optional parameters correctly."""
    db = TokamakParametersDB()
    # Some machines don't have fusion_power or fusion_gain
    machines = ["diii-d", "asdex-upgrade", "east"]
    stats = db.compute_statistics(machines)

    # These machines don't have fusion power/gain, so they shouldn't be in stats
    assert "fusion_power" not in stats["physics"]
    assert "fusion_gain" not in stats["physics"]

    # But they all have major_radius
    assert "major_radius" in stats["geometry"]
    assert stats["geometry"]["major_radius"].machine_count == 3


def test_machine_not_found():
    """Test error handling for unknown machine."""
    db = TokamakParametersDB()

    with pytest.raises(ValueError) as exc_info:
        db.get("UNKNOWN")

    assert "not found" in str(exc_info.value)
    assert "Available:" in str(exc_info.value)


def test_case_insensitive_machine_name():
    """Test that machine names are case insensitive."""
    db = TokamakParametersDB()

    params_lower = db.get("iter")
    params_upper = db.get("ITER")
    params_mixed = db.get("ItEr")

    assert params_lower.machine == "ITER"
    assert params_upper.machine == "ITER"
    assert params_mixed.machine == "ITER"


def test_caching():
    """Test that parameters are cached."""
    db = TokamakParametersDB()

    params1 = db.get("iter")
    params2 = db.get("iter")

    # Should be the same object due to caching
    assert params1 is params2


@pytest.mark.anyio
async def test_mcp_tool_single_machine():
    """Test MCP tool with single machine."""
    tool = TokamakParametersTool()
    result = await tool.get_tokamak_parameters("ITER")

    assert "geometry" in result
    assert result["geometry"]["major_radius"]["value"] == 6.2
    assert "statistics" not in result
    assert "catalog_version" in result


@pytest.mark.anyio
async def test_mcp_tool_multiple_machines():
    """Test MCP tool with multiple machines."""
    tool = TokamakParametersTool()
    result = await tool.get_tokamak_parameters("ITER JET DIII-D")

    assert "machines" in result
    assert "statistics" in result
    assert len(result["machines"]) == 3
    assert "geometry" in result["statistics"]
    assert "major_radius" in result["statistics"]["geometry"]
    assert result["machine_count"] == 3
    assert "catalog_version" in result


@pytest.mark.anyio
async def test_mcp_tool_all_machines():
    """Test MCP tool with 'all' parameter."""
    tool = TokamakParametersTool()
    result = await tool.get_tokamak_parameters("all")

    assert "machines" in result
    assert "statistics" in result
    assert result["machine_count"] >= 8
    assert "catalog_version" in result


@pytest.mark.anyio
async def test_mcp_tool_default_is_all():
    """Test MCP tool defaults to 'all' machines."""
    tool = TokamakParametersTool()
    result = await tool.get_tokamak_parameters()

    assert "machines" in result
    assert "statistics" in result
    assert result["machine_count"] >= 8


@pytest.mark.anyio
async def test_mcp_tool_not_found():
    """Test error handling for unknown machine."""
    tool = TokamakParametersTool()
    result = await tool.get_tokamak_parameters("UNKNOWN")

    assert result["error"] == "MachineNotFound"
    assert "available_machines" in result
    assert "usage" in result


@pytest.mark.anyio
async def test_mcp_tool_partial_invalid():
    """Test error when one machine in list is invalid."""
    tool = TokamakParametersTool()
    result = await tool.get_tokamak_parameters("ITER UNKNOWN JET")

    assert result["error"] == "MachineNotFound"
    assert "available_machines" in result


def test_all_machines_have_required_fields():
    """Test that all machine files have required fields."""
    db = TokamakParametersDB()
    machines = db.list_machines()

    for machine in machines:
        params = db.get(machine)

        # Check required top-level fields
        assert params.machine
        assert params.facility
        assert params.location
        assert params.operational_status in [
            "operational",
            "under_construction",
            "decommissioned",
        ]
        assert params.last_updated
        assert len(params.sources) > 0

        # Check required geometry fields
        assert params.geometry.major_radius
        assert params.geometry.minor_radius
        assert params.geometry.plasma_volume

        # Check required physics fields
        assert params.physics.toroidal_magnetic_field
        assert params.physics.plasma_current


def test_parameter_units():
    """Test that parameters have correct units."""
    db = TokamakParametersDB()
    params = db.get("iter")

    assert params.geometry.major_radius.unit == "m"
    assert params.geometry.minor_radius.unit == "m"
    assert params.geometry.plasma_volume.unit == "m^3"
    assert params.physics.toroidal_magnetic_field.unit == "T"
    assert params.physics.plasma_current.unit == "MA"


def test_statistics_values():
    """Test that statistics produce reasonable values."""
    db = TokamakParametersDB()
    machines = ["iter", "jet", "diii-d"]
    stats = db.compute_statistics(machines)

    major_radius_stats = stats["geometry"]["major_radius"]

    # ITER has R=6.2m, JET has R=2.96m, DIII-D has R=1.67m
    assert major_radius_stats.min == pytest.approx(1.67, rel=0.01)
    assert major_radius_stats.max == pytest.approx(6.2, rel=0.01)
    assert 1.67 <= major_radius_stats.mean <= 6.2
    assert 1.67 <= major_radius_stats.median <= 6.2
