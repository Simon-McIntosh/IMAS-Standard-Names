"""Tree view for IMAS Standard Names resources.

This module provides a small composable dataclass model that mirrors the
directory structure under ``imas_standard_names/resources/standard_names`` and
utilities to render that structure as a Textual ``Tree`` widget. YAML files
are parsed and their (single) root mapping is expanded into child nodes so the
user can explore the contents directly inside the tree.

The structure purposefully stays *simple* so it can later be re‑used to
calculate and visualise proposed changes (diffs) to the tree: you only need to
compare instances of these dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Any
import importlib.resources as ir
import yaml

from textual.widgets import Tree
from rich.text import Text

RESOURCES_PACKAGE = "imas_standard_names.resources"
STANDARD_NAMES_DIRNAME = "standard_names"


# ---------------------------------------------------------------------------
# Dataclass model
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class YamlFileNode:
    """Leaf node representing a single standard name YAML file.

    Attributes
    ----------
    path: Path to the YAML file on disk.
    name: Display name (file stem).
    data: Parsed YAML mapping (a ``dict``). If the YAML uses the legacy
          ``{name: {...}}`` structure we unwrap the top-level key so ``data``
          becomes just the inner mapping.
    """

    path: Path
    name: str
    data: dict[str, Any] = field(repr=False)

    @classmethod
    def from_file(cls, file_path: Path) -> "YamlFileNode":
        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        # Normalise legacy format {name: {...}} to inner mapping
        if isinstance(raw, dict) and len(raw) == 1 and next(iter(raw)) != "name":
            only_key = next(iter(raw))
            inner = raw[only_key]
            if isinstance(inner, dict):
                data = inner
                name = only_key
            else:  # Fallback – keep as is
                data = raw
                name = file_path.stem
        else:
            data = (
                {k: v for k, v in raw.items() if k != "name"}
                if isinstance(raw, dict)
                else {}
            )
            name = (
                raw.get("name", file_path.stem)
                if isinstance(raw, dict)
                else file_path.stem
            )
        return cls(path=file_path, name=name, data=data)

    def to_dict(self) -> dict[str, Any]:  # for potential JSON display later
        return {"name": self.name, **self.data}


@dataclass(slots=True)
class DirectoryNode:
    """A directory in the resources tree.

    Contains nested ``DirectoryNode`` and ``YamlFileNode`` children.
    """

    path: Path
    name: str
    directories: list["DirectoryNode"] = field(default_factory=list)
    files: list[YamlFileNode] = field(default_factory=list)

    @classmethod
    def from_path(cls, path: Path) -> "DirectoryNode":
        directories: list[DirectoryNode] = []
        files: list[YamlFileNode] = []
        for child in sorted(path.iterdir()):
            if child.name.startswith("."):
                continue
            if child.is_dir():
                directories.append(cls.from_path(child))
            elif child.suffix in {".yml", ".yaml"}:
                try:
                    files.append(YamlFileNode.from_file(child))
                except Exception as exc:  # pragma: no cover - defensive
                    # Represent parse errors as empty node; could log later.
                    files.append(
                        YamlFileNode(
                            path=child, name=child.stem, data={"error": str(exc)}
                        )
                    )
        return cls(path=path, name=path.name, directories=directories, files=files)

    # Iteration utilities (useful for future diffing)
    def iter_files(self) -> Iterable[YamlFileNode]:
        for f in self.files:
            yield f
        for d in self.directories:
            yield from d.iter_files()


@dataclass(slots=True)
class ResourcesTree:
    """Root container for the standard names resource tree."""

    root: DirectoryNode

    @classmethod
    def load(cls) -> "ResourcesTree":
        traversable = ir.files(RESOURCES_PACKAGE).joinpath(STANDARD_NAMES_DIRNAME)
        # Ensure we have a concrete filesystem path (needed for rglob / iterdir)
        with ir.as_file(traversable) as fs_path:
            return cls(root=DirectoryNode.from_path(Path(fs_path)))

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def build_tree_widget(self) -> Tree[dict | None]:
        """Return a Textual Tree widget populated with the resource data.

        Changes vs previous implementation:
        * The top-level directory name (``standard_names``) is no longer
          duplicated as a child. The tree root is a *virtual* container whose
          immediate children are the first category directories (e.g.
          ``equilibrium``, ``magnetic_field`` ...).
                * Each standard name file exposes its YAML mapping as an expandable
                    JSON-style structure (following the provided ``add_json`` pattern)
                    so individual keys / values are navigable.
        """

        tree: Tree[dict | None] = Tree("standard_names", id="names_tree")

        def add_directory(dir_node: DirectoryNode, parent):  # recursive closure
            dir_branch = parent.add(dir_node.name, expand=False, data=None)
            for subdir in dir_node.directories:
                add_directory(subdir, dir_branch)
            for file_node in dir_node.files:
                # Create a node for the file, then attach JSON-style children
                file_branch = dir_branch.add(file_node.name, data=file_node.data)
                # Add JSON representation of YAML (excluding the name key)
                self.add_json(file_branch, file_node.data)

        # Skip inserting the root directory itself to avoid repetition – go
        # straight to its children.
        for top_dir in self.root.directories:
            add_directory(top_dir, tree.root)
        # If there are any loose files at the top level include them too.
        for top_file in self.root.files:
            file_branch = tree.root.add(top_file.name, data=top_file.data)
            self.add_json(file_branch, top_file.data)

        tree.root.expand()
        return tree

    # ------------------------------------------------------------------
    # JSON display helper (pattern provided by user)
    # ------------------------------------------------------------------
    @staticmethod
    def add_json(node, json_data: object) -> None:  # type: ignore[override]
        """Populate a ``Tree`` node with a JSON-style expandable structure.

        Follows the user-provided pattern: dictionaries and lists become
        expandable nodes labeled with ``{}`` or ``[]``. Scalars are leaf nodes
        showing ``key=value`` with syntax highlighting.

        Args:
            node: A ``TreeNode`` (kept untyped at runtime for compatibility).
            json_data (object): Parsed mapping / sequence / scalar.
        """

        from rich.highlighter import (
            ReprHighlighter,
        )  # local import to reduce startup cost

        highlighter = ReprHighlighter()

        def add_node(name: str, parent_node, data: object) -> None:
            if isinstance(data, dict):
                # Label current node (if it has no existing label beyond name)
                if name:
                    parent_node.set_label(Text(f"{{}} {name}"))
                for key, value in data.items():
                    child = parent_node.add("")
                    add_node(key, child, value)
            elif isinstance(data, list):
                if name:
                    parent_node.set_label(Text(f"[] {name}"))
                for index, value in enumerate(data):
                    child = parent_node.add("")
                    add_node(str(index), child, value)
            else:
                parent_node.allow_expand = False
                if name:
                    label = Text.assemble(
                        Text.from_markup(f"[b]{name}[/b]="), highlighter(repr(data))
                    )
                else:
                    label = Text(repr(data))
                parent_node.set_label(label)

        # We don't want to wrap in an extra "JSON" node; we attach children directly.
        if isinstance(json_data, (dict, list)):
            for key, value in (
                json_data.items()
                if isinstance(json_data, dict)
                else enumerate(json_data)
            ):
                child = node.add("")
                add_node(str(key), child, value)
        else:  # scalar root (unlikely for YAML standard names)
            add_node("", node, json_data)


# Convenience factory used by the App
def build_standard_names_tree() -> Tree[dict | None]:
    return ResourcesTree.load().build_tree_widget()


__all__ = [
    "YamlFileNode",
    "DirectoryNode",
    "ResourcesTree",
    "build_standard_names_tree",
]
