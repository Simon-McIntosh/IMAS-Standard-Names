"""Catalog rendering for Standard Names documentation.

Provides reusable catalog rendering logic that can be used by both
the main project docs and external catalog repositories.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

import yaml


class CatalogRenderer:
    """Renders standard names catalog as Markdown documentation.

    This class loads YAML standard name files from a directory and generates
    Markdown content suitable for mkdocs-based documentation sites.

    Parameters
    ----------
    catalog_path : Path
        Path to directory containing YAML standard name files.
    """

    def __init__(self, catalog_path: Path):
        self.catalog_path = Path(catalog_path)
        self._names: list[dict] | None = None

    def load_names(self) -> list[dict]:
        """Load all YAML standard names from the catalog directory.

        Recursively searches all subdirectories for YAML files.

        Returns
        -------
        list[dict]
            List of standard name dictionaries loaded from YAML files.
        """
        if self._names is not None:
            return self._names

        standard_names = []

        if not self.catalog_path.exists():
            return standard_names

        # Use rglob for recursive search (matches YamlStore behavior)
        yaml_files = sorted(
            list(self.catalog_path.rglob("*.yml"))
            + list(self.catalog_path.rglob("*.yaml"))
        )

        for yaml_file in yaml_files:
            try:
                yaml_content = yaml_file.read_text(encoding="utf-8")
                data = yaml.safe_load(yaml_content)

                if data and isinstance(data, dict) and "name" in data:
                    data["_file_path"] = str(yaml_file)
                    data["_category"] = "standard_names"
                    standard_names.append(data)
            except Exception as e:
                print(f"Error loading {yaml_file.name}: {e}")

        self._names = standard_names
        return standard_names

    def get_tags(self) -> dict[str, list[dict]]:
        """Group standard names by their physics domain.

        Returns
        -------
        dict[str, list[dict]]
            Dictionary mapping physics domain to list of entries.
        """
        names = self.load_names()
        tags_groups: dict[str, list[dict]] = defaultdict(list)

        for item in names:
            pd = item.get("physics_domain", "")
            if pd:
                tags_groups[pd].append(item)

        return dict(tags_groups)

    def get_stats(self) -> dict:
        """Get statistics about the catalog.

        Returns
        -------
        dict
            Dictionary with total_names, total_tags, and tags breakdown.
        """
        tags = self.get_tags()
        total_names = sum(len(items) for items in tags.values())

        return {
            "total_names": total_names,
            "total_tags": len(tags),
            "tags": tags,
        }

    @staticmethod
    def _fix_markdown_formatting(text: str) -> str:
        """Fix markdown formatting and ensure proper indentation."""
        if not text:
            return ""

        text = text.strip()
        text = text.replace("\\n", "\n")

        paragraphs = text.split("\n\n")
        processed_paragraphs = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            processed_paragraphs.append(paragraph)

        result = "\n\n".join(processed_paragraphs)
        result = re.sub(r"\n\s*\$\$", "\n\n$$", result)
        result = re.sub(r"\$\$\s*\n", "$$\n\n", result)

        return result

    @staticmethod
    def _parse_base(name: str) -> str:
        """Extract base name from a standard name.

        Attempts to parse using grammar, falls back to 'unknown'.
        """
        try:
            from ..grammar.model import parse_standard_name  # noqa: PLC0415

            parsed = parse_standard_name(name)
            return parsed.physical_base or parsed.geometric_base or "unknown"
        except Exception:
            return "unknown"

    def render_catalog(self) -> str:
        """Generate complete catalog organized by primary tag and base name.

        Returns
        -------
        str
            Markdown formatted catalog content.
        """
        result = ""
        tags = self.get_tags()

        if not tags:
            return "_No standard names found in the catalog._"

        for category, items in sorted(tags.items()):
            category_name = category.replace("-", " ").title()
            result += f"## {category_name} {{: #{category} }}\n\n"
            result += "---\n\n"

            # Group items by base name
            base_groups: dict[str, list[dict]] = defaultdict(list)
            for item in items:
                name = item.get("name", "Unknown")
                base = self._parse_base(name)
                base_groups[base].append(item)

            for base_name in sorted(base_groups.keys()):
                base_items = base_groups[base_name]
                base_display = base_name.replace("_", " ").title()
                result += f"### {base_display}\n\n"

                sorted_items = sorted(base_items, key=lambda x: x.get("name", ""))

                for item in sorted_items:
                    name = item.get("name", "Unknown")
                    unit = item.get("unit", "")
                    description = item.get("description", "")
                    documentation = item.get("documentation", "")
                    item_tags = item.get("tags", [])
                    status = item.get("status", "")

                    tags_display = (
                        ", ".join(f"`{tag}`" for tag in item_tags)
                        if item_tags
                        else "None"
                    )

                    result += f"#### {name} {{: #{name} }}\n\n"
                    result += f"{description}\n\n"

                    if documentation:
                        result += f"{self._fix_markdown_formatting(documentation)}\n\n"

                    if unit:
                        result += f"**Unit:** `{unit}`\n\n"

                    if status:
                        result += f"**Status:** {status.title()}\n\n"

                    if item_tags:
                        result += f"**Tags:** {tags_display}\n\n"

                    result += "---\n\n"

        return result

    def render_overview(self, link_prefix: str = "") -> str:
        """Generate overview statistics for the catalog.

        Parameters
        ----------
        link_prefix : str
            Prefix for category links. Use "catalog.md" when rendering
            overview for a different page (e.g., index.md).

        Returns
        -------
        str
            Markdown formatted overview content.
        """
        stats = self.get_stats()

        if stats["total_names"] == 0:
            return "_The standard names catalog is currently empty._"

        result = f"**Total Standard Names:** {stats['total_names']}\n\n"
        result += f"**Categories:** {stats['total_tags']}\n\n"

        result += "### Categories\n\n"
        for category, items in sorted(stats["tags"].items()):
            category_name = category.replace("-", " ").title()
            count = len(items)
            result += f"- **[{category_name}]({link_prefix}#{category})** - {count} standard names\n"

        return result

    def render_navigation(self) -> str:
        """Generate navigation sidebar with all standard names.

        Returns
        -------
        str
            Markdown formatted navigation content.
        """
        tags = self.get_tags()

        if not tags:
            return ""

        result = ""

        for category, items in sorted(tags.items()):
            category_name = category.replace("-", " ").title()
            result += f"**[{category_name}](#{category})**\n\n"

            base_groups: dict[str, list[dict]] = defaultdict(list)
            for item in items:
                name = item.get("name", "Unknown")
                base = self._parse_base(name)
                base_groups[base].append(item)

            for base_name in sorted(base_groups.keys()):
                base_items = base_groups[base_name]
                sorted_items = sorted(base_items, key=lambda x: x.get("name", ""))

                for item in sorted_items:
                    name = item.get("name", "Unknown")
                    result += f"- [{name}](#{name})\n"

            result += "\n"

        return result


def get_catalog_path_from_env() -> Path | None:
    """Get catalog path from environment variable.

    Returns
    -------
    Path | None
        Catalog path if DOCS_CATALOG_ROOT is set, None otherwise.
    """
    catalog_root = os.environ.get("DOCS_CATALOG_ROOT")
    if catalog_root:
        return Path(catalog_root).expanduser().resolve()
    return None


__all__ = ["CatalogRenderer", "get_catalog_path_from_env"]
