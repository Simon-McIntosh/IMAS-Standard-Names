"""mkdocs-macros plugin module for auto-generating grammar documentation.

This module provides Jinja2 macros that expose the canonical grammar
specification from grammar.yml to the documentation build process.

All tables and lists are generated at build time from the single source
of truth, ensuring documentation stays synchronized with the implementation.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


def define_env(env: Any) -> None:
    """Register custom macros for grammar documentation.

    This function is called by mkdocs-macros plugin during the build process.
    It registers all custom macros and filters that can be used in markdown files.

    Args:
        env: The mkdocs-macros environment object.
    """
    # Import here to avoid issues if grammar types aren't generated yet
    from imas_standard_names.grammar_codegen.spec import GrammarSpec

    # Load the grammar specification (cached)
    _grammar_spec = GrammarSpec.load()

    @env.macro
    def grammar_vocabulary_table(
        vocab_name: str,
        include_description: bool = False,
    ) -> str:
        """Generate a markdown table of vocabulary tokens.

        Args:
            vocab_name: Name of the vocabulary (e.g., 'components', 'subjects').
            include_description: Whether to include a description column.

        Returns:
            Markdown table as a string.
        """
        tokens = _grammar_spec.vocabulary_tokens(vocab_name)
        if not tokens:
            return f"_No tokens defined for vocabulary '{vocab_name}'_"

        if include_description:
            # Future: when descriptions are added to grammar.yml
            lines = ["| Token | Description |", "|-------|-------------|"]
            for token in tokens:
                lines.append(f"| `{token}` | _(description pending)_ |")
        else:
            # Simple list format
            lines = ["| Token |", "|-------|"]
            for token in tokens:
                lines.append(f"| `{token}` |")

        return "\n".join(lines)

    @env.macro
    def grammar_segment_order() -> str:
        """Generate formatted list of segment order.

        Returns:
            Markdown formatted segment order.
        """
        segments = [seg.identifier for seg in _grammar_spec.segments]

        lines = ["```text"]
        lines.append(" → ".join(segments))
        lines.append("```")
        lines.append("")
        lines.append("Where:")
        lines.append("")

        for seg in _grammar_spec.segments:
            optional = " (optional)" if seg.optional else " (required)"
            template_info = f" - template: `{seg.template}`" if seg.template else ""
            lines.append(f"- **{seg.identifier}**{optional}{template_info}")

        return "\n".join(lines)

    @env.macro
    def grammar_basis_components() -> str:
        """Generate basis to components mapping table.

        Returns:
            Markdown table showing which components belong to each basis.
        """
        if not _grammar_spec.basis:
            return "_No basis definitions found_"

        lines = [
            "| Basis | Description | Components |",
            "|-------|-------------|------------|",
        ]

        for basis_name, basis_group in _grammar_spec.basis.items():
            components = ", ".join(f"`{c}`" for c in basis_group.components)
            description = basis_group.description or "_(no description)_"
            lines.append(f"| `{basis_name}` | {description} | {components} |")

        return "\n".join(lines)

    @env.macro
    def grammar_segment_rules_table() -> str:
        """Generate comprehensive segment rules table.

        Returns:
            Markdown table with segment metadata.
        """
        lines = [
            "| Segment | Required | Template | Vocabulary | Exclusive With |",
            "|---------|----------|----------|------------|----------------|",
        ]

        for seg in _grammar_spec.segments:
            required = "Yes" if not seg.optional else "No"
            template = f"`{seg.template}`" if seg.template else "—"
            vocab = seg.vocabulary_name or "_(dynamic)_"
            exclusive = (
                ", ".join(f"`{ex}`" for ex in seg.exclusive_with)
                if seg.exclusive_with
                else "—"
            )

            lines.append(
                f"| `{seg.identifier}` | {required} | {template} | {vocab} | {exclusive} |"
            )

        return "\n".join(lines)

    @env.macro
    def grammar_exclusive_pairs() -> str:
        """Generate list of mutually exclusive segment pairs.

        Returns:
            Markdown formatted list.
        """
        # Collect all exclusive pairs
        pairs = set()
        for seg in _grammar_spec.segments:
            for other in seg.exclusive_with:
                # Store as sorted tuple to avoid duplicates
                pair = tuple(sorted([seg.identifier, other]))
                pairs.add(pair)

        if not pairs:
            return "_No exclusive pairs defined_"

        lines = []
        for seg1, seg2 in sorted(pairs):
            lines.append(f"- `{seg1}` and `{seg2}` are mutually exclusive")

        return "\n".join(lines)

    @env.macro
    def grammar_version() -> str:
        """Get grammar version information from package metadata.

        Returns:
            Version string from the installed package.
        """
        try:
            from importlib.metadata import version

            pkg_version = version("imas-standard-names")
            return f"Grammar version: {pkg_version}"
        except Exception:
            # Fallback during development or if package not installed
            return "Grammar version: development build"

    @env.macro
    def grammar_vocabulary_count(vocab_name: str) -> int:
        """Get count of tokens in a vocabulary.

        Args:
            vocab_name: Name of the vocabulary.

        Returns:
            Number of tokens.
        """
        tokens = _grammar_spec.vocabulary_tokens(vocab_name)
        return len(tokens)

    @env.macro
    def grammar_all_vocabularies() -> str:
        """Generate overview of all vocabularies with counts.

        Returns:
            Markdown table of all vocabularies.
        """
        lines = [
            "| Vocabulary | Token Count | Usage |",
            "|------------|-------------|-------|",
        ]

        vocab_usage = {
            "components": "Vector component directions",
            "subjects": "Particle species or plasma subjects",
            "basis": "Coordinate system bases",
            "positions": "Spatial locations or regions",
            "processes": "Physical processes or mechanisms",
        }

        for vocab_name in _grammar_spec.vocabularies.keys():
            count = len(_grammar_spec.vocabulary_tokens(vocab_name))
            usage = vocab_usage.get(vocab_name, "_(see documentation)_")
            lines.append(f"| `{vocab_name}` | {count} | {usage} |")

        return "\n".join(lines)

    @env.macro
    def grammar_component_tokens() -> str:
        """Generate inline list of component tokens.

        Useful for prose where full table is too verbose.

        Returns:
            Comma-separated inline list.
        """
        tokens = _grammar_spec.vocabulary_tokens("components")
        return ", ".join(f"`{token}`" for token in tokens)

    @env.macro
    def grammar_subject_tokens() -> str:
        """Generate inline list of subject tokens.

        Returns:
            Comma-separated inline list.
        """
        tokens = _grammar_spec.vocabulary_tokens("subjects")
        return ", ".join(f"`{token}`" for token in tokens)

    @env.macro
    def grammar_position_tokens() -> str:
        """Generate inline list of position tokens.

        Returns:
            Comma-separated inline list.
        """
        tokens = _grammar_spec.vocabulary_tokens("positions")
        return ", ".join(f"`{token}`" for token in tokens)

    @env.macro
    def grammar_process_tokens() -> str:
        """Generate inline list of process tokens.

        Returns:
            Comma-separated inline list.
        """
        tokens = _grammar_spec.vocabulary_tokens("processes")
        return ", ".join(f"`{token}`" for token in tokens)

    @env.macro
    def grammar_basis_tokens() -> str:
        """Generate inline list of basis tokens.

        Returns:
            Comma-separated inline list.
        """
        tokens = _grammar_spec.vocabulary_tokens("basis")
        return ", ".join(f"`{token}`" for token in tokens)

    # Standard Names Catalog Macros
    @env.macro
    def load_standard_names():
        """Load all YAML standard names from the catalog directory"""
        project_root = Path(env.project_dir).parent
        standard_names_dir = (
            project_root / "imas_standard_names" / "resources" / "standard_names"
        )
        standard_names = []

        if standard_names_dir.exists():
            for root, dirs, files in os.walk(standard_names_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                for file in files:
                    if file.endswith(".yml") or file.endswith(".yaml"):
                        yaml_path = Path(root) / file
                        try:
                            with open(yaml_path, encoding="utf-8") as f:
                                data = yaml.safe_load(f)

                            if data and isinstance(data, dict):
                                data["_file_path"] = str(
                                    yaml_path.relative_to(project_root)
                                )
                                data["_category"] = yaml_path.parent.name
                                standard_names.append(data)
                        except Exception as e:
                            print(f"Error loading {yaml_path}: {e}")

        return standard_names

    @env.macro
    def get_categories():
        """Get all unique categories (directories) containing standard names"""
        standard_names = load_standard_names()
        categories = {}

        for item in standard_names:
            category = item.get("_category", "unknown")
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        return categories

    @env.macro
    def get_tags():
        """Group standard names by their primary tags"""
        standard_names = load_standard_names()
        tags_groups = defaultdict(list)

        for item in standard_names:
            if "tags" in item and item["tags"]:
                primary_tag = item["tags"][0]
                tags_groups[primary_tag].append(item)

        return dict(tags_groups)

    @env.macro
    def category_stats():
        """Get statistics about categories and standard names"""
        categories = get_categories()
        tags = get_tags()
        total_names = sum(len(items) for items in categories.values())

        return {
            "total_names": total_names,
            "total_categories": len(categories),
            "total_tags": len(tags),
            "categories": categories,
            "tags": tags,
        }

    def _fix_markdown_formatting(text):
        """Fix markdown formatting and ensure proper indentation for admonitions"""
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

            if "$$" in paragraph:
                processed_paragraphs.append(paragraph)
            elif paragraph.startswith("$$") and paragraph.endswith("$$"):
                processed_paragraphs.append(paragraph)
            elif "$" in paragraph and paragraph.count("$") >= 2:
                processed_paragraphs.append(paragraph)
            elif any(
                line.strip().startswith(("-", "*", "+"))
                for line in paragraph.split("\n")
            ):
                processed_paragraphs.append(paragraph)
            elif any(
                re.match(r"^\d+\.", line.strip()) for line in paragraph.split("\n")
            ):
                processed_paragraphs.append(paragraph)
            else:
                processed_paragraphs.append(paragraph)

        result = "\n\n".join(processed_paragraphs)
        result = re.sub(r"\n\s*\$\$", "\n\n$$", result)
        result = re.sub(r"\$\$\s*\n", "$$\n\n", result)

        return result

    @env.macro
    def standard_names_catalog():
        """Generate a complete catalog of all standard names organized by primary tag"""
        result = ""
        tags = get_tags()

        if not tags:
            return "_No standard names found in the catalog._"

        for category, items in sorted(tags.items()):
            category_name = category.replace("-", " ").title()
            result += f"## **{category_name}** {{#{category}}}\n\n"
            result += "---\n\n"

            sorted_items = sorted(items, key=lambda x: x.get("name", ""))

            for item in sorted_items:
                name = item.get("name", "Unknown")
                unit = item.get("unit", "")
                description = item.get("description", "")
                documentation = item.get("documentation", "")
                item_tags = item.get("tags", [])
                status = item.get("status", "")

                tags_display = (
                    ", ".join(f"`{tag}`" for tag in item_tags) if item_tags else "None"
                )

                result += f"### {name}\n\n"
                result += f"{description}\n\n"

                if documentation:
                    result += f"{_fix_markdown_formatting(documentation)}\n\n"

                if unit:
                    result += f"**Unit:** `{unit}`\n\n"

                if status:
                    result += f"**Status:** {status.title()}\n\n"

                if item_tags:
                    result += f"**Tags:** {tags_display}\n\n"

                result += "---\n\n"

        return result

    @env.macro
    def catalog_overview():
        """Generate overview statistics for the catalog"""
        stats = category_stats()

        if stats["total_names"] == 0:
            return "_The standard names catalog is currently empty._"

        result = f"**Total Standard Names:** {stats['total_names']}\n\n"
        result += f"**Categories:** {stats['total_tags']}\n\n"

        result += "### Categories\n\n"
        for category, items in sorted(stats["tags"].items()):
            category_name = category.replace("-", " ").title()
            category_anchor = category_name.lower().replace(" ", "-")
            count = len(items)
            result += f"- **[{category_name}](#{category_anchor})** - {count} standard names\n"

        return result
