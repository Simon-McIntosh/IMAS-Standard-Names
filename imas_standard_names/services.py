"""Service layer utilities: validation aggregation and row->model conversion."""

from __future__ import annotations

from typing import Dict, List
import json
import sqlite3

from .schema import create_standard_name, StandardName
from .validation.structural import run_structural_checks
from .validation.semantic import run_semantic_checks


def validate_models(models: Dict[str, StandardName]) -> List[str]:
    """Run structural + semantic validation returning list of issues."""
    return run_structural_checks(models) + run_semantic_checks(models)


def row_to_model(conn: sqlite3.Connection, row: sqlite3.Row) -> StandardName:
    data = {
        "name": row["name"],
        "kind": row["kind"],
        "status": row["status"],
        "unit": row["unit"] or "",
        "description": row["description"],
        "documentation": row["documentation"] or "",
        "validity_domain": row["validity_domain"] or "",
        "deprecates": row["deprecates"] or "",
        "superseded_by": row["superseded_by"] or "",
    }
    if row["kind"].endswith("vector"):
        comps = conn.execute(
            "SELECT axis, component_name FROM vector_component WHERE vector_name=?",
            (row["name"],),
        ).fetchall()
        data["components"] = {c[0]: c[1] for c in comps}
    op = conn.execute(
        "SELECT operator_chain, base, operator_id FROM provenance_operator WHERE name=?",
        (row["name"],),
    ).fetchone()
    red = conn.execute(
        "SELECT reduction, domain, base FROM provenance_reduction WHERE name=?",
        (row["name"],),
    ).fetchone()
    expr = conn.execute(
        "SELECT expression FROM provenance_expression WHERE name=?", (row["name"],)
    ).fetchone()
    if op:
        data["provenance"] = {
            "mode": "operator",
            "operators": json.loads(op[0]),
            "base": op[1],
            "operator_id": op[2],
        }
    elif red:
        data["provenance"] = {
            "mode": "reduction",
            "reduction": red[0],
            "domain": red[1],
            "base": red[2],
        }
    elif expr:
        deps = [
            r[0]
            for r in conn.execute(
                "SELECT dependency FROM provenance_expression_dependency WHERE name=?",
                (row["name"],),
            ).fetchall()
        ]
        data["provenance"] = {
            "mode": "expression",
            "expression": expr[0],
            "dependencies": deps,
        }
    tags = [
        r[0]
        for r in conn.execute(
            "SELECT tag FROM tag WHERE name=?", (row["name"],)
        ).fetchall()
    ]
    if tags:
        data["tags"] = tags
    links = [
        r[0]
        for r in conn.execute(
            "SELECT link FROM link WHERE name=?", (row["name"],)
        ).fetchall()
    ]
    if links:
        data["links"] = links
    return create_standard_name(data)


__all__ = ["validate_models", "row_to_model"]
