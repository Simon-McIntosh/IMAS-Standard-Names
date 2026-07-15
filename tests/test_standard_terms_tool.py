import asyncio

from imas_standard_names.tools.terms import StandardTermsTool


def test_fetch_standard_terms_reports_missing_tokens() -> None:
    result = asyncio.run(StandardTermsTool().fetch_standard_terms(["LCFS", "missing"]))
    assert result["terms"][0]["token"] == "last_closed_flux_surface"
    assert result["missing"] == ["missing"]


def test_search_standard_terms_validates_limit() -> None:
    result = asyncio.run(StandardTermsTool().search_standard_terms("barrier", limit=0))
    assert result["error"] == "ValueError"
