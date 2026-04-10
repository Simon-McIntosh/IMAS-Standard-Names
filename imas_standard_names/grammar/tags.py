"""Tag vocabulary utilities for IMAS Standard Names.

Provides functions to load and query the controlled tag vocabulary,
including physics domains (for catalog organization) and secondary tags
(for cross-cutting classification).
"""

from pathlib import Path
from typing import Any

import yaml


def load_tag_vocabulary() -> dict[str, Any]:
    """Load the complete tag vocabulary from tags.yml.

    Returns:
        Dictionary with 'primary_tags' and 'secondary_tags' sections.
    """
    vocab_path = Path(__file__).parent / "vocabularies" / "tags.yml"
    if not vocab_path.exists():
        return {"primary_tags": {}, "secondary_tags": []}

    with open(vocab_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"primary_tags": {}, "secondary_tags": []}


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


def get_secondary_tags() -> list[str]:
    """Get list of valid secondary tag identifiers.

    Returns:
        List of secondary tag IDs for cross-cutting classification.
    """
    vocab = load_tag_vocabulary()
    secondary = vocab.get("secondary_tags", [])
    return [tag["id"] for tag in secondary if isinstance(tag, dict) and "id" in tag]


def get_tag_description(tag_id: str) -> str:
    """Get description for a specific tag.

    Args:
        tag_id: Tag identifier to look up.

    Returns:
        Description string, or empty string if not found.
    """
    vocab = load_tag_vocabulary()

    # Check primary tags
    primary = vocab.get("primary_tags", {})
    if tag_id in primary:
        return primary[tag_id].get("description", "")

    # Check secondary tags
    secondary = vocab.get("secondary_tags", [])
    for tag in secondary:
        if isinstance(tag, dict) and tag.get("id") == tag_id:
            return tag.get("description", "")

    return ""


def get_tag_examples(tag_id: str) -> list[str]:
    """Get example standard names for a primary tag.

    Args:
        tag_id: Primary tag identifier.

    Returns:
        List of example standard name patterns.
    """
    vocab = load_tag_vocabulary()
    primary = vocab.get("primary_tags", {})
    if tag_id in primary:
        return primary[tag_id].get("examples", [])
    return []


def get_tag_ids_list(tag_id: str) -> list[str]:
    """Get list of IMAS IDS associated with a primary tag.

    Args:
        tag_id: Primary tag identifier.

    Returns:
        List of IDS names associated with this tag.
    """
    vocab = load_tag_vocabulary()
    primary = vocab.get("primary_tags", {})
    if tag_id in primary:
        return primary[tag_id].get("ids", [])
    return []


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


def validate_tags(tags: list[str]) -> tuple[bool, str]:
    """Validate a list of secondary tags against the controlled vocabulary.

    Args:
        tags: List of secondary tags to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not tags:
        return True, ""

    secondary_tags = get_secondary_tags()
    for tag in tags:
        if tag not in secondary_tags:
            return False, (
                f"Secondary tag '{tag}' not in controlled vocabulary. "
                f"Valid secondary tags: {', '.join(secondary_tags[:10])}... "
                f"(see tags.yml for complete list)"
            )

    return True, ""


__all__ = [
    "load_tag_vocabulary",
    "get_physics_domains",
    "get_physics_domain_description",
    "get_secondary_tags",
    "get_tag_description",
    "get_tag_examples",
    "get_tag_ids_list",
    "validate_physics_domain",
    "validate_tags",
]
