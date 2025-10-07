"""
MCP tool for composing and parsing IMAS Standard Names in an LLM-friendly way.

This tool exposes:
  - name_compose: Named-parameter interface with enum-constrained
    fields (no nested dicts required) that returns the canonical name and
    the validated parts.
  - name_parse: Parse a canonical name back into structured
    parts using the same enum domain.
  - name_list_tokens: Enumerate valid tokens per segment so LLMs
    can reliably select from allowed values.

Notes:
  - geometry and position are mutually exclusive.
  - base must match the canonical token pattern: ^[a-z][a-z0-9_]*$.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

import imas_standard_names.grammar.model as grammar_model
import imas_standard_names.grammar.types as grammar_types
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import BaseTool


def _enum_values[
    E: (
        grammar_types.Component,
        grammar_types.Subject,
        grammar_types.Position,
        grammar_types.Process,
    )
](
    enum_cls: type[E],
) -> list[str]:
    """Return the allowed string values for a StrEnum type.

    Args:
        enum_cls: Enumeration type (StrEnum subclasses).

    Returns:
        List of string values.
    """

    return [e.value for e in enum_cls]


def _coerce_enum[
    E: (
        grammar_types.Component,
        grammar_types.Subject,
        grammar_types.Position,
        grammar_types.Process,
    )
](enum_cls: type[E], value: E | str | None) -> E | None:
    """Coerce a possibly-string value to an enum member.

    Accepts the enum member already, or its .value string. Returns None when
    value is None. Raises ValueError if the string doesn't match an allowed
    member.
    """

    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - defensive
            allowed = ", ".join(_enum_values(enum_cls))
            raise ValueError(f"Invalid value '{value}' (allowed: {allowed})") from exc
    msg = f"Expected {enum_cls.__name__} | str | None, got {type(value).__name__}"
    raise TypeError(msg)


class NamesTool(BaseTool):
    """Tool exposing friendly compose/parse helpers for standard names."""

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "standard-name-grammar"

    @mcp_tool(
        description=(
            "Compose a canonical IMAS standard name from named parameters. "
            "All parameters except 'base' are optional and constrained to "
            "enumerated values. geometry and position are mutually exclusive. "
            "Returns {'name', 'parts'} where parts is the validated compact dict."
        )
    )
    async def name_compose(
        self,
        base: str,
        component: grammar_types.Component | str | None = None,
        subject: grammar_types.Subject | str | None = None,
        geometry: grammar_types.Position | str | None = None,
        position: grammar_types.Position | str | None = None,
        process: grammar_types.Process | str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Build and validate a standard name.

        Parameters are tolerant of either enum members or their string values.
        Raises ValueError on invalid tokens or exclusivity violations.
        """

        comp = _coerce_enum(grammar_types.Component, component)
        subj = _coerce_enum(grammar_types.Subject, subject)
        geom = _coerce_enum(grammar_types.Position, geometry)
        pos = _coerce_enum(grammar_types.Position, position)
        proc = _coerce_enum(grammar_types.Process, process)

        model = grammar_model.StandardName(
            component=comp,
            subject=subj,
            base=base,
            geometry=geom,
            position=pos,
            process=proc,
        )
        name = model.compose()
        return {"name": name, "parts": model.model_dump_compact()}

    @mcp_tool(
        description=(
            "Parse a canonical IMAS standard name into structured parts. "
            "Returns {'name', 'parts'} where parts uses the same keys as in build."
        )
    )
    async def name_parse(self, name: str, ctx: Context | None = None) -> dict[str, Any]:
        model = grammar_model.parse_standard_name(name)
        return {"name": name, "parts": model.model_dump_compact()}

    @mcp_tool(
        description=(
            "List allowed tokens for each segment and interface rules. "
            "Returns {component, subject, position, process, notes}. "
            "Use to pick valid values before calling name_compose."
        )
    )
    async def name_list_tokens(self, ctx: Context | None = None) -> dict[str, Any]:
        return {
            "component": _enum_values(grammar_types.Component),
            "subject": _enum_values(grammar_types.Subject),
            "geometry": _enum_values(grammar_types.Position),
            "position": _enum_values(grammar_types.Position),
            "process": _enum_values(grammar_types.Process),
            "notes": [
                "geometry and position are mutually exclusive",
                "base must match ^[a-z][a-z0-9_]*$",
                "prefix order: component, subject, base; suffix order: geometry|position, process",
            ],
            "examples": [
                {
                    "call": "name_compose",
                    "args": {
                        "component": "radial",
                        "subject": "electron",
                        "base": "density",
                        "position": "magnetic_axis",
                        "process": "conduction",
                    },
                },
                {
                    "call": "name_compose",
                    "args": {"base": "temperature"},
                },
            ],
        }
