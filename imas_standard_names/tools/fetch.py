"""
Fetch tool for comprehensive standard name retrieval.

This tool provides full standard name entries with all metadata including:
- Complete descriptions and documentation
- Grammar component breakdown
- Provenance (derived_from, superseded_by, deprecates)
- Constraints, tags, and links

Similar to imas-dd-debug fetch_imas_paths but for standard names.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

import imas_standard_names.grammar.model as grammar_model
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.models import StandardNameEntry
from imas_standard_names.provenance import (
    ExpressionProvenance,
    OperatorProvenance,
    ReductionProvenance,
)
from imas_standard_names.tools.base import CatalogTool


class FetchTool(CatalogTool):
    """Tool for comprehensive standard name retrieval."""

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "standard-name-fetch"

    @mcp_tool(
        description=(
            "Retrieve full IMAS standard name entries with complete metadata. "
            "Accepts space-delimited string or list of names. "
            "Returns comprehensive information including description, documentation, "
            "grammar breakdown, provenance, constraints, and links. "
            "Use this when you already know the exact name(s) and need complete details/metadata. "
            "For discovery use search_standard_names; for listing all names use list_standard_names."
        )
    )
    async def fetch_standard_names(
        self,
        names: str | list[str],
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Retrieve full standard name entries with all metadata.

        Args:
            names: Space-delimited string or list of standard names to fetch.

        Returns:
            Dictionary with full entries array and summary statistics.
        """
        # Parse input - handle both string and list
        name_list = names.split() if isinstance(names, str) else names

        entries = []
        not_found = []

        for name in name_list:
            # Get full entry from repository
            entry = self.catalog.get(name)

            if entry:
                # Parse grammar components
                grammar_parts = None
                try:
                    parsed = grammar_model.parse_standard_name(name)
                    grammar_parts = parsed.model_dump_compact()
                except Exception:  # pragma: no cover - defensive
                    # Grammar parsing shouldn't fail for valid catalog entries
                    # but handle gracefully just in case
                    pass

                # Extract provenance/derivation info
                derived_from = self._get_derived_from(entry)

                # Build comprehensive response
                entry_dict = {
                    "name": name,
                    "description": entry.description,
                    "documentation": entry.documentation,
                    "status": entry.status,
                    "kind": entry.kind,
                    "validity_domain": entry.validity_domain,
                    "constraints": entry.constraints,
                    "grammar": grammar_parts,
                    "provenance": {
                        "superseded_by": entry.superseded_by,
                        "deprecates": entry.deprecates,
                        "derived_from": derived_from,
                    },
                    "tags": entry.tags,
                    "links": self._format_links(entry.links),
                }

                # Only include unit field for scalar and vector entries
                if entry.kind != "metadata":
                    entry_dict["unit"] = str(entry.unit)

                entries.append(entry_dict)
            else:
                not_found.append(name)

        # Build summary statistics
        summary = {
            "total_requested": len(name_list),
            "retrieved": len(entries),
            "not_found": len(not_found),
            "not_found_names": not_found,
        }

        return {"entries": entries, "summary": summary}

    def _format_links(self, links: list[str]) -> list[dict[str, str]]:
        """Format links with type discrimination.

        Args:
            links: List of link strings (URLs or internal references)

        Returns:
            List of link dicts with 'type' and appropriate key ('url' or 'name')
        """
        formatted = []
        for link in links:
            if link.startswith("name:"):
                # Internal standard name reference
                name_part = link[5:].strip()
                formatted.append({"type": "standard_name", "name": name_part})
            else:
                # External URL
                formatted.append({"type": "url", "url": link})
        return formatted

    def _get_derived_from(self, entry: StandardNameEntry) -> list[str]:
        """Extract derivation dependencies from entry.

        Args:
            entry: Standard name entry to extract dependencies from.

        Returns:
            List of standard name dependencies from provenance.
        """
        if not hasattr(entry, "provenance") or not entry.provenance:
            return []

        # Handle different provenance types
        if isinstance(entry.provenance, OperatorProvenance):
            # Operator provenance has a base
            return [entry.provenance.base]
        elif isinstance(entry.provenance, ExpressionProvenance):
            # Expression provenance has dependencies
            return entry.provenance.dependencies
        elif isinstance(entry.provenance, ReductionProvenance):
            # Reduction provenance has a base
            return [entry.provenance.base]

        return []
