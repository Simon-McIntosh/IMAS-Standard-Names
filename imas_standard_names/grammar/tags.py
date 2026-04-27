"""Physics domain vocabulary utilities for IMAS Standard Names.

Provides functions to query the controlled physics domain vocabulary
(for catalog organization).
"""


def get_physics_domains() -> list[str]:
    """Get list of valid physics domain identifiers.

    Returns:
        Sorted list of physics domain values from the PhysicsDomain enum.
    """
    from .tag_types import PHYSICS_DOMAINS

    return list(PHYSICS_DOMAINS)


def get_physics_domain_description(domain: str) -> str:
    """Get description for a physics domain.

    Args:
        domain: Physics domain identifier to look up.

    Returns:
        Description string, or empty string if not found.
    """
    from .tag_types import PHYSICS_DOMAIN_DESCRIPTIONS

    return PHYSICS_DOMAIN_DESCRIPTIONS.get(domain, "")


def validate_physics_domain(domain: str) -> tuple[bool, str]:
    """Validate a physics domain against the controlled vocabulary.

    Args:
        domain: Physics domain string to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    from .tag_types import PHYSICS_DOMAINS

    if not domain:
        return False, "Physics domain is required"
    if domain not in PHYSICS_DOMAINS:
        return False, (
            f"Invalid physics domain '{domain}'. "
            f"Valid: {', '.join(sorted(PHYSICS_DOMAINS)[:10])}..."
        )
    return True, ""


__all__ = [
    "get_physics_domains",
    "get_physics_domain_description",
    "validate_physics_domain",
]
