from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.overview import OverviewTool


def test_overview_structure():
    repo = StandardNameCatalog()
    tool = OverviewTool(repo)
    # call directly (sync wrapper of async not needed if we just run loop)
    import asyncio

    result = asyncio.run(tool.get_standard_names_overview())

    assert "total_standard_names" in result and result["total_standard_names"] == len(
        repo
    )
    assert result["total_standard_names"] > 0

    expected_kinds = {"scalar", "vector"}
    assert set(result["standard_names_by_kind"]) == expected_kinds  # all kinds present
    assert (
        sum(result["standard_names_by_kind"].values()) == result["total_standard_names"]
    )

    expected_status = {"draft", "active", "deprecated", "superseded"}
    assert set(result["standard_names_by_status"]) == expected_status
    assert (
        sum(result["standard_names_by_status"].values())
        == result["total_standard_names"]
    )

    # Unit mapping: at least one unit key and dimensionless may appear
    assert "standard_names_by_unit" in result and isinstance(
        result["standard_names_by_unit"], dict
    )
    # Basic sanity: total entries >= sum of units? (Multiple entries share units)
    assert (
        sum(result["standard_names_by_unit"].values()) >= result["total_standard_names"]
    )

    # Tags aggregation present (may be empty dict)
    assert "standard_names_by_tag" in result
    assert isinstance(result["standard_names_by_tag"], dict)

    # Version present
    assert "version" in result and isinstance(result["version"], str)
