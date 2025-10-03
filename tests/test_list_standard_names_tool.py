import asyncio

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.overview import OverviewTool


def invoke(tool, *args, **kwargs):
    return asyncio.run(tool.list_standard_names(*args, **kwargs))


def test_list_standard_names_scopes_basic():
    repo = StandardNameCatalog()
    tool = OverviewTool(repo)
    # all scope
    all_payload = invoke(tool)
    assert (
        "counts" in all_payload
        and "universal_set" in all_payload
        and "committed" in all_payload
    )
    committed = invoke(tool, scope="committed")
    assert "counts" in committed and "committed" in committed
    staged = invoke(tool, scope="staged")
    assert "staged" in staged and "counts" in staged

    # specific empty scopes should still include counts
    for sc in ["new", "modified", "renamed", "deleted"]:
        payload = invoke(tool, scope=sc)
        assert "counts" in payload


def test_list_standard_names_with_edits(tmp_path):
    # Use a temp copy of the packaged catalog root by initializing repo with pattern
    repo = StandardNameCatalog()  # baseline packaged data
    tool = OverviewTool(repo)
    # Attach an EditCatalog to tool to surface diff classification
    tool.edit_catalog = EditCatalog(repo)  # type: ignore[attr-defined]

    # Pick an existing name to modify (first committed name)
    committed_names = invoke(tool)["committed"]
    target = committed_names[0]
    model = repo.get(target)
    # modify description
    modified_model_dict = model.model_dump()  # type: ignore[attr-defined]
    modified_model_dict["description"] = (
        modified_model_dict["description"] + " (modified)"
    )
    tool.edit_catalog.modify(target, modified_model_dict)  # type: ignore[attr-defined]

    # add new name (simple scalar)
    new_name_data = {
        "name": "temporary_test_scalar_name",
        "kind": "scalar",
        "description": "Temporary test scalar",
        "status": "draft",
        "unit": "",
    }
    tool.edit_catalog.add(new_name_data)  # type: ignore[attr-defined]

    # rename the newly added name to another
    renamed_data = new_name_data.copy()
    renamed_data["name"] = "renamed_temporary_test_scalar_name"
    tool.edit_catalog.rename("temporary_test_scalar_name", renamed_data)  # type: ignore[attr-defined]

    # delete an existing different name (skip the modified one)
    if len(committed_names) > 1:
        tool.edit_catalog.delete(committed_names[1])  # type: ignore[attr-defined]

    diff_all = invoke(tool)
    staged = diff_all["staged"]
    # Ensure classifications present
    assert (
        "new" in staged
        and "modified" in staged
        and "rename_map" in staged
        and "deleted" in staged
    )
    # Validate scope filtered variants still include counts
    for sc in ["new", "modified", "renamed", "deleted", "staged"]:
        payload = invoke(tool, scope=sc)
        assert "counts" in payload

    # Integrity: counts totals match lengths
    counts = diff_all["counts"]
    assert counts["new_count"] == len(staged["new"])
    assert counts["modified_count"] == len(staged["modified"])
    assert counts["renamed_count"] == len(
        staged["rename_map"]
    )  # rename map dict mapping
    assert counts["deleted_count"] == len(staged["deleted"])
    assert counts["staged_total_count"] == (
        counts["new_count"]
        + counts["modified_count"]
        + counts["renamed_count"]
        + counts["deleted_count"]
    )
