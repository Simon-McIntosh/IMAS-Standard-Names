import asyncio

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.list import ListTool


def invoke(tool, *args, **kwargs):
    return asyncio.run(tool.list_standard_names(*args, **kwargs))


def test_list_standard_names_basic():
    repo = StandardNameCatalog()
    tool = ListTool(repo)
    result = invoke(tool)
    assert "names" in result
    assert "count" in result
    assert result["count"] == len(result["names"])
    assert result["count"] > 0
