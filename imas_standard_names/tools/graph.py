"""MCP tools for local catalog graph traversal (plan 41)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.graph.local_graph import (
    ALL_EDGE_TYPES,
    build_catalog_graph,
    get_ancestors,
    get_descendants,
    get_neighbours,
    shortest_path,
)
from imas_standard_names.tools.base import Tool

logger = logging.getLogger(__name__)


_EDGE_CONVENTIONS = (
    "Edge directions: HAS_ARGUMENT points wrapped->arg; HAS_ERROR points "
    "base->variant (base-centric); HAS_PREDECESSOR points entry->deprecates; "
    "HAS_SUCCESSOR points entry->superseded_by; REFERENCES points "
    "entry->link target."
)


class LocalGraphTool(Tool):
    """Graph-traversal MCP tools backed by the plan-40 per-domain YAML."""

    def __init__(self, catalog_root: str | None):
        super().__init__()
        self._catalog_root = catalog_root
        self._graph: Any | None = None
        self._build_error: str | None = None

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "standard-name-graph"

    # ------------------------------------------------------------------
    # Graph lifecycle
    # ------------------------------------------------------------------
    def _ensure_graph(self) -> Any | None:
        if self._graph is not None or self._build_error is not None:
            return self._graph
        if self._catalog_root is None:
            self._build_error = "catalog_root not configured"
            return None
        try:
            self._graph = build_catalog_graph(Path(self._catalog_root))
        except Exception as exc:  # pragma: no cover - defensive
            self._build_error = str(exc)
            logger.warning("Failed to build local catalog graph: %s", exc)
            return None
        n_nodes = self._graph.number_of_nodes()
        n_edges = self._graph.number_of_edges()
        n_stubs = sum(
            1 for _, attrs in self._graph.nodes(data=True) if attrs.get("stub")
        )
        logger.info(
            "Local graph built: %d nodes (%d stubs), %d edges",
            n_nodes,
            n_stubs,
            n_edges,
        )
        return self._graph

    def _edge_types_filter(self, edge_types: list[str] | None) -> set[str] | None:
        if not edge_types:
            return None
        unknown = set(edge_types) - ALL_EDGE_TYPES
        if unknown:
            raise ValueError(
                f"Unknown edge_types {sorted(unknown)}; valid: {sorted(ALL_EDGE_TYPES)}"
            )
        return set(edge_types)

    # ------------------------------------------------------------------
    # MCP tools
    # ------------------------------------------------------------------
    @mcp_tool(
        description=(
            "Return immediate neighbours of a standard name in the local "
            "catalog graph. Edge types: HAS_ARGUMENT, HAS_ERROR, "
            "HAS_PREDECESSOR, HAS_SUCCESSOR, REFERENCES. " + _EDGE_CONVENTIONS
        )
    )
    async def get_standard_name_neighbours(
        self,
        name: str,
        edge_types: list[str] | None = None,
        direction: str = "both",
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """List neighbours of ``name`` with edge metadata."""

        g = self._ensure_graph()
        if g is None:
            return {"error": self._build_error or "graph unavailable", "results": []}
        if direction not in ("out", "in", "both"):
            return {
                "error": f"direction must be 'out', 'in', or 'both' (got {direction!r})",
                "results": [],
            }
        types = self._edge_types_filter(edge_types)
        neighbours = get_neighbours(g, name, edge_types=types, direction=direction)  # type: ignore[arg-type]
        return {
            "name": name,
            "direction": direction,
            "edge_types": sorted(types) if types else sorted(ALL_EDGE_TYPES),
            "results": neighbours,
            "count": len(neighbours),
        }

    @mcp_tool(
        description=(
            "Return ancestors of a standard name via the ordering-parent "
            "closure: outgoing HAS_ARGUMENT edges (the thing this entry "
            "wraps, transitively) and incoming HAS_ERROR edges (the base "
            "for which this entry is an uncertainty variant). " + _EDGE_CONVENTIONS
        )
    )
    async def get_standard_name_ancestors(
        self,
        name: str,
        edge_types: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Return the ancestor closure for ``name``."""

        g = self._ensure_graph()
        if g is None:
            return {"error": self._build_error or "graph unavailable", "ancestors": []}
        types = self._edge_types_filter(edge_types)
        ancestors = get_ancestors(g, name, edge_types=types)
        return {
            "name": name,
            "ancestors": ancestors,
            "count": len(ancestors),
        }

    @mcp_tool(
        description=(
            "Return descendants of a standard name via the ordering-child "
            "closure: incoming HAS_ARGUMENT edges (things that wrap this "
            "entry) and outgoing HAS_ERROR edges (uncertainty variants). "
            + _EDGE_CONVENTIONS
        )
    )
    async def get_standard_name_descendants(
        self,
        name: str,
        edge_types: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Return the descendant closure for ``name``."""

        g = self._ensure_graph()
        if g is None:
            return {
                "error": self._build_error or "graph unavailable",
                "descendants": [],
            }
        types = self._edge_types_filter(edge_types)
        descendants = get_descendants(g, name, edge_types=types)
        return {
            "name": name,
            "descendants": descendants,
            "count": len(descendants),
        }

    @mcp_tool(
        description=(
            "Return the shortest directed path between two standard names, "
            "traversing all structural edges. Each element is "
            "{name, edge_type_in}; the source has edge_type_in=None. "
            + _EDGE_CONVENTIONS
        )
    )
    async def shortest_standard_name_path(
        self,
        source: str,
        target: str,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Return the shortest path from ``source`` to ``target``."""

        g = self._ensure_graph()
        if g is None:
            return {"error": self._build_error or "graph unavailable", "path": []}
        path = shortest_path(g, source, target)
        return {
            "source": source,
            "target": target,
            "path": path,
            "hops": max(0, len(path) - 1),
        }


__all__ = ["LocalGraphTool"]
