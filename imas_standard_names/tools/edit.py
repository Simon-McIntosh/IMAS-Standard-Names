from fastmcp import Context

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.editing.edit_models import (
    ApplyInput,
    ApplyResult,
    apply_input_schema,
    example_inputs,
    parse_apply_input,
)
from imas_standard_names.tools.base import BaseTool


class CatalogTool(BaseTool):
    """Tool exposing catalog edit operations via the unified apply API.
    Successful calls return the structured ApplyResult model (dict-serializable
    via model_dump by the framework). Errors return an envelope containing:
        error: string error type (exception class name)
        message: human-readable detail
        schema: JSON schema for ApplyInput union
        examples: example input payloads
    """

    def __init__(self, catalog, edit_catalog: EditCatalog | None = None):  # type: ignore[no-untyped-def]
        super().__init__(catalog)
        self.edit_catalog = edit_catalog or EditCatalog(catalog)

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "edit_standard_names"

    @mcp_tool(
        description=(
            "Modify, rename, or delete existing catalog entries. "
            "Use this tool to update existing standard name entries. "
            "For creating new entries, use create_standard_names instead. "
            "Supported actions: "
            "- modify: Update an existing entry's fields (name must match) "
            "- rename: Change an entry's name (use dry_run to see dependencies) "
            "- delete: Remove an entry (use dry_run to see dependencies) "
            "- batch_delete: Remove multiple entries at once "
            "- batch: Execute multiple operations in sequence "
            "All changes are kept in-memory (pending) until write_standard_names is called. "
            "Returns structured result with operation details or error with schema + examples. "
            "Typical workflow: (1) fetch_standard_names to get current entry, "
            "(2) edit_standard_name with desired action, "
            "(3) list_standard_names scope='pending' to review, (4) write_standard_names to persist."
        )
    )
    async def edit_standard_names(self, payload: dict, ctx: Context | None = None):  # type: ignore[no-untyped-def]
        try:
            # Parse first to surface validation errors consistently
            apply_input: ApplyInput = parse_apply_input(payload)
            result: ApplyResult = self.edit_catalog.apply(apply_input)
            return result.model_dump()
        except Exception as e:  # broad to ensure schema always returned
            return {
                "error": type(e).__name__,
                "message": str(e),
                "schema": apply_input_schema(),
                "examples": example_inputs(),
            }
