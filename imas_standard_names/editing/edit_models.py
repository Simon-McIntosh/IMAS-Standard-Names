"""Edit operation input and result models.

This module defines the discriminated union of edit input variants
(`ApplyInput`) and the corresponding result variants (`ApplyResult`).
These are transport-agnostic shapes consumed by the editing layer
(`EditRepository`).

Previously named `inputs.py`; renamed to clarify it also bundles
result models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, model_validator

from ..models import StandardNameEntry, create_standard_name_entry

if TYPE_CHECKING:
    pass


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
    dry_run: bool = False

    @model_validator(mode="after")
    def _check_model(self):  # type: ignore[no-untyped-def]
        # Pure rename only: any attempt to supply a model should be rejected at parse layer.
        return self


class DeleteInput(BaseModel):
    action: Literal["delete"]
    name: str
    dry_run: bool = False


class BatchDeleteInput(BaseModel):
    action: Literal["batch_delete"]
    names: list[str]
    dry_run: bool = False


class BatchInput(BaseModel):
    action: Literal["batch"]
    operations: list[ModifyInput | RenameInput | DeleteInput]
    mode: Literal["continue", "atomic"] = "continue"
    dry_run: bool = False
    resume_from_index: int = 0


ApplyInput = Annotated[
    ModifyInput | RenameInput | DeleteInput | BatchDeleteInput | BatchInput,
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
            "action": "modify",
            "name": "example_name",
            "model": {"name": "example_name", "kind": "scalar", "description": "desc"},
        },
        {"action": "rename", "old_name": "old", "new_name": "new"},
        {"action": "rename", "old_name": "a", "new_name": "b", "dry_run": True},
        {"action": "delete", "name": "obsolete_name"},
        {"action": "delete", "name": "test_name", "dry_run": True},
        {
            "action": "batch_delete",
            "names": ["old_entry_1", "old_entry_2", "old_entry_3"],
        },
        {"action": "batch_delete", "names": ["test_1", "test_2"], "dry_run": True},
        {
            "action": "batch",
            "mode": "continue",
            "dry_run": False,
            "operations": [
                {
                    "action": "modify",
                    "name": "base_quantity",
                    "model": {
                        "name": "base_quantity",
                        "kind": "scalar",
                        "description": "Updated description",
                    },
                },
                {
                    "action": "delete",
                    "name": "obsolete_quantity",
                },
            ],
        },
    ]


class BaseResult(BaseModel):
    """Marker base class for edit results (lean schema)."""

    pass


class ErrorDetail(BaseModel):
    """Structured error information for failed operations."""

    type: str
    message: str
    field: str | None = None
    suggestion: str | None = None


class OperationResult(BaseModel):
    """Result of a single operation in a batch."""

    index: int
    operation: ModifyInput | RenameInput | DeleteInput
    status: Literal["success", "error", "skipped"]
    result: Any = None  # Will be ApplyResult, use Any to avoid circular reference
    error: ErrorDetail | None = None


class BatchResult(BaseResult):
    """Result of batch operation with summary and per-operation details."""

    action: Literal["batch"] = "batch"
    summary: dict
    results: list[OperationResult]
    last_successful_index: int | None = None


class ModifyResult(BaseResult):
    action: Literal["modify"] = "modify"
    old_model: StandardNameEntry
    new_model: StandardNameEntry


class RenameResult(BaseResult):
    action: Literal["rename"] = "rename"
    old_name: str
    new_name: str
    dry_run: bool = False
    dependencies: list[str] | None = None  # Entries that depend on the old name


class DeleteResult(BaseResult):
    action: Literal["delete"] = "delete"
    old_model: StandardNameEntry | None
    existed: bool
    dry_run: bool = False
    dependencies: list[str] | None = None  # Entries that depend on this one


class BatchDeleteResult(BaseResult):
    action: Literal["batch_delete"] = "batch_delete"
    summary: dict
    results: list[tuple[str, bool, list[str] | None]]  # (name, existed, dependencies)
    dry_run: bool = False


ApplyResult = (
    ModifyResult | RenameResult | DeleteResult | BatchDeleteResult | BatchResult
)


def result_from_dict(d: dict) -> ApplyResult:
    """Reconstruct a result model from a dictionary (lean schema only)."""
    action = d.get("action")
    if action == "modify":
        return ModifyResult(**d)
    if action == "rename":
        return RenameResult(**d)
    if action == "delete":
        return DeleteResult(**d)
    if action == "batch_delete":
        return BatchDeleteResult(**d)
    if action == "batch":
        return BatchResult(**d)
    raise ValueError(f"Unknown action in result: {action!r}")


__all__ = [
    # inputs
    "ModifyInput",
    "RenameInput",
    "DeleteInput",
    "BatchDeleteInput",
    "BatchInput",
    "ApplyInput",
    "parse_apply_input",
    "apply_input_schema",
    "example_inputs",
    # results
    "BaseResult",
    "ModifyResult",
    "RenameResult",
    "DeleteResult",
    "BatchDeleteResult",
    "ErrorDetail",
    "OperationResult",
    "BatchResult",
    "ApplyResult",
    "result_from_dict",
]
