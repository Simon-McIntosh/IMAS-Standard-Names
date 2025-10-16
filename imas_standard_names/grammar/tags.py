"""Tag vocabulary utilities for IMAS Standard Names.

Provides functions to load and query the controlled tag vocabulary,
including primary tags (for catalog organization) and secondary tags
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


def get_primary_tags() -> list[str]:
    """Get list of valid primary tag identifiers.

    Returns:
        Sorted list of primary tag IDs that can be used as tags[0].
    """
    vocab = load_tag_vocabulary()
    return sorted(vocab.get("primary_tags", {}).keys())


def get_secondary_tags() -> list[str]:
    """Get list of valid secondary tag identifiers.

    Returns:
        List of secondary tag IDs that can be used as tags[1:].
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


def validate_tags(tags: list[str]) -> tuple[bool, str]:
    """Validate a list of tags against the controlled vocabulary.

    Args:
        tags: List of tags to validate (tags[0] must be primary).

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not tags:
        return True, ""

    primary_tags = get_primary_tags()
    secondary_tags = get_secondary_tags()

    # Validate primary tag
    if tags[0] not in primary_tags:
        return False, (
            f"Primary tag (tags[0]) '{tags[0]}' not in controlled vocabulary. "
            f"Valid primary tags: {', '.join(primary_tags)}"
        )

    # Validate secondary tags (optional)
    for tag in tags[1:]:
        if tag not in secondary_tags and tag not in primary_tags:
            return False, (
                f"Secondary tag '{tag}' not in controlled vocabulary. "
                f"Valid secondary tags: {', '.join(secondary_tags[:10])}... "
                f"(see tags.yml for complete list)"
            )

    return True, ""


__all__ = [
    "load_tag_vocabulary",
    "get_primary_tags",
    "get_secondary_tags",
    "get_tag_description",
    "get_tag_examples",
    "get_tag_ids_list",
    "validate_tags",
]
