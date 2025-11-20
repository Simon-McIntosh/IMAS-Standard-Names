"""Service layer utilities: validation aggregation and row->model conversion."""

from __future__ import annotations

import json
import sqlite3

from pydantic import ValidationError

from .models import (
    StandardNameEntry,
    StandardNameMetadataEntry,
    StandardNameScalarEntry,
    StandardNameVectorEntry,
    create_standard_name_entry,
    load_standard_name_entry,
)
from .validation.semantic import run_semantic_checks
from .validation.structural import run_structural_checks


def validate_models(models: dict[str, StandardNameEntry]) -> list[str]:
    """Run structural + semantic validation returning list of issues."""
    return run_structural_checks(models) + run_semantic_checks(models)


def row_to_model(conn: sqlite3.Connection, row: sqlite3.Row) -> StandardNameEntry:
    """Convert database row to StandardNameEntry model.

    Uses model introspection to determine which fields to include based on
    the target model class for the given kind. This ensures metadata entries
    don't receive unit/provenance fields that are forbidden by their schema.

    Uses model_construct() fallback for invalid entries to ensure all entries
    load (allowing validation tools to report on them) without crashing server.
    """
    # Determine which fields to include based on kind
    kind_to_model_class = {
        "scalar": StandardNameScalarEntry,
        "vector": StandardNameVectorEntry,
        "metadata": StandardNameMetadataEntry,
    }
    ModelClass = kind_to_model_class.get(row["kind"], StandardNameScalarEntry)
    model_fields = set(ModelClass.model_fields.keys())

    # Build data dict with only fields that exist in the target model
    data = {
        "name": row["name"],
        "kind": row["kind"],
        "status": row["status"],
        "description": row["description"],
        "documentation": row["documentation"] or "",
        "validity_domain": row["validity_domain"] or "",
        "deprecates": row["deprecates"] or "",
        "superseded_by": row["superseded_by"] or "",
    }

    # Conditionally include unit if model has this field
    if "unit" in model_fields:
        data["unit"] = row["unit"] or ""

    # Conditionally include provenance if model has this field
    if "provenance" in model_fields:
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

    # Tags and links are common to all models
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

    try:
        return create_standard_name_entry(data)
    except ValidationError:
        # Entry is invalid but load it anyway using load_standard_name_entry
        # which bypasses validation. This allows server to start and
        # validation tools to report all issues.
        return load_standard_name_entry(data)


__all__ = ["validate_models", "row_to_model"]
