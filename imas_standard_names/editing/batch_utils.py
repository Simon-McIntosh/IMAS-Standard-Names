"""Utility functions for batch editing operations.

This module provides dependency ordering and batch processing helpers.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .edit_models import AddInput, DeleteInput, ModifyInput, RenameInput


def extract_name_from_operation(
    op: AddInput | ModifyInput | RenameInput | DeleteInput,
) -> str | None:
    """Extract the primary name being created/modified by an operation."""
    if op.action == "add":
        return op.model.name  # type: ignore[attr-defined]
    elif op.action == "modify":
        return op.name
    elif op.action == "rename":
        return op.new_name
    elif op.action == "delete":
        return None  # Deletion doesn't create a name
    return None


def extract_dependencies(
    op: AddInput | ModifyInput | RenameInput | DeleteInput,
) -> list[str]:
    """Extract names that this operation depends on (from provenance)."""
    dependencies = []

    if op.action in ("add", "modify"):
        model = op.model  # type: ignore[attr-defined]
        provenance = getattr(model, "provenance", None)

        if provenance is not None:
            mode = getattr(provenance, "mode", None)

            if mode == "operator":
                base = getattr(provenance, "base", None)
                if base:
                    dependencies.append(base)
            elif mode == "reduction":
                base = getattr(provenance, "base", None)
                if base:
                    dependencies.append(base)
            elif mode == "expression":
                deps = getattr(provenance, "dependencies", [])
                dependencies.extend(deps)

    return dependencies


def topological_sort_operations(
    operations: list[AddInput | ModifyInput | RenameInput | DeleteInput],
) -> tuple[list[AddInput | ModifyInput | RenameInput | DeleteInput], list[str]]:
    """
    Topologically sort operations based on provenance dependencies.

    Returns:
        (sorted_operations, circular_dependency_errors)

    If circular dependencies are detected, returns the original order and
    a list of error messages describing the cycles.
    """
    # Build dependency graph
    graph: dict[int, list[int]] = defaultdict(list)
    in_degree: dict[int, int] = {}
    name_to_indices: dict[str, list[int]] = defaultdict(list)

    # Map names to operation indices
    for i, op in enumerate(operations):
        name = extract_name_from_operation(op)
        if name:
            name_to_indices[name].append(i)
        in_degree[i] = 0

    # Build edges: if op[i] depends on name produced by op[j], add edge j -> i
    for i, op in enumerate(operations):
        deps = extract_dependencies(op)
        for dep_name in deps:
            if dep_name in name_to_indices:
                for j in name_to_indices[dep_name]:
                    if j != i:  # Avoid self-loops
                        graph[j].append(i)
                        in_degree[i] = in_degree.get(i, 0) + 1

    # Kahn's algorithm for topological sort
    queue = deque([i for i in range(len(operations)) if in_degree[i] == 0])
    sorted_indices = []

    while queue:
        idx = queue.popleft()
        sorted_indices.append(idx)

        for neighbor in graph[idx]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check for cycles
    if len(sorted_indices) != len(operations):
        # Circular dependency detected
        errors = []
        unprocessed = set(range(len(operations))) - set(sorted_indices)

        for idx in unprocessed:
            op = operations[idx]
            name = extract_name_from_operation(op)
            deps = extract_dependencies(op)
            if name and deps:
                errors.append(
                    f"Circular dependency detected: '{name}' depends on {deps}, "
                    f"but one or more dependencies also depend on '{name}'"
                )

        return operations, errors

    # Return sorted operations
    sorted_ops = [operations[i] for i in sorted_indices]
    return sorted_ops, []


__all__ = [
    "extract_name_from_operation",
    "extract_dependencies",
    "topological_sort_operations",
]
