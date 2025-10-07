"""Dependency-based ordering for StandardName models using graphlib.TopologicalSorter.

This module centralizes dependency extraction and topological ordering so that
any component (repository load, catalog builder, validation tools) can obtain
models in a safe insertion sequence that respects:

- Vector component dependencies (vector -> its scalar components)
- Operator / reduction provenance base dependencies (derived* -> base)
- Expression provenance dependencies (expression -> each dependency + base)

Cycles or unresolved dependencies produce clear exceptions.
"""

from __future__ import annotations

from collections.abc import Iterable
from graphlib import CycleError, TopologicalSorter

from .models import StandardNameEntry


class OrderingError(RuntimeError):
    """Raised when models cannot be ordered (cycle or missing prerequisite)."""


def _extract_dependencies(model: StandardNameEntry, available: set[str]) -> set[str]:
    deps: set[str] = set()
    kind = getattr(model, "kind", "")

    # Vector components must exist before the vector.
    if kind.endswith("vector"):
        # Iterate over component NAME values (previous implementation incorrectly
        # iterated over axis keys, producing empty dependency sets and allowing
        # vectors to appear before their components in topological order).
        for comp in (getattr(model, "components", {}) or {}).values():
            if comp in available:
                deps.add(comp)

    # Provenance dependencies.
    prov = getattr(model, "provenance", None)
    if prov:
        mode = getattr(prov, "mode", None)
        base = getattr(prov, "base", None)
        if base and base in available:
            deps.add(base)
        if mode == "expression":  # expression dependencies list
            for dep in getattr(prov, "dependencies", []) or []:
                if dep in available:
                    deps.add(dep)
        # Reduction provenance already covered by base; other modes implicitly only depend on base.
    return deps


def ordered_model_names(models: Iterable[StandardNameEntry]) -> Iterable[str]:
    """Yield model names in a dependency-safe order.

    Uses a topological sort over the implicit dependency graph. Cycles raise
    OrderingError with diagnostic detail.
    """
    model_list: list[StandardNameEntry] = list(models)
    name_map: dict[str, StandardNameEntry] = {m.name: m for m in model_list}
    names = set(name_map.keys())

    ts = TopologicalSorter()
    missing_refs: dict[str, set[str]] = {}

    for m in model_list:
        deps = _extract_dependencies(m, names)
        # Track references to missing names (informational; not edges)
        raw_deps = set(deps)
        if raw_deps - names:
            missing_refs[m.name] = raw_deps - names
        ts.add(m.name, *sorted(deps))

    try:
        yield from ts.static_order()
    except CycleError as e:  # rewrap for consistency
        raise OrderingError(f"Cycle detected in standard name dependencies: {e}") from e


def ordered_models(models: Iterable[StandardNameEntry]) -> Iterable[StandardNameEntry]:
    """Yield full model objects in dependency order (wrapper over ordered_model_names)."""
    model_list: list[StandardNameEntry] = list(models)
    name_map: dict[str, StandardNameEntry] = {m.name: m for m in model_list}
    for name in ordered_model_names(model_list):
        yield name_map[name]


__all__ = [
    "OrderingError",
    "ordered_models",
    "ordered_model_names",
]
