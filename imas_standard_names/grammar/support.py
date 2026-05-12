"""Static helpers for standard-name parsing and composition.

These functions are intentionally hand-written to minimize churn in the
auto-generated file and to keep behavior clear and testable.
"""

from __future__ import annotations

import re
from typing import Any

# Token pattern used by base and the overall name validation.
TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


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
    (
        "diamagnetic_component_of_",
        (
            "'diamagnetic' is a drift qualifier, not a spatial axis. "
            "Did you mean: radial_component_of_<subject>_diamagnetic_drift_velocity?"
        ),
        (),
    ),
    (
        "_density_ratio",
        (
            "Ad-hoc ratio compound. Use canonical form: "
            "ratio_of_<A>_density_to_<B>_density"
        ),
        # Exclude names that legitimately contain ratio_of (canonical form)
        ("ratio_of_",),
    ),
)


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


class UnknownBaseTokenError(ValueError):
    """Raised when a base token is not in the closed vocabulary.

    Attributes:
        token: The unrecognised token.
        segment: Always ``"physical_base"``.
        known_tokens: Tuple of valid tokens for the segment.
    """

    def __init__(self, token: str, known_tokens: tuple[str, ...]) -> None:
        self.token = token
        self.segment = "physical_base"
        self.known_tokens = known_tokens
        super().__init__(
            f"Unknown physical_base token '{token}' — "
            f"not in closed vocabulary ({len(known_tokens)} tokens). "
            f"Report as a vocab_gap or choose from the registered tokens."
        )
