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
    BINARY_OPERATOR_CONNECTORS,
    BINARY_OPERATOR_TOKENS,
    DECOMPOSITION_TOKENS,
    EXCLUSIVE_SEGMENT_PAIRS,
    PREFIX_SEGMENTS,
    SEGMENT_PREFIX_TOKEN_MAP,
    SEGMENT_SUFFIX_TOKEN_MAP,
    SEGMENT_TEMPLATES,
    SEGMENT_TOKEN_MAP,
    SUFFIX_SEGMENTS,
    SUFFIX_SEGMENTS_REVERSED,
    TRANSFORMATION_TOKENS,
)

# Token pattern used by base and the overall name validation.
TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Sort transformation tokens longest-first for greedy matching
_TRANSFORMATION_TOKENS_SORTED = tuple(
    sorted(TRANSFORMATION_TOKENS, key=len, reverse=True)
)

# Sort decomposition tokens longest-first for greedy matching
_DECOMPOSITION_TOKENS_SORTED = tuple(
    sorted(DECOMPOSITION_TOKENS, key=len, reverse=True)
)

# Sort binary operator tokens longest-first for greedy matching
_BINARY_OPERATOR_TOKENS_SORTED = tuple(
    sorted(BINARY_OPERATOR_TOKENS, key=len, reverse=True)
)

# Prefix-only exclusive pairs (both sides in PREFIX_SEGMENTS)
_PREFIX_EXCLUSIVE_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (left, right)
    for left, right in EXCLUSIVE_SEGMENT_PAIRS
    if left in PREFIX_SEGMENTS and right in PREFIX_SEGMENTS
)


# ---------------------------------------------------------------------------
# Synonym rewrites: applied to raw name before parsing to canonicalize
# near-duplicate forms. Keys are literal substrings; values are replacements.
# Order matters: longer patterns are tried first.
# ---------------------------------------------------------------------------

SYNONYM_REWRITES: tuple[tuple[str, str], ...] = (
    # Longest patterns first
    ("_per_toroidal_mode_number", "_per_toroidal_mode"),
    ("_field_probe", "_magnetic_field_probe"),
    # Note: `over_` → `per_` is intentionally NOT a global rewrite because
    # `over_` appears in valid transformation tokens (maximum_over_flux_surface,
    # minimum_over_flux_surface) and decomposition tokens (m_over_n_equals_*).
    # Use validate_forbidden_patterns() to flag misuse case-by-case.
)


# ---------------------------------------------------------------------------
# Forbidden suffix patterns: names matching these raise ValidationError
# with a clear message directing the user to the canonical form.
# Each entry is (pattern, message, exclusion_substrings). The pattern is
# only flagged if NONE of the exclusion_substrings appear in the name.
# ---------------------------------------------------------------------------

FORBIDDEN_SUFFIX_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "_per_toroidal_mode_number",
        "Use '_per_toroidal_mode' instead of '_per_toroidal_mode_number'.",
        (),
    ),
)


def _is_prefix_exclusive_with(segment: str, prefix_matched: set[str]) -> bool:
    """Check if segment is exclusive with any already-matched prefix segment."""
    for left, right in _PREFIX_EXCLUSIVE_PAIRS:
        if segment == left and right in prefix_matched:
            return True
        if segment == right and left in prefix_matched:
            return True
    return False


def value_of(value: Any) -> str:
    """Return the string value for an enum or bare string.

    Accepts StrEnum members or plain strings; falls back to ``str(value)``.
    """
    return value.value if hasattr(value, "value") else str(value)


def normalize_standard_name(name: str) -> str:
    """Apply synonym rewrites to canonicalize a standard name.

    Rewrites known non-canonical forms to their canonical equivalents
    before parsing. For example, ``_per_toroidal_mode_number`` becomes
    ``_per_toroidal_mode``.

    Args:
        name: Raw standard name string.

    Returns:
        Canonicalized name with all synonym rewrites applied.
    """
    result = name
    for pattern, replacement in SYNONYM_REWRITES:
        result = result.replace(pattern, replacement)
    return result


