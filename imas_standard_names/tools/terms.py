"""Read-only MCP access to governed grammar terms."""

from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.grammar.terms import (
    fetch_standard_terms,
    search_standard_terms,
)
from imas_standard_names.tools.base import Tool


class StandardTermsTool(Tool):
    """Fetch and search normative compositional grammar terms."""

    @property
    def tool_name(self) -> str:
        return "standard_terms"

    @mcp_tool(
        description=(
            "Fetch exact governed grammar terms by canonical token or display "
            "abbreviation. These are compositional terms, not complete standard names."
        )
    )
    async def fetch_standard_terms(
        self, tokens: list[str] | str, ctx: Context | None = None
    ) -> dict:
        """Return exact term records and explicitly report missing inputs."""
        requested = [tokens] if isinstance(tokens, str) else tokens
        terms = fetch_standard_terms(requested)
        matched = {
            value.casefold()
            for term in terms
            for value in (term.token, *term.abbreviations)
        }
        return {
            "terms": [term.model_dump(mode="json") for term in terms],
            "missing": [
                token for token in requested if token.casefold() not in matched
            ],
        }

    @mcp_tool(
        description=(
            "Search governed grammar terms by token, normative definition, or "
            "display abbreviation, optionally restricted to a grammar segment."
        )
    )
    async def search_standard_terms(
        self,
        query: str,
        segment: str | None = None,
        limit: int = 25,
        ctx: Context | None = None,
    ) -> dict:
        """Return matching terms in deterministic token order."""
        if limit < 1 or limit > 100:
            return {
                "error": "ValueError",
                "message": "limit must be between 1 and 100",
                "examples": [{"query": "LCFS"}, {"query": "transport barrier"}],
            }
        terms = search_standard_terms(query, segment=segment)
        return {
            "terms": [term.model_dump(mode="json") for term in terms[:limit]],
            "total": len(terms),
        }
