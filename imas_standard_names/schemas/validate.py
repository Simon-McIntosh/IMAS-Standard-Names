"""Validate arbitrary data against the StandardNameEntry contract."""

from pydantic import TypeAdapter, ValidationError

from imas_standard_names.models import StandardNameEntry

_ENTRY_ADAPTER = TypeAdapter(StandardNameEntry)


def validate_against_schema(data: dict) -> list[str]:
    """Validate an arbitrary dictionary against the ``StandardNameEntry`` schema.

    Uses Pydantic's ``TypeAdapter`` to perform full model validation,
    including discriminated-union dispatch and all field-level constraints.
    This function does not require a catalog database or any file I/O.

    Args:
        data: A dictionary representing a candidate standard name entry.
            Must include at least a ``kind`` discriminator field.

    Returns:
        A list of human-readable validation error strings.  An empty list
        means the data is valid.
    """
    try:
        _ENTRY_ADAPTER.validate_python(data)
        return []
    except ValidationError as exc:
        return [
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            if err.get("loc")
            else err["msg"]
            for err in exc.errors()
        ]
