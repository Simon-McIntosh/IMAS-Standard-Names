"""Catalog rendering for Standard Names documentation.

Provides reusable catalog rendering logic that can be used by both
the main project docs and external catalog repositories.

The renderer groups entries by *locus* (the structural or spatial
"what is this attached to" token extracted by the ISN grammar IR
parser). Locus-first grouping clusters names that refer to the same
physical object/region/position together — e.g. all reflectometer
antenna properties appear in one block, all separatrix quantities in
another. Names without a locus fall back to grouping by their
physical-base token (e.g. all magnetic-flux variants together).

The visual design emphasises the standard name itself as the primary
heading for each entry. Group ordering is internal — no group
heading clutter is rendered, so the page TOC is a flat list of
canonical names.
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


_UNIT_SUP_RE = re.compile(r"\^(-?\d+)")


def _format_unit(unit: str) -> str:
    """Render a SI shorthand unit string as HTML with proper superscripts.

    ``m^2``  → ``m<sup>2</sup>``
    ``m.s^-1`` → ``m·s<sup>-1</sup>``  (the ``.`` separator becomes ``·``)
    """
    if not unit:
        return ""
    text = unit.replace(".", "·")
    return _UNIT_SUP_RE.sub(r"<sup>\1</sup>", text)


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
        """Demote nested markdown headers to bold paragraphs.

        Documentation content sits beneath an entry's H2 name heading.
        Inline ``# … ####`` lines from the source would otherwise leak
        into the page TOC and break the flat structure.
        """
        if not text:
            return ""

        text = text.strip()
        text = text.replace("\\n", "\n")

        text = re.sub(r"^#{1,6}\s+(.+)$", r"**\1**", text, flags=re.MULTILINE)

        paragraphs = text.split("\n\n")
        processed: list[str] = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                processed.append(paragraph)

        result = "\n\n".join(processed)
        result = re.sub(r"\n\s*\$\$", "\n\n$$", result)
        result = re.sub(r"\$\$\s*\n", "$$\n\n", result)

        return result

    @staticmethod
    def _parse_ir(name: str):
        """Parse a name to its IR; returns ``None`` on failure."""
        try:
            from ..grammar.parser import parse as ir_parse  # noqa: PLC0415

            result = ir_parse(name)
            return result.ir
        except Exception:
            return None

    @classmethod
    def _parse_base(cls, name: str) -> str:
        """Return the physical-base / geometric-base token (best effort).

        Kept for backwards compatibility with downstream callers and
        for use as a fallback grouping key when no locus is present.
        """
        ir = cls._parse_ir(name)
        if ir is not None and getattr(ir, "base", None) is not None:
            token = getattr(ir.base, "token", None)
            if token:
                return token

        try:
            from ..grammar.model import parse_standard_name  # noqa: PLC0415

            parsed = parse_standard_name(name)
            base = parsed.physical_base or ""
            if not base and parsed.geometric_base:
                gb = parsed.geometric_base
                base = gb.value if hasattr(gb, "value") else str(gb)
            if parsed.transformation and base.startswith("of_"):
                base = base[3:]
                wrt_idx = base.find("_with_respect_to_")
                if wrt_idx > 0:
                    base = base[:wrt_idx]
            return base or "unknown"
        except Exception:
            return "unknown"

    @classmethod
    def _parse_locus(cls, name: str) -> tuple[str, str] | None:
        """Return ``(token, relation)`` for a locus reference or ``None``.

        Recognises ``_of_``, ``_at_``, and ``_over_`` patterns. The
        token is the bare locus name (e.g. ``magnetic_axis``, no
        preposition prefix); the relation is one of ``of``, ``at``,
        ``over``.
        """
        ir = cls._parse_ir(name)
        if ir is not None and getattr(ir, "locus", None) is not None:
            locus = ir.locus
            relation_value = (
                locus.relation.value
                if hasattr(locus.relation, "value")
                else str(locus.relation)
            )
            return (locus.token, relation_value)
        return None

    @classmethod
    def _group_key(cls, name: str) -> tuple[int, str]:
        """Return a sortable ``(priority, key)`` tuple for grouping.

        Priorities:
        - 0 = locus (object / region / position) — clusters by
          structural locality (most distinctive)
        - 1 = physical / geometric base — clusters by quantity
        - 2 = unknown / unparseable — bucket at end
        """
        locus = cls._parse_locus(name)
        if locus is not None:
            return (0, locus[0])
        base = cls._parse_base(name)
        if base and base != "unknown":
            return (1, base)
        return (2, "unknown")

    # ------------------------------------------------------------------
    # Visual rendering helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _render_links(links: list[str]) -> str:
        """Render ``links:`` as markdown; ``name:X`` → humanized in-page anchor.

        Emitted as plain markdown so the link syntax resolves; the
        leading ``.sn-see-also`` class is attached via ``attr_list``
        for CSS targeting.
        """
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
        return "**See also:** " + " · ".join(parts) + "\n{: .sn-see-also }\n\n"

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
        """Render a Mermaid hierarchy when structural fields exist.

        Emitted as a plain ```mermaid``` fenced block (no enclosing
        ``<details>``) so the diagram renders immediately on page load.
        Nodes carry humanised labels and are clickable to in-page
        anchors.
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
        nodes: dict[str, str] = {}
        node_counter = 0

        def _node(full_name: str) -> str:
            nonlocal node_counter
            if full_name not in nodes:
                nodes[full_name] = f"n{node_counter}"
                node_counter += 1
            return nodes[full_name]

        def _decl(full_name: str) -> str:
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

        for full_name, nid in nodes.items():
            if full_name != name:
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
        """Render compact sibling navigation (arguments, wrappers, variants).

        Emitted as plain markdown paragraphs tagged with ``.sn-meta``
        via ``attr_list``. Plain markdown is required so the embedded
        ``[label](#anchor)`` links actually resolve.
        """
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
            lines.append("**Arguments:** " + " · ".join(arg_links))

        name = item.get("name", "")
        wrappers = wrapped_by.get(name) or []
        if wrappers:
            lines.append("**Wrapped by:** " + " · ".join(_link(w) for w in wrappers))

        error_variants = item.get("error_variants") or {}
        if isinstance(error_variants, dict) and error_variants:
            variant_parts = [
                f"{etype}: {_link(target)}"
                for etype, target in error_variants.items()
                if target
            ]
            if variant_parts:
                lines.append("**Error variants:** " + " · ".join(variant_parts))

        deprecates = item.get("deprecates")
        if deprecates:
            lines.append(f"**Deprecates:** {_link(deprecates)}")

        superseded_by = item.get("superseded_by")
        if superseded_by:
            lines.append(f"**Superseded by:** {_link(superseded_by)}")

        if not lines:
            return ""
        # Each line is its own paragraph carrying the .sn-meta class.
        return "\n\n".join(line + "\n{: .sn-meta }" for line in lines) + "\n\n"

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
        """Render a single standard name entry with a name-as-heading layout.

        Layout:
        ::

            ## name { #name .sn-name }
            <meta line: unit · sources count>
            > one-line description
            documentation paragraphs
            ```mermaid …``` (inline if present)
            <see-also / sibling-nav lines>
        """
        name = item.get("name", "Unknown")
        unit = item.get("unit", "")
        description = _rewrite_name_links(item.get("description", ""))
        documentation = _rewrite_name_links(
            self._fix_markdown_formatting(item.get("documentation", ""))
        )

        result = f"## {name} {{ #{name} .sn-name }}\n\n"

        meta_bits: list[str] = []
        if unit:
            meta_bits.append(f'<span class="sn-unit">{_format_unit(unit)}</span>')
        kind = item.get("kind")
        if kind and kind not in ("scalar", None):
            meta_bits.append(f'<span class="sn-kind">{kind}</span>')
        sources = item.get("sources") or []
        if sources:
            meta_bits.append(
                f'<span class="sn-sources">{len(sources)} source'
                f"{'s' if len(sources) != 1 else ''}</span>"
            )
        if meta_bits:
            result += '<p class="sn-meta-line">' + " · ".join(meta_bits) + "</p>\n\n"

        if description:
            result += f"_{description}_\n\n"

        if not documentation:
            result += (
                '<p class="sn-badge sn-badge-pending">documentation pending</p>\n\n'
            )

        if documentation:
            result += f'<div class="sn-docs" markdown>\n\n{documentation}\n\n</div>\n\n'

        mermaid_md = self._render_mermaid(item)
        if mermaid_md:
            result += f'<div class="sn-mermaid" markdown>\n\n{mermaid_md}</div>\n\n'

        links_md = self._render_links(item.get("links", []))
        if links_md:
            result += links_md

        sibling_md = self._render_sibling_nav(item, wrapped_by)
        if sibling_md:
            result += sibling_md

        return result

    def _ordered_items(self, items: list[dict]) -> list[dict]:
        """Return items ordered by locus-first grouping.

        Within each group, entries are sorted alphabetically. Groups
        are ordered largest first (so visually clustered topics appear
        at the top of the page), then alphabetically by key as a
        tie-breaker. Locus groups (priority 0) win ties against base
        groups (priority 1).
        """
        groups: dict[tuple[int, str], list[dict]] = defaultdict(list)
        for item in items:
            key = self._group_key(item.get("name", ""))
            groups[key].append(item)

        def _sort_key(entry: tuple[tuple[int, str], list[dict]]):
            (priority, token), bucket = entry
            return (-len(bucket), priority, token)

        ordered: list[dict] = []
        for _key, bucket in sorted(groups.items(), key=_sort_key):
            bucket.sort(key=lambda x: x.get("name", ""))
            ordered.extend(bucket)
        return ordered

    def render_domain_page(self, domain: str) -> str:
        """Generate a single domain page with locus-first ordering.

        The page renders a flat list of standard-name entries. Each
        entry is its own H2 (the canonical snake_case name), so the
        page TOC lists every name. Internal ordering follows
        :meth:`_ordered_items` — entries that share a locus or base
        appear together without any visible group heading.
        """
        domains = self.get_domains()
        items = domains.get(domain, [])
        if not items:
            return f"_No standard names found for domain: {domain}_\n"

        domain_display = domain.replace("_", " ").title()
        wrapped_by = self._build_wrapped_by_index(self.load_names())

        result = f"# {domain_display}\n\n"
        result += (
            f'<p class="sn-domain-summary">'
            f"<strong>{len(items)}</strong> standard names in this domain."
            f"</p>\n\n"
        )

        for item in self._ordered_items(items):
            result += self._render_entry(item, wrapped_by)

        return result

    def render_catalog(self) -> str:
        """Generate complete catalog organized by physics domain.

        Each domain is an H1 section; entries within follow the same
        locus-first ordering used on per-domain pages. Entries are H2
        — anchored, visible in the TOC, and free of redundant group
        headings.
        """
        result = ""
        domains = self.get_domains()

        if not domains:
            return "_No standard names found in the catalog._"

        wrapped_by = self._build_wrapped_by_index(self.load_names())

        for domain, items in sorted(domains.items()):
            domain_display = domain.replace("_", " ").title()
            result += f"## {domain_display} {{: #{domain} }}\n\n"
            for item in self._ordered_items(items):
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

        index_content = "# Standard Names Catalog\n\n"
        index_content += (
            f'<p class="sn-domain-summary">'
            f"<strong>{stats['total_names']}</strong> standard names across "
            f"<strong>{stats['total_domains']}</strong> physics domains."
            f"</p>\n\n"
        )
        index_content += (
            "Browse by domain using the navigation, or use the search bar "
            "(top right) to find specific quantities.\n\n"
        )
        index_content += '<div class="sn-domain-grid" markdown>\n\n'
        index_content += "| Domain | Names |\n|--------|------:|\n"
        for domain in sorted(domains.keys()):
            domain_display = domain.replace("_", " ").title()
            count = len(domains[domain])
            index_content += f"| [{domain_display}]({domain}.md) | {count} |\n"
        index_content += "\n</div>\n"

        (catalog_dir / "index.md").write_text(index_content)

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
            result += (
                f"- **[{domain_display}]({link_prefix}{domain}/)** - "
                f"{count} standard names\n"
            )

        return result

    def render_navigation(self) -> str:
        """Generate navigation listing all canonical names per domain.

        Names are listed verbatim (snake_case) — the same form used as
        their in-page anchors — so the navigation doubles as a direct
        index of the catalog.
        """
        domains = self.get_domains()

        if not domains:
            return ""

        result = ""
        for domain, items in sorted(domains.items()):
            domain_display = domain.replace("_", " ").title()
            result += f"**[{domain_display}](#{domain})**\n\n"
            for item in self._ordered_items(items):
                name = item.get("name", "")
                if name:
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
