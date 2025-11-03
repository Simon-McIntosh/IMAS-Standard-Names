"""Static helpers for standard-name parsing and composition.

These functions are intentionally hand-written to minimize churn in the
auto-generated file and to keep behavior clear and testable.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from imas_standard_names.grammar.constants import (
    BASE_SEGMENTS,
    EXCLUSIVE_SEGMENT_PAIRS,
    PREFIX_SEGMENTS,
    SEGMENT_PREFIX_TOKEN_MAP,
    SEGMENT_SUFFIX_TOKEN_MAP,
    SEGMENT_TEMPLATES,
    SEGMENT_TOKEN_MAP,
    SUFFIX_SEGMENTS,
    SUFFIX_SEGMENTS_REVERSED,
)

# Token pattern used by base and the overall name validation.
TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def value_of(value: Any) -> str:
    """Return the string value for an enum or bare string.

    Accepts StrEnum members or plain strings; falls back to ``str(value)``.
    """
    return value.value if hasattr(value, "value") else str(value)


def enum_values[E](enum_cls: type[E]) -> list[str]:
    """Return the allowed string values for a StrEnum type.

    Args:
        enum_cls: Enumeration type (StrEnum subclasses from grammar.types).

    Returns:
        List of string values from the enum.

    Example:
        >>> from imas_standard_names.grammar.model_types import Component
        >>> enum_values(Component)
        ['radial', 'poloidal', 'toroidal', ...]
    """
    return [e.value for e in enum_cls]  # type: ignore[attr-defined]


def coerce_enum[E](enum_cls: type[E], value: E | str | None) -> E | None:
    """Coerce a possibly-string value to an enum member.

    Accepts the enum member already, or its .value string. Returns None when
    value is None. Raises ValueError if the string doesn't match an allowed
    member.

    Args:
        enum_cls: Target enumeration type.
        value: Enum member, string value, or None.

    Returns:
        Enum member or None.

    Raises:
        ValueError: If string value doesn't match any enum member.

    Example:
        >>> from imas_standard_names.grammar.model_types import Component
        >>> coerce_enum(Component, "radial")
        <Component.RADIAL: 'radial'>
        >>> coerce_enum(Component, Component.RADIAL)
        <Component.RADIAL: 'radial'>
        >>> coerce_enum(Component, None)
        None
    """
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)  # type: ignore[call-arg]
        except ValueError as e:
            allowed = [e.value for e in enum_cls]  # type: ignore[attr-defined]
            raise ValueError(
                f"Invalid {enum_cls.__name__} token '{value}'. "
                f"Allowed values: {allowed}"
            ) from e
    raise TypeError(
        f"Expected {enum_cls.__name__}, str, or None; got {type(value).__name__}"
    )


def compose_standard_name(parts: Mapping[str, Any]) -> str:
    """Compose a standard name from parts.

    Expects keys matching the generated SEGMENT names. Unknown keys are ignored
    by callers who validate inputs upstream.
    The generated module will bind a thin wrapper to ensure the same signature
    when using the Pydantic model.
    """
    tokens: list[str] = []
    for segment in PREFIX_SEGMENTS:
        value = parts.get(segment)
        if value:
            template = SEGMENT_TEMPLATES.get(segment)
            token_value = value_of(value)
            # Apply template if present, otherwise use token directly
            if template:
                rendered = template.format(token=token_value)
            else:
                rendered = token_value
            tokens.append(rendered)

    # Handle base segments (geometric_base or physical_base)
    base_found = False
    for base_segment in BASE_SEGMENTS:
        base_value = parts.get(base_segment)
        if base_value:
            if base_found:
                raise ValueError(f"Cannot have multiple base segments: {BASE_SEGMENTS}")
            token_value = value_of(base_value)
            if not TOKEN_PATTERN.fullmatch(token_value):
                raise ValueError(
                    f"{base_segment} segment must match the canonical token pattern"
                )
            tokens.append(token_value)
            base_found = True

    if not base_found:
        raise ValueError(f"One of {BASE_SEGMENTS} must be set")

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

    # Parse prefixes greedily - at each position, find the longest match across
    # ALL unmatched segments, then consume it. This ensures poloidal_field_coil_
    # (device) is matched before poloidal_ (coordinate).
    # But we still respect ordering by only moving forward in the segment list.
    current_segment_idx = 0

    while current_segment_idx < len(PREFIX_SEGMENTS) and remaining:
        # Find the best match among segments from current position onward
        best_token = None
        best_length = 0
        best_segment = None
        best_segment_idx = current_segment_idx

        for idx in range(current_segment_idx, len(PREFIX_SEGMENTS)):
            segment = PREFIX_SEGMENTS[idx]
            if segment in values:
                # Already matched this segment
                continue

            template = SEGMENT_TEMPLATES.get(segment)
            for token in SEGMENT_PREFIX_TOKEN_MAP.get(segment, ()):
                # Apply template if present, otherwise use token directly
                if template:
                    rendered = template.format(token=token)
                else:
                    rendered = token
                prefix = rendered + "_"
                if remaining.startswith(prefix) and len(prefix) > best_length:
                    best_token = token
                    best_length = len(prefix)
                    best_segment = segment
                    best_segment_idx = idx

        if best_token is not None:
            # Apply the best match
            prefix_str = SEGMENT_TEMPLATES.get(best_segment)
            if prefix_str:
                prefix = prefix_str.format(token=best_token) + "_"
            else:
                prefix = best_token + "_"
            remaining = remaining[len(prefix) :]
            values[best_segment] = best_token
            # Move to the next segment position after the one we just matched
            current_segment_idx = best_segment_idx + 1
        else:
            # No match found, move to next segment
            current_segment_idx += 1

    if not remaining:
        raise ValueError("Missing base segment in name")

    # Determine which base segment type this is
    # Check if remaining matches any controlled geometric_base tokens
    base_assigned = False
    for base_segment in BASE_SEGMENTS:
        tokens = SEGMENT_TOKEN_MAP.get(base_segment, ())
        if tokens and remaining in tokens:
            values[base_segment] = remaining
            base_assigned = True
            break

    # If not in controlled vocabulary, assign to physical_base (open vocabulary)
    if not base_assigned:
        if "physical_base" in BASE_SEGMENTS:
            values["physical_base"] = remaining
        else:
            # Fallback for legacy grammar with single "base" segment
            values["base"] = remaining

    if "subject" in values and "component" not in values:
        # Get base token from whichever base segment was assigned
        base_token = None
        for base_segment in BASE_SEGMENTS:
            if base_segment in values:
                base_token = values[base_segment]
                break
        if not base_token and "base" in values:  # Legacy fallback
            base_token = values["base"]

        if base_token:
            component_tokens = SEGMENT_PREFIX_TOKEN_MAP.get("component", ())
            for token in component_tokens:
                if base_token.startswith(f"{token}_"):
                    msg = "Component must precede subject; use '<component>_<subject>_<base>'"
                    raise ValueError(msg)

    # Exclusivity checks for parsed output can be validated by model later, but we keep
    # this for parity with previous behavior.
    for left, right in EXCLUSIVE_SEGMENT_PAIRS:
        if values.get(left) and values.get(right):
            raise ValueError(f"Segments '{left}' and '{right}' cannot both be set")

    return values
