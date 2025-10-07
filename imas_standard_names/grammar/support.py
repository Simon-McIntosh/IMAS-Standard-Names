"""Static helpers for standard-name parsing and composition.

These functions are intentionally hand-written to minimize churn in the
auto-generated file and to keep behavior clear and testable.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

# Token pattern used by base and the overall name validation.
TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def value_of(value: Any) -> str:
    """Return the string value for an enum or bare string.

    Accepts StrEnum members or plain strings; falls back to ``str(value)``.
    """
    return value.value if hasattr(value, "value") else str(value)


def compose_standard_name(parts: Mapping[str, Any]) -> str:
    """Compose a standard name from parts.

    Expects keys matching the generated SEGMENT names. Unknown keys are ignored
    by callers who validate inputs upstream.
    The generated module will bind a thin wrapper to ensure the same signature
    when using the Pydantic model.
    """
    from imas_standard_names.grammar.types import (  # local import to avoid cycle
        PREFIX_SEGMENTS,
        SEGMENT_TEMPLATES,
        SUFFIX_SEGMENTS,
    )

    tokens: list[str] = []
    for segment in PREFIX_SEGMENTS:
        value = parts.get(segment)
        if value:
            tokens.append(value_of(value))
    base = parts.get("base")
    if not isinstance(base, str) or not TOKEN_PATTERN.fullmatch(base):
        raise ValueError("base segment must match the canonical token pattern")
    tokens.append(base)

    for segment in SUFFIX_SEGMENTS:
        value = parts.get(segment)
        if not value:
            continue
        template = SEGMENT_TEMPLATES.get(segment)
        token_value = value_of(value)
        rendered = template.format(token=token_value) if template else token_value
        tokens.append(rendered)

    return "_".join(tokens)


def parse_standard_name(name: str) -> dict[str, str]:
    """Parse a standard name into a dict of parts.

    Returns a dict with keys matching segment identifiers.
    """
    from imas_standard_names.grammar.types import (  # local import to avoid cycle
        EXCLUSIVE_SEGMENT_PAIRS,
        PREFIX_SEGMENTS,
        SEGMENT_PREFIX_TOKEN_MAP,
        SEGMENT_SUFFIX_TOKEN_MAP,
        SEGMENT_TEMPLATES,
        SUFFIX_SEGMENTS_REVERSED,
    )

    if not TOKEN_PATTERN.fullmatch(name):
        raise ValueError("Invalid token characters in name")

    remaining = name
    values: dict[str, str] = {}

    for segment in SUFFIX_SEGMENTS_REVERSED:
        template = SEGMENT_TEMPLATES.get(segment)
        if not template:
            continue
        for token in SEGMENT_SUFFIX_TOKEN_MAP.get(segment, ()):
            rendered = template.format(token=token)
            suffix = "_" + rendered
            if remaining.endswith(suffix):
                remaining = remaining[: -len(suffix)]
                values[segment] = token
                break

    for segment in PREFIX_SEGMENTS:
        for token in SEGMENT_PREFIX_TOKEN_MAP.get(segment, ()):
            prefix = token + "_"
            if remaining.startswith(prefix):
                remaining = remaining[len(prefix) :]
                values[segment] = token
                break

    if not remaining:
        raise ValueError("Missing base segment in name")
    values["base"] = remaining

    if "subject" in values and "component" not in values:
        base_token = values["base"]
        component_tokens = SEGMENT_PREFIX_TOKEN_MAP.get("component", ())
        for token in component_tokens:
            if base_token.startswith(f"{token}_"):
                msg = (
                    "Component must precede subject; use '<component>_<subject>_<base>'"
                )
                raise ValueError(msg)

    # Exclusivity checks for parsed output can be validated by model later, but we keep
    # this for parity with previous behavior.
    for left, right in EXCLUSIVE_SEGMENT_PAIRS:
        if values.get(left) and values.get(right):
            raise ValueError(f"Segments '{left}' and '{right}' cannot both be set")

    return values
