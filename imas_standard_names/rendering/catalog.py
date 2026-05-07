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

# Rewrite [label](name:foo_bar) → [label](#foo_bar) for in-page anchors.
_NAME_LINK_RE = re.compile(r"\[([^\]]+)\]\(name:([a-z0-9_]+)\)")


def _humanize(name: str) -> str:
    """Convert ``snake_case`` standard name to readable text."""
    return name.replace("_", " ")


def _rewrite_name_links(text: str) -> str:
    """Replace ``name:foo`` protocol links with humanized in-page anchors."""
    return _NAME_LINK_RE.sub(
        lambda m: f"[{_humanize(m.group(2))}](#{m.group(2)})", text
    )


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

        Supports both per-domain list files (plan 40 layout) and legacy
        per-file single-entry dicts with a ``name`` key.

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

                if isinstance(data, list):
                    for entry in data:
                        if entry and isinstance(entry, dict) and "name" in entry:
                            entry["_file_path"] = str(yaml_file)
                            entry["_category"] = "standard_names"
                            standard_names.append(entry)
                elif data and isinstance(data, dict) and "name" in data:
                    data["_file_path"] = str(yaml_file)
                    data["_category"] = "standard_names"
                    standard_names.append(data)
            except Exception as e:
                print(f"Error loading {yaml_file.name}: {e}")

        self._names = standard_names
        return standard_names

    def get_domains(self) -> dict[str, list[dict]]:
        """Group standard names by physics_domain.

        Falls back to "uncategorized" for entries without a physics_domain.

        Returns
        -------
        dict[str, list[dict]]
            Dictionary mapping physics domain to list of entries.
        """
        names = self.load_names()
        domain_groups: dict[str, list[dict]] = defaultdict(list)

        for item in names:
            domain = item.get("physics_domain") or "uncategorized"
            domain_groups[domain].append(item)

        return dict(domain_groups)

    def get_stats(self) -> dict:
        """Get statistics about the catalog.

        Returns
        -------
        dict
            Dictionary with total_names, total_domains, and domains breakdown.
        """
        domains = self.get_domains()
        total_names = sum(len(items) for items in domains.values())

        return {
            "total_names": total_names,
            "total_domains": len(domains),
            "domains": domains,
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
        """Extract base name from a standard name for catalog grouping.

        Uses the ISN grammar parser to extract the core physical quantity.
        For transformed names (derivative_of_X, tendency_of_X), extracts the
        inner quantity so all derivatives of the same base group together.
        """
        try:
            from ..grammar.model import parse_standard_name  # noqa: PLC0415

            parsed = parse_standard_name(name)
            base = parsed.physical_base or parsed.geometric_base or "unknown"

            # Transformed names leave residue in physical_base.
            # Strip transformation prefixes to find the true base quantity.
            # e.g. "of_electron_density_with_respect_to_..." → "electron_density"
            if base.startswith("of_"):
                inner = base[3:]
                # Strip "with_respect_to_..." suffix (derivative denominator)
                wrt_idx = inner.find("_with_respect_to_")
                if wrt_idx >= 0:
                    inner = inner[:wrt_idx]
                base = inner

            # If subject is present, include it for better grouping
            # e.g. "electron" + "density" → "electron_density"
            subject = getattr(parsed, "subject", None)
            if subject and not base.startswith(subject):
                base = f"{subject}_{base}"

            return base
        except Exception:
            return "unknown"

    # ------------------------------------------------------------------
    # Plan 41 helpers: links, cocos, mermaid, sibling nav
    # ------------------------------------------------------------------
    @staticmethod
    def _render_links(links: list[str]) -> str:
        """Render ``links:`` as markdown; ``name:X`` → humanized in-page anchor."""
        if not links:
            return ""
        parts: list[str] = []
        for link in links:
            if not isinstance(link, str):
                continue
            link = link.strip()
            if link.startswith("name:"):
                target = link[len("name:") :].strip()
                if target:
                    parts.append(f"[{_humanize(target)}](#{target})")
            elif link:
                parts.append(f"[{link}]({link})")
        if not parts:
            return ""
        return "**See also:** " + " · ".join(parts) + "\n\n"

    @staticmethod
    def _argument_label(arg: dict) -> str:
        """Build a mermaid edge label for a HAS_ARGUMENT edge."""
        operator = arg.get("operator") or "arg"
        parts = [str(operator)]
        role = arg.get("role")
        if role:
            parts.append(f"role={role}")
        axis = arg.get("axis")
        if axis:
            parts.append(f"axis={axis}")
        shape = arg.get("shape")
        if shape:
            parts.append(f"shape={shape}")
        return " ".join(parts)

    @classmethod
    def _render_mermaid(cls, item: dict) -> str:
        """Emit a Mermaid hierarchy block when structural fields exist.

        Uses short node IDs with humanized display labels to prevent
        text overflow in diagrams. Nodes are clickable — linking to
        the corresponding entry's anchor on the same page.
        """
        arguments = item.get("arguments") or []
        error_variants = item.get("error_variants") or {}
        deprecates = item.get("deprecates")
        superseded_by = item.get("superseded_by")

        has_any = (
            bool(arguments)
            or bool(error_variants)
            or bool(deprecates)
            or bool(superseded_by)
        )
        if not has_any:
            return ""

        name = item.get("name", "")
        # Build node registry for short IDs
        nodes: dict[str, str] = {}  # full_name → short_id
        node_counter = 0

        def _node(full_name: str) -> str:
            nonlocal node_counter
            if full_name not in nodes:
                nodes[full_name] = f"n{node_counter}"
                node_counter += 1
            return nodes[full_name]

        def _decl(full_name: str) -> str:
            """Node declaration with humanized label."""
            nid = _node(full_name)
            label = _humanize(full_name)
            return f'{nid}["{label}"]'

        lines: list[str] = ["```mermaid", "graph LR"]
        src = _decl(name)
        for arg in arguments:
            if isinstance(arg, dict) and arg.get("name"):
                label = cls._argument_label(arg)
                tgt = _decl(arg["name"])
                lines.append(f'  {src} -- "{label}" --> {tgt}')
            elif isinstance(arg, str):
                tgt = _decl(arg)
                lines.append(f'  {src} -- "arg" --> {tgt}')
        if isinstance(error_variants, dict):
            for error_type, target in error_variants.items():
                if target:
                    tgt = _decl(target)
                    lines.append(f'  {src} -- "error {error_type}" --> {tgt}')
        if deprecates:
            tgt = _decl(deprecates)
            lines.append(f'  {src} -- "deprecates" --> {tgt}')
        if superseded_by:
            tgt = _decl(superseded_by)
            lines.append(f'  {src} -- "superseded by" --> {tgt}')

        # Make nodes clickable — link to in-page anchors
        for full_name, nid in nodes.items():
            if full_name != name:  # Don't link to self
                lines.append(f'  click {nid} "#{full_name}"')

        lines.append("```")
        return "\n".join(lines) + "\n\n"

    @staticmethod
    def _build_wrapped_by_index(
        names: list[dict],
    ) -> dict[str, list[str]]:
        """Inverse index for ``HAS_ARGUMENT`` edges: target → [sources]."""
        wrapped_by: dict[str, list[str]] = {}
        for item in names:
            src = item.get("name")
            args = item.get("arguments") or []
            for arg in args:
                target = arg.get("name") if isinstance(arg, dict) else arg
                if target and src:
                    wrapped_by.setdefault(target, []).append(src)
        return wrapped_by

    @staticmethod
    def _render_sibling_nav(
        item: dict,
        wrapped_by: dict[str, list[str]],
    ) -> str:
        """Emit neighbour lists below the entry body."""
        lines: list[str] = []

        def _link(target: str) -> str:
            return f"[{_humanize(target)}](#{target})"

        arguments = item.get("arguments") or []
        arg_links = []
        for arg in arguments:
            target = arg.get("name") if isinstance(arg, dict) else arg
            if target:
                arg_links.append(_link(target))
        if arg_links:
            lines.append(f"**Arguments:** {' · '.join(arg_links)}")

        name = item.get("name", "")
        wrappers = wrapped_by.get(name) or []
        if wrappers:
            lines.append("**Wrapped by:** " + " · ".join(_link(w) for w in wrappers))

        error_variants = item.get("error_variants") or {}
        if isinstance(error_variants, dict) and error_variants:
            variant_links = [
                f"{etype}: {_link(target)}"
                for etype, target in error_variants.items()
                if target
            ]
            if variant_links:
                lines.append("**Error variants:** " + " · ".join(variant_links))

        deprecates = item.get("deprecates")
        if deprecates:
            lines.append(f"**Deprecates:** {_link(deprecates)}")

        superseded_by = item.get("superseded_by")
        if superseded_by:
            lines.append(f"**Superseded by:** {_link(superseded_by)}")

        if not lines:
            return ""
        return "\n\n".join(lines) + "\n\n"

    @staticmethod
    def _render_sources(sources: list[dict]) -> str:
        """Render a collapsed ``<details>`` block listing debug source provenance."""
        if not sources:
            return ""
        lines: list[str] = ["<details>", "<summary>Sources (debug)</summary>", ""]
        for src in sources:
            dd_path = src.get("dd_path")
            signal_id = src.get("signal_id")
            status = src.get("status") or ""
            label = f"dd:{dd_path}" if dd_path else (signal_id or src.get("id", "?"))
            status_str = f" ({status})" if status else ""
            lines.append(f"- `{label}`{status_str}")
        lines += ["", "</details>", ""]
        return "\n".join(lines) + "\n"

    def _render_entry(self, item: dict, wrapped_by: dict[str, list[str]]) -> str:
        """Render a single standard name entry as a compact browsable card."""
        name = item.get("name", "Unknown")
        unit = item.get("unit", "")
        description = _rewrite_name_links(item.get("description", ""))
        documentation = _rewrite_name_links(
            self._fix_markdown_formatting(item.get("documentation", ""))
        )
        kind = item.get("kind", "")

        # Compact card with anchor
        result = f'<div class="sn-card" id="{name}" markdown>\n\n'

        # Title line: name with inline metadata badge
        result += f'<span class="sn-name">{name}</span>'
        badges: list[str] = []
        if unit:
            badges.append(f'<code class="sn-unit">{unit}</code>')
        if kind:
            badges.append(f'<span class="sn-kind">{kind}</span>')
        if badges:
            result += " " + " ".join(badges)
        result += "\n{: .sn-title }\n\n"

        # Description (always visible — the primary browsing content)
        if description:
            result += f"{description}\n\n"

        # Documentation + links + relationships in single collapsible block
        details_parts: list[str] = []
        if documentation:
            details_parts.append(documentation)

        # Mermaid relationship diagram (clickable nodes link to entries)
        mermaid_md = self._render_mermaid(item)
        if mermaid_md:
            details_parts.append(mermaid_md)

        links_md = self._render_links(item.get("links", []))
        if links_md:
            details_parts.append(links_md)

        sibling_md = self._render_sibling_nav(item, wrapped_by)
        if sibling_md:
            details_parts.append(sibling_md)

        sources_md = self._render_sources(item.get("sources") or [])
        if sources_md:
            details_parts.append(sources_md)

        if details_parts:
            result += (
                "<details markdown>\n"
                "<summary>Details</summary>\n\n"
                + "\n\n".join(details_parts)
                + "\n</details>\n\n"
            )

        result += "</div>\n\n"
        return result

    def render_domain_page(self, domain: str) -> str:
        """Generate a single domain page with base-name grouping.

        Parameters
        ----------
        domain : str
            Physics domain key (e.g. "equilibrium", "transport").

        Returns
        -------
        str
            Markdown content for the domain page.
        """
        domains = self.get_domains()
        items = domains.get(domain, [])
        if not items:
            return f"_No standard names found for domain: {domain}_\n"

        domain_display = domain.replace("_", " ").title()
        wrapped_by = self._build_wrapped_by_index(self.load_names())

        result = f"# {domain_display}\n\n"
        result += f"**{len(items)} standard names** in this domain.\n\n"

        # Group items by base name
        base_groups: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            name = item.get("name", "Unknown")
            base = self._parse_base(name)
            base_groups[base].append(item)

        for base_name in sorted(base_groups.keys()):
            base_items = base_groups[base_name]
            result += f"## {_humanize(base_name)} {{: #{base_name} }}\n\n"

            sorted_items = sorted(base_items, key=lambda x: x.get("name", ""))
            for item in sorted_items:
                result += self._render_entry(item, wrapped_by)

        return result

    def render_catalog(self) -> str:
        """Generate complete catalog organized by physics_domain and base name.

        Entries are rendered as anchored card-style blocks (not headings) to
        keep the sidebar/TOC clean. Only domain (H2) and base group (H3)
        levels appear in the page TOC. Long documentation is wrapped in a
        collapsible ``<details>`` block.

        Returns
        -------
        str
            Markdown formatted catalog content.
        """
        result = ""
        domains = self.get_domains()

        if not domains:
            return "_No standard names found in the catalog._"

        wrapped_by = self._build_wrapped_by_index(self.load_names())

        for domain, items in sorted(domains.items()):
            domain_display = domain.replace("_", " ").title()
            result += f"## {domain_display} {{: #{domain} }}\n\n"

            # Group items by base name
            base_groups: dict[str, list[dict]] = defaultdict(list)
            for item in items:
                name = item.get("name", "Unknown")
                base = self._parse_base(name)
                base_groups[base].append(item)

            for base_name in sorted(base_groups.keys()):
                base_items = base_groups[base_name]
                result += f"### {_humanize(base_name)} {{: #{base_name} }}\n\n"

                sorted_items = sorted(base_items, key=lambda x: x.get("name", ""))
                for item in sorted_items:
                    result += self._render_entry(item, wrapped_by)

        return result

    def generate_site(self, output_dir: Path) -> dict:
        """Generate a multi-page site structure with per-domain pages.

        Creates:
        - index.md: overview with stats and domain links
        - catalog/index.md: catalog overview with domain navigation
        - catalog/<domain>.md: per-domain page

        Parameters
        ----------
        output_dir : Path
            Directory to write generated markdown files into.

        Returns
        -------
        dict
            Navigation structure suitable for mkdocs.yml ``nav:`` key.
        """
        domains = self.get_domains()
        stats = self.get_stats()

        catalog_dir = output_dir / "catalog"
        catalog_dir.mkdir(parents=True, exist_ok=True)

        # --- Catalog index page ---
        index_content = "# Standard Names Catalog\n\n"
        index_content += f"**{stats['total_names']} standard names** "
        index_content += f"across **{stats['total_domains']} physics domains**.\n\n"
        index_content += (
            "Browse by domain using the navigation on the left, "
            "or use the search bar to find specific quantities.\n\n"
        )
        index_content += "| Domain | Names |\n|--------|-------|\n"
        for domain in sorted(domains.keys()):
            domain_display = domain.replace("_", " ").title()
            count = len(domains[domain])
            index_content += f"| [{domain_display}]({domain}.md) | {count} |\n"

        (catalog_dir / "index.md").write_text(index_content)

        # --- Per-domain pages ---
        nav_items: list[dict[str, str]] = [
            {"Overview": "catalog/index.md"},
        ]
        for domain in sorted(domains.keys()):
            domain_display = domain.replace("_", " ").title()
            page_content = self.render_domain_page(domain)
            (catalog_dir / f"{domain}.md").write_text(page_content)
            nav_items.append({domain_display: f"catalog/{domain}.md"})

        return {"Catalog": nav_items}

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
        result += f"**Categories:** {stats['total_domains']}\n\n"

        result += "### Categories\n\n"
        for domain, items in sorted(stats["domains"].items()):
            domain_display = domain.replace("_", " ").title()
            count = len(items)
            result += f"- **[{domain_display}]({link_prefix}#{domain})** - {count} standard names\n"

        return result

    def render_navigation(self) -> str:
        """Generate navigation sidebar grouped by domain and base name.

        Individual standard names are omitted — they are anchored cards
        within the page, reachable via search or in-page links.

        Returns
        -------
        str
            Markdown formatted navigation content.
        """
        domains = self.get_domains()

        if not domains:
            return ""

        result = ""

        for domain, items in sorted(domains.items()):
            domain_display = domain.replace("_", " ").title()
            result += f"**[{domain_display}](#{domain})**\n\n"

            base_groups: dict[str, int] = defaultdict(int)
            for item in items:
                name = item.get("name", "Unknown")
                base = self._parse_base(name)
                base_groups[base] += 1

            for base_name in sorted(base_groups.keys()):
                result += f"- [{_humanize(base_name)}](#{base_name})\n"

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
