"""
MCP tool for composing and parsing IMAS Standard Names in an LLM-friendly way.

This tool exposes:
  - compose_standard_name: Named-parameter interface with enum-constrained
    fields (no nested dicts required) that returns the canonical name and
    the validated parts.
  - parse_standard_name: Parse a canonical name back into structured
    parts using the same enum domain.

For vocabulary and grammar rules, use get_grammar_and_vocabulary tool.

Notes:
  - component and coordinate are mutually exclusive.
  - object and source are mutually exclusive.
  - geometry and position are mutually exclusive.
  - base must match the canonical token pattern: ^[a-z][a-z0-9_]*$.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

import imas_standard_names.grammar.model as grammar_model
import imas_standard_names.grammar.types as grammar_types
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.grammar.support import coerce_enum
from imas_standard_names.tools.base import Tool


class ComposeTool(Tool):
    """Tool for composing and parsing IMAS Standard Names.

    Use compose_standard_name to build validated names from parameters.
    Use parse_standard_name to deconstruct names into structured parts.
    """

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "compose"

    @mcp_tool(
        description=(
            "Compose a canonical IMAS standard name from named parameters. "
            "Either geometric_base or physical_base must be provided (mutually exclusive). "
            "All other parameters are optional and constrained to enumerated values. "
            "geometry and position are mutually exclusive. "
            "Returns {'name', 'parts'} where parts is the validated compact dict."
        )
    )
    async def compose_standard_name(
        self,
        geometric_base: grammar_types.GeometricBase | str | None = None,
        physical_base: str | None = None,
        component: grammar_types.Component | str | None = None,
        coordinate: grammar_types.Component | str | None = None,
        subject: grammar_types.Subject | str | None = None,
        device: grammar_types.Object | str | None = None,
        object: grammar_types.Object | str | None = None,
        geometry: grammar_types.Position | str | None = None,
        position: grammar_types.Position | str | None = None,
        process: grammar_types.Process | str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Build and validate a standard name.

        Parameters are tolerant of either enum members or their string values.
        Raises ValueError on invalid tokens or exclusivity violations.
        """

        geo_base = coerce_enum(grammar_types.GeometricBase, geometric_base)
        comp = coerce_enum(grammar_types.Component, component)
        coord = coerce_enum(grammar_types.Component, coordinate)
        subj = coerce_enum(grammar_types.Subject, subject)
        dev = coerce_enum(grammar_types.Object, device)
        obj = coerce_enum(grammar_types.Object, object)
        geom = coerce_enum(grammar_types.Position, geometry)
        pos = coerce_enum(grammar_types.Position, position)
        proc = coerce_enum(grammar_types.Process, process)

        model = grammar_model.StandardName(
            geometric_base=geo_base,
            physical_base=physical_base,
            component=comp,
            coordinate=coord,
            subject=subj,
            device=dev,
            object=obj,
            geometry=geom,
            position=pos,
            process=proc,
        )
        name = model.compose()
        return {"name": name, "parts": model.model_dump_compact()}

    @mcp_tool(
        description=(
            "Parse canonical IMAS standard name(s) into structured parts. "
            "Accepts space-delimited string or list of names for batch parsing. "
            "Parameter: 'name' (accepts single name string, space-delimited string, or list). "
            "Returns dict with 'entries' list for batch mode, or {name, parts} for single name."
        )
    )
    async def parse_standard_name(
        self, name: str | list[str], ctx: Context | None = None
    ) -> dict[str, Any]:
        # Normalize input to list
        if isinstance(name, str):
            name_list = name.split()
        else:
            name_list = name

        # Single name: backward compatible format
        if len(name_list) == 1:
            try:
                model = grammar_model.parse_standard_name(name_list[0])
                return {"name": name_list[0], "parts": model.model_dump_compact()}
            except Exception as e:
                return {
                    "name": name_list[0],
                    "parts": None,
                    "valid": False,
                    "error": str(e),
                }

        # Batch mode: parse all names
        results = []
        for name in name_list:
            try:
                model = grammar_model.parse_standard_name(name)
                results.append(
                    {
                        "name": name,
                        "parts": model.model_dump_compact(),
                        "valid": True,
                        "error": None,
                    }
                )
            except Exception as e:
                results.append(
                    {"name": name, "parts": None, "valid": False, "error": str(e)}
                )

        return {
            "entries": results,
            "summary": {
                "total": len(name_list),
                "valid": sum(1 for r in results if r["valid"]),
                "invalid": sum(1 for r in results if not r["valid"]),
            },
        }
