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
            "Apply a single catalog mutation (add, modify, rename, delete) to the "
            "Standard Names catalog. Input accepts a discriminated union with 'action' key. "
            "Returns typed result variant or structured error with schema + examples."
        )
    )
    async def edit_standard_name(self, payload: dict, ctx: Context | None = None):  # type: ignore[no-untyped-def]
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
