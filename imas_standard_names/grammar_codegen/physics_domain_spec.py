"""Load and normalize the physics domain vocabulary specification.

Similar to tag_spec.py but specialized for physics_domains.yml structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

import yaml

_GRAMMAR_PACKAGE = "imas_standard_names.grammar"
_VOCABULARIES_SUBPATH = "vocabularies"
_PHYSICS_DOMAINS_FILENAME = "physics_domains.yml"


@dataclass(frozen=True)
class PhysicsDomainSpec:
    """Specification for physics domain vocabulary."""

    domains: tuple[str, ...]
    descriptions: dict[str, str]
    categories: dict[str, str]
    ids_mapping: dict[str, list[str]]
    tag_aliases: dict[str, str]

    @classmethod
    def load(cls) -> PhysicsDomainSpec:
        """Load physics domain vocabulary from physics_domains.yml."""
        domains_path = (
            resources.files(_GRAMMAR_PACKAGE)
            / _VOCABULARIES_SUBPATH
            / _PHYSICS_DOMAINS_FILENAME
        )
        with domains_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        # Extract physics domains (dict structure)
        domains_raw = data.get("physics_domains", {})
        domains: list[str] = []
        descriptions: dict[str, str] = {}
        categories: dict[str, str] = {}
        ids_mapping: dict[str, list[str]] = {}

        if isinstance(domains_raw, dict):
            for domain_id, domain_data in domains_raw.items():
                domains.append(domain_id)
                if isinstance(domain_data, dict):
                    descriptions[domain_id] = domain_data.get("description", "")
                    categories[domain_id] = domain_data.get("category", "")
                    ids_raw = domain_data.get("ids", [])
                    ids_mapping[domain_id] = (
                        list(ids_raw) if isinstance(ids_raw, list) else []
                    )

        # Extract tag aliases (dict structure)
        aliases_raw = data.get("tag_aliases", {})
        tag_aliases: dict[str, str] = {}

        if isinstance(aliases_raw, dict):
            for old_tag, new_domain in aliases_raw.items():
                tag_aliases[str(old_tag)] = str(new_domain)

        return cls(
            domains=tuple(domains),
            descriptions=descriptions,
            categories=categories,
            ids_mapping=ids_mapping,
            tag_aliases=tag_aliases,
        )


__all__ = ["PhysicsDomainSpec"]
