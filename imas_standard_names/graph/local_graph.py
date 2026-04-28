"""Lightweight NetworkX local graph over the per-domain catalog YAML.

This module consumes the plan-40 per-domain catalog layout and exposes a
minimal ``networkx.DiGraph`` plus traversal helpers.  It intentionally
mirrors the shipped imas-codex Neo4j edge schema so downstream consumers
(MCP tools, catalog-site renderer, external tooling) can answer
graph-shaped questions without a Neo4j instance.

Edge semantics (see plan 41 §1):

- ``HAS_ARGUMENT`` points from the *wrapped* entry to the argument name
  carried in ``arguments[].name``.  Unary operators emit one edge;
  binary operators emit two edges with ``role=a``/``role=b``.
  Projection operators carry ``axis`` + ``shape``.
- ``HAS_ERROR`` points from the *base* entry to each uncertainty
  variant declared under ``error_variants`` — direction is
  ``base → variant`` (base-centric, not variant-centric).
- ``HAS_PREDECESSOR`` points from an entry to the name it deprecates
  (``deprecates: <name>``).
- ``HAS_SUCCESSOR`` points from an entry to its replacement
  (``superseded_by: <name>``).
- ``REFERENCES`` points from an entry to each ``links: [name:<X>]``
  target.

Forward-reference targets (an edge target that is not itself an entry
in the catalog) are added as ``stub=True`` nodes to match the codex
Neo4j writer, which ``MERGE``s bare placeholders for forward-refs.

``DiGraph`` is chosen deliberately: the codex writer collapses duplicate
``(src, tgt, edge_type)`` tuples via ``MERGE``, so the shipped structural
graph is already a simple digraph.  Binary operators remain faithful
because their two edges have distinct targets.  The pathological
``ratio_of_X_to_X`` case collapses to a single edge — accepted, matches
Neo4j.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

try:  # pragma: no cover - import guard
    import networkx as nx
except ImportError:  # pragma: no cover - optional dependency
    nx = None  # type: ignore[assignment]


EdgeType = Literal[
    "HAS_ARGUMENT",
    "HAS_ERROR",
    "HAS_PREDECESSOR",
    "HAS_SUCCESSOR",
    "REFERENCES",
]


ALL_EDGE_TYPES: frozenset[str] = frozenset(
    {
        "HAS_ARGUMENT",
        "HAS_ERROR",
        "HAS_PREDECESSOR",
        "HAS_SUCCESSOR",
        "REFERENCES",
    }
)


_NODE_ATTR_KEYS: tuple[str, ...] = (
    "kind",
    "unit",
    "description",
    "documentation",
    "status",
    "tags",
    "cocos_transformation_type",
)


class LocalGraphError(RuntimeError):
    """Raised when the local graph cannot be built."""


def _require_networkx() -> None:
    if nx is None:  # pragma: no cover - dependency guard
        raise LocalGraphError(
            "networkx is required for the local graph; install the "
            "`graph-local` extra: pip install imas-standard-names[graph-local]"
        )


def _iter_yaml_files(catalog_root: Path) -> list[Path]:
    root = Path(catalog_root).expanduser().resolve()
    if not root.exists():
        return []
    standard_names_dir = root / "standard_names"
    search_root = standard_names_dir if standard_names_dir.exists() else root
    return sorted(list(search_root.rglob("*.yml")) + list(search_root.rglob("*.yaml")))


def _load_entries(catalog_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for yaml_file in _iter_yaml_files(catalog_root):
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        if data is None:
            continue
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "name" in data:
            items = [data]
        else:
            continue
        domain = yaml_file.stem
        for entry in items:
            if not (isinstance(entry, dict) and "name" in entry):
                continue
            entry.setdefault("_domain", domain)
            entries.append(entry)
    return entries


def _ensure_node(g: Any, name: str, **attrs: Any) -> None:
    if name not in g:
        g.add_node(name, stub=False, **attrs)
    else:
        # Upgrade an existing stub to a real node when attrs become known.
        if attrs:
            stub = g.nodes[name].get("stub", False)
            g.nodes[name].update(attrs)
            if stub and any(k in attrs for k in ("kind", "description")):
                g.nodes[name]["stub"] = False


def _ensure_stub(g: Any, name: str) -> None:
    if name not in g:
        g.add_node(name, stub=True)


def _add_edge(
    g: Any,
    src: str,
    tgt: str,
    edge_type: str,
    **props: Any,
) -> None:
    """Add a typed edge; collapses duplicate (src,tgt) keys like Neo4j MERGE."""
    g.add_edge(src, tgt, edge_type=edge_type, **props)


def _add_arguments_edges(g: Any, entry: dict[str, Any]) -> None:
    args = entry.get("arguments") or []
    if not args:
        return
    src = entry["name"]
    for arg in args:
        if isinstance(arg, str):
            target = arg
            props: dict[str, Any] = {}
        elif isinstance(arg, dict):
            target = arg.get("name")
            if not target:
                continue
            props = {k: v for k, v in arg.items() if k != "name" and v is not None}
        else:
            continue
        _ensure_stub(g, target)
        _add_edge(g, src, target, "HAS_ARGUMENT", **props)


def _add_error_edges(g: Any, entry: dict[str, Any]) -> None:
    evars = entry.get("error_variants")
    if not evars or not isinstance(evars, dict):
        return
    src = entry["name"]
    for error_type, target in evars.items():
        if not target:
            continue
        _ensure_stub(g, target)
        _add_edge(g, src, target, "HAS_ERROR", error_type=error_type)


def _add_scalar_edges(g: Any, entry: dict[str, Any]) -> None:
    src = entry["name"]
    deprecates = entry.get("deprecates")
    if deprecates:
        _ensure_stub(g, deprecates)
        _add_edge(g, src, deprecates, "HAS_PREDECESSOR")
    superseded_by = entry.get("superseded_by")
    if superseded_by:
        _ensure_stub(g, superseded_by)
        _add_edge(g, src, superseded_by, "HAS_SUCCESSOR")


def _add_link_edges(g: Any, entry: dict[str, Any]) -> None:
    links = entry.get("links") or []
    if not links:
        return
    src = entry["name"]
    for link in links:
        if not isinstance(link, str) or not link.startswith("name:"):
            continue
        target = link[len("name:") :].strip()
        if not target:
            continue
        _ensure_stub(g, target)
        _add_edge(g, src, target, "REFERENCES")


def build_catalog_graph(catalog_root: Path | str) -> Any:
    """Build a ``networkx.DiGraph`` over the per-domain catalog.

    Parameters
    ----------
    catalog_root
        Root of the catalog directory (the folder containing ``catalog.yml``
        or the ``standard_names/`` subtree).  Both layouts are accepted:
        callers may pass either the catalog root or the
        ``standard_names/`` directory directly.

    Returns
    -------
    networkx.DiGraph
        A directed graph with one node per catalog entry plus stub nodes
        for forward-referenced names that do not themselves appear as
        entries.  Every edge carries an ``edge_type`` attribute drawn from
        :data:`ALL_EDGE_TYPES` along with the per-edge property dict
        described in the module docstring.
    """

    _require_networkx()
    g = nx.DiGraph()  # type: ignore[union-attr]

    entries = _load_entries(Path(catalog_root))
    known_names = {e["name"] for e in entries}

    for entry in entries:
        attrs: dict[str, Any] = {"domain": entry.get("_domain", "")}
        for key in _NODE_ATTR_KEYS:
            if key in entry and entry[key] is not None:
                attrs[key] = entry[key]
        _ensure_node(g, entry["name"], **attrs)

    for entry in entries:
        _add_arguments_edges(g, entry)
        _add_error_edges(g, entry)
        _add_scalar_edges(g, entry)
        _add_link_edges(g, entry)

    # Finalize stub flag: any node not in the loaded entry set stays stubbed.
    for node in list(g.nodes):
        if node not in known_names:
            g.nodes[node]["stub"] = True

    return g


def _filter_edge_types(
    edge_types: set[str] | None,
) -> set[str]:
    if edge_types is None:
        return set(ALL_EDGE_TYPES)
    unknown = set(edge_types) - ALL_EDGE_TYPES
    if unknown:
        raise ValueError(
            f"Unknown edge_types {sorted(unknown)}; valid: {sorted(ALL_EDGE_TYPES)}"
        )
    return set(edge_types)


def get_neighbours(
    g: Any,
    name: str,
    edge_types: set[str] | None = None,
    direction: Literal["out", "in", "both"] = "both",
) -> list[dict[str, Any]]:
    """Return neighbours of ``name`` with edge metadata.

    Each result dict has ``neighbour``, ``edge_type``, ``direction``
    (``"out"`` or ``"in"``), and ``props`` (edge property dict minus
    ``edge_type``).
    """

    _require_networkx()
    if name not in g:
        return []
    types = _filter_edge_types(edge_types)
    results: list[dict[str, Any]] = []
    if direction in ("out", "both"):
        for _, tgt, data in g.out_edges(name, data=True):
            if data.get("edge_type") in types:
                props = {k: v for k, v in data.items() if k != "edge_type"}
                results.append(
                    {
                        "neighbour": tgt,
                        "edge_type": data["edge_type"],
                        "direction": "out",
                        "props": props,
                    }
                )
    if direction in ("in", "both"):
        for src, _, data in g.in_edges(name, data=True):
            if data.get("edge_type") in types:
                props = {k: v for k, v in data.items() if k != "edge_type"}
                results.append(
                    {
                        "neighbour": src,
                        "edge_type": data["edge_type"],
                        "direction": "in",
                        "props": props,
                    }
                )
    return results


def _ordering_parents(g: Any, name: str) -> list[tuple[str, str]]:
    """Return (parent, edge_type) pairs per the plan 41 ancestor rule.

    Ordering parents := HAS_ARGUMENT-outgoing (my args) ∪
    HAS_ERROR-incoming (the base I'm an uncertainty variant of).
    """

    pairs: list[tuple[str, str]] = []
    for _, tgt, data in g.out_edges(name, data=True):
        if data.get("edge_type") == "HAS_ARGUMENT":
            pairs.append((tgt, "HAS_ARGUMENT"))
    for src, _, data in g.in_edges(name, data=True):
        if data.get("edge_type") == "HAS_ERROR":
            pairs.append((src, "HAS_ERROR"))
    return pairs


def _ordering_children(g: Any, name: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for src, _, data in g.in_edges(name, data=True):
        if data.get("edge_type") == "HAS_ARGUMENT":
            pairs.append((src, "HAS_ARGUMENT"))
    for _, tgt, data in g.out_edges(name, data=True):
        if data.get("edge_type") == "HAS_ERROR":
            pairs.append((tgt, "HAS_ERROR"))
    return pairs


def get_ancestors(
    g: Any,
    name: str,
    edge_types: set[str] | None = None,
) -> list[str]:
    """Transitive ancestor closure via ordering-parent edges.

    An ancestor of ``x`` is a name reachable by repeatedly stepping:

    - outward along ``HAS_ARGUMENT`` (the thing ``x`` wraps, and so on);
    - inward along ``HAS_ERROR`` (the base ``x`` is an uncertainty
      variant of).

    If ``edge_types`` is provided, steps are restricted to those types.
    The source node ``name`` itself is excluded from the result.
    """

    _require_networkx()
    if name not in g:
        return []
    types = _filter_edge_types(edge_types)
    seen: set[str] = set()
    order: list[str] = []
    stack = [name]
    while stack:
        current = stack.pop()
        for parent, etype in _ordering_parents(g, current):
            if etype not in types:
                continue
            if parent in seen or parent == name:
                continue
            seen.add(parent)
            order.append(parent)
            stack.append(parent)
    return order


def get_descendants(
    g: Any,
    name: str,
    edge_types: set[str] | None = None,
) -> list[str]:
    """Transitive descendant closure via ordering-child edges.

    Inverse of :func:`get_ancestors` — steps inward along
    ``HAS_ARGUMENT`` (things that wrap me) and outward along
    ``HAS_ERROR`` (my uncertainty variants).
    """

    _require_networkx()
    if name not in g:
        return []
    types = _filter_edge_types(edge_types)
    seen: set[str] = set()
    order: list[str] = []
    stack = [name]
    while stack:
        current = stack.pop()
        for child, etype in _ordering_children(g, current):
            if etype not in types:
                continue
            if child in seen or child == name:
                continue
            seen.add(child)
            order.append(child)
            stack.append(child)
    return order


def shortest_path(g: Any, a: str, b: str) -> list[dict[str, Any]]:
    """Shortest directed path from ``a`` to ``b`` over all edge types.

    Returns ``list[dict]`` where each element is ``{name, edge_type_in}``.
    The first element has ``edge_type_in = None`` (the source node);
    each subsequent element records the edge type used to reach it
    from the previous hop.  Returns ``[]`` if no path exists or either
    node is absent.
    """

    _require_networkx()
    if a not in g or b not in g:
        return []
    try:
        node_path = nx.shortest_path(g, source=a, target=b)  # type: ignore[union-attr]
    except nx.NetworkXNoPath:  # type: ignore[union-attr]
        return []
    except nx.NodeNotFound:  # type: ignore[union-attr]
        return []
    hops: list[dict[str, Any]] = [{"name": node_path[0], "edge_type_in": None}]
    for prev, curr in zip(node_path[:-1], node_path[1:], strict=True):
        data = g.get_edge_data(prev, curr) or {}
        hops.append({"name": curr, "edge_type_in": data.get("edge_type")})
    return hops


__all__ = [
    "ALL_EDGE_TYPES",
    "EdgeType",
    "LocalGraphError",
    "build_catalog_graph",
    "get_ancestors",
    "get_descendants",
    "get_neighbours",
    "shortest_path",
]