def validate_forbidden_patterns(name: str) -> None:
    """Check a standard name for forbidden suffix patterns.

    Raises ValueError with a clear message directing the user to the
    canonical form if a forbidden pattern is detected.

    Args:
        name: Standard name string to validate.

    Raises:
        ValueError: If name contains a forbidden pattern.
    """
    for pattern, message, exclusions in FORBIDDEN_SUFFIX_PATTERNS:
        if pattern in name:
            # Skip if any exclusion substring is present (avoids false positives)
            if exclusions and any(excl in name for excl in exclusions):
                continue
            raise ValueError(
                f"Forbidden pattern '{pattern}' in name '{name}'. {message}"
            )


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
    binary_operator = parts.get("binary_operator")
    secondary_base = parts.get("secondary_base")
    transformation = parts.get("transformation")
    decomposition = parts.get("decomposition")

    # Binary operator mode: {operator}_{base1}_{connector}_{base2} [+ suffixes]
    if binary_operator:
        op_value = value_of(binary_operator)
        connector = BINARY_OPERATOR_CONNECTORS.get(op_value)
        if not connector:
            raise ValueError(
                f"Unknown binary operator '{op_value}'. "
                f"Allowed: {list(BINARY_OPERATOR_CONNECTORS)}"
            )

        base1 = parts.get("physical_base")
        if not base1:
            raise ValueError("binary_operator requires physical_base (first operand)")
        if not secondary_base:
            raise ValueError("binary_operator requires secondary_base (second operand)")

        base1_value = value_of(base1)
        base2_value = value_of(secondary_base)

        if not TOKEN_PATTERN.fullmatch(base1_value):
            raise ValueError(
                "physical_base segment must match the canonical token pattern"
            )
        if not TOKEN_PATTERN.fullmatch(base2_value):
            raise ValueError(
                "secondary_base segment must match the canonical token pattern"
            )

        # Validate operands don't contain the connector as a standalone word
        connector_sep = f"_{connector}_"
        if connector_sep in f"_{base1_value}_":
            raise ValueError(
                f"physical_base '{base1_value}' contains reserved connector "
                f"word '{connector}'"
            )
        if connector_sep in f"_{base2_value}_":
            raise ValueError(
                f"secondary_base '{base2_value}' contains reserved connector "
                f"word '{connector}'"
            )

        tokens = [f"{op_value}_{base1_value}_{connector}_{base2_value}"]

        # Append suffix segments
        for segment in SUFFIX_SEGMENTS:
            value = parts.get(segment)
            if not value:
                continue
            template = SEGMENT_TEMPLATES.get(segment)
            token_value = value_of(value)
            rendered = template.format(token=token_value) if template else token_value
            tokens.append(rendered)

        return "_".join(tokens)

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
            # Prepend transformation and/or decomposition if present (only for physical_base)
            if base_segment == "physical_base" and (transformation or decomposition):
                prefix_parts: list[str] = []
                if transformation:
                    prefix_parts.append(value_of(transformation))
                if decomposition:
                    prefix_parts.append(value_of(decomposition))
                prefix_parts.append(token_value)
                tokens.append("_".join(prefix_parts))
            else:
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

    Applies synonym rewrites to canonicalize near-duplicate forms before
    parsing. Returns a dict with keys matching segment identifiers.
    """
    if not TOKEN_PATTERN.fullmatch(name):
        raise ValueError("Invalid token characters in name")

    # Apply synonym rewrites for canonical forms
    remaining = normalize_standard_name(name)
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

    # Check for binary operator prefix (before regular prefix parsing)
    binary_parsed = _try_parse_binary_operator(remaining)
    if binary_parsed:
        values["binary_operator"] = binary_parsed["binary_operator"]
        values["physical_base"] = binary_parsed["physical_base"]
        values["secondary_base"] = binary_parsed["secondary_base"]

        # Exclusivity checks
        for left, right in EXCLUSIVE_SEGMENT_PAIRS:
            if values.get(left) and values.get(right):
                raise ValueError(f"Segments '{left}' and '{right}' cannot both be set")
        return values

    # Parse prefixes greedily - at each position, find the longest match across
    # ALL unmatched segments, then consume it. This ensures poloidal_field_coil_
    # (device) is matched before poloidal_ (coordinate).
    # But we still respect ordering by only moving forward in the segment list.
    current_segment_idx = 0
    prefix_matched: set[str] = set()

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
            if _is_prefix_exclusive_with(segment, prefix_matched):
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
            prefix_matched.add(best_segment)
            # Move to the next segment position after the one we just matched
            current_segment_idx = best_segment_idx + 1
        else:
            # No match found, move to next segment
            current_segment_idx += 1

    if not remaining:
        raise ValueError("Missing base segment in name")

    # Check for transformation prefix on the remaining base text
    transformation_parsed = _try_parse_transformation(remaining)
    if transformation_parsed:
        values["transformation"] = transformation_parsed["transformation"]
        remaining = transformation_parsed["physical_base"]

    # Check for decomposition prefix (innermost, closest to the base).
    # Exclusive with transformation — covered by a model validator.
    decomposition_parsed = _try_parse_decomposition(remaining)
    if decomposition_parsed:
        values["decomposition"] = decomposition_parsed["decomposition"]
        remaining = decomposition_parsed["physical_base"]

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


def _try_parse_transformation(remaining: str) -> dict[str, str] | None:
    """Try to extract a transformation prefix from the remaining base text.

    Returns dict with 'transformation' and 'physical_base' keys, or None.
    """
    for token in _TRANSFORMATION_TOKENS_SORTED:
        prefix = token + "_"
        if remaining.startswith(prefix):
            base = remaining[len(prefix) :]
            if base and TOKEN_PATTERN.fullmatch(base):
                return {"transformation": token, "physical_base": base}
    return None


def _try_parse_decomposition(remaining: str) -> dict[str, str] | None:
    """Try to extract a decomposition prefix from the remaining base text.

    Sits between transformation and physical_base. Exclusive with transformation
    (enforced by a model validator). Returns dict with 'decomposition' and
    'physical_base' keys, or None.
    """
    for token in _DECOMPOSITION_TOKENS_SORTED:
        prefix = token + "_"
        if remaining.startswith(prefix):
            base = remaining[len(prefix) :]
            if base and TOKEN_PATTERN.fullmatch(base):
                return {"decomposition": token, "physical_base": base}
    return None


def _try_parse_binary_operator(remaining: str) -> dict[str, str] | None:
    """Try to parse a binary operator expression from remaining text.

    Expected form: {operator}_{base1}_{connector}_{base2}

    Returns dict with 'binary_operator', 'physical_base', 'secondary_base',
    or None if no binary operator is detected.
    """
    for op_token in _BINARY_OPERATOR_TOKENS_SORTED:
        prefix = op_token + "_"
        if remaining.startswith(prefix):
            connector = BINARY_OPERATOR_CONNECTORS.get(op_token)
            if not connector:
                continue
            operand_text = remaining[len(prefix) :]
            connector_sep = f"_{connector}_"

            # Split on the connector; use the last occurrence to maximize
            # the first operand (physical bases are open vocabulary)
            idx = operand_text.rfind(connector_sep)
            if idx < 0:
                continue

            base1 = operand_text[:idx]
            base2 = operand_text[idx + len(connector_sep) :]

            if (
                base1
                and base2
                and TOKEN_PATTERN.fullmatch(base1)
                and TOKEN_PATTERN.fullmatch(base2)
            ):
                return {
                    "binary_operator": op_token,
                    "physical_base": base1,
                    "secondary_base": base2,
                }
    return None
