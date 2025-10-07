"""Edit operation input and result models.

This module defines the discriminated union of edit input variants
(`ApplyInput`) and the corresponding result variants (`ApplyResult`).
These are transport-agnostic shapes consumed by the editing layer
(`EditRepository`).

Previously named `inputs.py`; renamed to clarify it also bundles
result models.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, model_validator

from ..models import StandardNameEntry, create_standard_name_entry


class AddInput(BaseModel):
    action: Literal["add"]
    model: StandardNameEntry


class ModifyInput(BaseModel):
    action: Literal["modify"]
    name: str
    model: StandardNameEntry

    @model_validator(mode="after")
    def _check_name(self):  # type: ignore[no-untyped-def]
        if self.model.name != self.name:  # type: ignore[attr-defined]
            raise ValueError("modify: model.name must match name; use rename")
        return self


class RenameInput(BaseModel):
    action: Literal["rename"]
    old_name: str
    new_name: str

    @model_validator(mode="after")
    def _check_model(self):  # type: ignore[no-untyped-def]
        # Pure rename only: any attempt to supply a model should be rejected at parse layer.
        return self


class DeleteInput(BaseModel):
    action: Literal["delete"]
    name: str


ApplyInput = Annotated[
    AddInput | ModifyInput | RenameInput | DeleteInput,
    Field(discriminator="action"),
]

_ApplyInputAdapter = TypeAdapter(ApplyInput)


def parse_apply_input(data: dict) -> ApplyInput:
    """Coerce raw dict payload (with optional model dict) into an ApplyInput."""
    if isinstance(data, dict) and "model" in data and isinstance(data["model"], dict):
        try:
            data = {**data, "model": create_standard_name_entry(data["model"])}
        except Exception as e:  # pragma: no cover
            raise ValueError(f"Invalid model payload: {e}") from e
    return _ApplyInputAdapter.validate_python(data)


def apply_input_schema() -> dict:
    return _ApplyInputAdapter.json_schema()


def example_inputs() -> list[dict]:
    return [
        {
            "action": "add",
            "model": {"name": "example_name", "kind": "scalar", "description": "desc"},
        },
        {
            "action": "modify",
            "name": "example_name",
            "model": {"name": "example_name", "kind": "scalar", "description": "desc"},
        },
        {"action": "rename", "old_name": "old", "new_name": "new"},
        {"action": "rename", "old_name": "a", "new_name": "b"},
        {"action": "delete", "name": "obsolete_name"},
    ]


class BaseResult(BaseModel):
    """Marker base class for edit results (lean schema)."""

    pass


class AddResult(BaseResult):
    action: Literal["add"] = "add"
    model: StandardNameEntry


class ModifyResult(BaseResult):
    action: Literal["modify"] = "modify"
    old_model: StandardNameEntry
    new_model: StandardNameEntry


class RenameResult(BaseResult):
    action: Literal["rename"] = "rename"
    old_name: str
    new_name: str


class DeleteResult(BaseResult):
    action: Literal["delete"] = "delete"
    old_model: StandardNameEntry | None
    existed: bool


ApplyResult = AddResult | ModifyResult | RenameResult | DeleteResult


def result_from_dict(d: dict) -> ApplyResult:
    """Reconstruct a result model from a dictionary (lean schema only)."""
    action = d.get("action")
    if action == "add":
        return AddResult(**d)
    if action == "modify":
        return ModifyResult(**d)
    if action == "rename":
        return RenameResult(**d)
    if action == "delete":
        return DeleteResult(**d)
    raise ValueError(f"Unknown action in result: {action!r}")


__all__ = [
    # inputs
    "AddInput",
    "ModifyInput",
    "RenameInput",
    "DeleteInput",
    "ApplyInput",
    "parse_apply_input",
    "apply_input_schema",
    "example_inputs",
    # results
    "BaseResult",
    "AddResult",
    "ModifyResult",
    "RenameResult",
    "DeleteResult",
    "ApplyResult",
    "result_from_dict",
]
