"""Load and normalize the tag vocabulary specification.

Similar to spec.py but specialized for tags.yml structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml

_GRAMMAR_PACKAGE = "imas_standard_names.grammar"
_VOCABULARIES_SUBPATH = "vocabularies"
_TAGS_FILENAME = "tags.yml"


@dataclass(frozen=True)
class TagSpec:
    """Specification for tag vocabularies."""

    primary_tags: tuple[str, ...]
    secondary_tags: tuple[str, ...]
    primary_metadata: dict[str, dict[str, Any]]
    secondary_metadata: dict[str, dict[str, Any]]

    @classmethod
    def load(cls) -> TagSpec:
        """Load tag vocabulary from tags.yml."""
        tags_path = (
            resources.files(_GRAMMAR_PACKAGE) / _VOCABULARIES_SUBPATH / _TAGS_FILENAME
        )
        with tags_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        # Extract primary tags (dict structure)
        primary_raw = data.get("primary_tags", {})
        primary_tags: list[str] = []
        primary_metadata: dict[str, dict[str, Any]] = {}

        if isinstance(primary_raw, dict):
            for tag_id, tag_data in primary_raw.items():
                primary_tags.append(tag_id)
                primary_metadata[tag_id] = (
                    tag_data if isinstance(tag_data, dict) else {}
                )

        # Extract secondary tags (list structure)
        secondary_raw = data.get("secondary_tags", [])
        secondary_tags: list[str] = []
        secondary_metadata: dict[str, dict[str, Any]] = {}

        if isinstance(secondary_raw, list):
            for entry in secondary_raw:
                if isinstance(entry, dict):
                    tag_id = entry.get("id")
                    if tag_id:
                        secondary_tags.append(tag_id)
                        secondary_metadata[tag_id] = entry

        return cls(
            primary_tags=tuple(primary_tags),
            secondary_tags=tuple(secondary_tags),
            primary_metadata=primary_metadata,
            secondary_metadata=secondary_metadata,
        )


__all__ = ["TagSpec"]
