"""Catalog utilities for IMAS Standard Names.

This module provides a high-level `StandardNameCatalog` class that can:
- Load all per-file standard name YAML definitions from a directory tree
- Expose them as validated Pydantic model instances (`schema.StandardName`)
- Emit JSON artifacts (full catalog + lightweight index + relationship graph)
- Offer a CLI entrypoint for build pipelines (e.g. docs or downstream tooling)

"""

from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Dict, List, Any
import json
import click

from imas_standard_names import schema


@dataclass
class StandardNameCatalog:
    """In-memory catalog of Standard Names sourced from a directory tree.

    Parameters
    ----------
    root : Path | str
        Root directory containing per-name YAML files (recursive scan).
    strict : bool
        When True (default) raise on duplicate names or parse errors.
    """

    root: Path | str
    strict: bool = True
    entries: Dict[str, schema.StandardName] = field(default_factory=dict, init=False)

    def __post_init__(self):  # pragma: no cover - simple path normalization
        self._resolve_root()

    def _resolve_root(self):  # pragma: no cover - called in __post_init__
        """Resolve the user-supplied `root` specification to a concrete Path.

        Accepted forms (examples):
        - ""                         -> <pkg>/resources/standard_names
        - "standard_names"            -> <pkg>/resources/standard_names
        - "equilibrium"               -> <pkg>/resources/standard_names/equilibrium
        - "equilibrium/subset"        -> <pkg>/resources/standard_names/equilibrium/subset
        - "standard_names/equilibrium"-> <pkg>/resources/standard_names/equilibrium
        - Path()/absolute path        -> used as-is (outside package allowed)
        - Existing filesystem path string (absolute) -> used as-is

        Resolution rules for strings (precedence):
        1. If empty or exactly "standard_names" -> base directory.
        2. If absolute path -> use directly.
        3. If first segment == "standard_names" -> drop that segment and
           interpret remainder under base.
        4. Otherwise treat the entire relative path (may contain separators)
           as subpath under base.

        This design lets simple tokens and relative subtrees be specified
        without needing full filesystem paths while still allowing external
        absolute paths when required.
        """
        original = self.root
        try:
            package_root = Path(importlib_resources.files(__package__))  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - defensive fallback
            package_root = Path(__file__).resolve().parent
        standard_names_root = package_root / "resources" / "standard_names"

        match original:
            # Already a Path
            case Path() as p:
                self.root = p.expanduser().resolve()

            # Empty string or explicit base token
            case str() as s if s.strip() in ("", "standard_names"):
                self.root = standard_names_root

            # Absolute path string
            case str() as s if Path(s).is_absolute():
                self.root = Path(s).expanduser().resolve()

            # Any relative string (optionally starting with standard_names/) -> under base
            case str() as s:
                parts = [p for p in s.replace("\\", "/").split("/") if p]
                if parts and parts[0] == "standard_names":  # drop leading token alias
                    parts = parts[1:]
                self.root = (
                    (standard_names_root.joinpath(*parts)).expanduser().resolve()
                )

            # Fallback coercion
            case _:
                self.root = Path(str(original)).expanduser().resolve()

    def load(self) -> "StandardNameCatalog":
        """Traverse root directory and load all standard name YAML files.

        Returns self for fluent chaining.
        """
        root_path = self.root if isinstance(self.root, Path) else Path(self.root)
        if not root_path.exists():  # pragma: no cover - defensive
            raise FileNotFoundError(f"Catalog root does not exist: {root_path}")

        matches = list(root_path.rglob("*.yml")) + list(root_path.rglob("*.yaml"))
        for file in sorted(matches):
            if file.is_dir():  # skip directories named with .yml/.yaml (rare)
                continue
            try:
                entry = schema.load_standard_name_file(file)
            except Exception:  # pragma: no cover - defensive
                if self.strict:
                    raise
                else:
                    continue
            if entry.name in self.entries:
                msg = f"Duplicate standard name '{entry.name}' (file: {file})"
                if self.strict:
                    raise ValueError(msg)
                continue
            self.entries[entry.name] = entry
        return self

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        """Return full catalog as mapping name -> serialized model dict."""
        return {
            name: e.model_dump(exclude_none=True, exclude_defaults=True)
            for name, e in self.entries.items()
        }

    def index(self) -> List[Dict[str, Any]]:
        """Return lightweight list of entries (for quick lookups / UIs)."""
        return [
            {
                "name": e.name,
                "kind": getattr(e, "kind", None),
                "status": getattr(e, "status", None),
                "unit": getattr(e, "unit", ""),
                "tags": getattr(e, "tags", []),
            }
            for e in self.entries.values()
        ]

    def relationships(self) -> Dict[str, Dict[str, Any]]:
        """Return simple relationship graph including provenance.

        Structure:
          name -> {
            components: {axis: component_name} | {},
            magnitude: str | None,
            provenance: {mode: operator|expression, ...} | None,
            parent_vector: str | None,
            axis: str | None
          }
        """
        rel: Dict[str, Dict[str, Any]] = {}
        for name, e in self.entries.items():
            data = e.model_dump()
            rel[name] = {
                "components": data.get("components", {}) or {},
                "magnitude": data.get("magnitude"),
                "provenance": data.get("provenance"),
                "parent_vector": data.get("parent_vector"),
                "axis": data.get("axis"),
            }
        return rel

    # ------------------------------------------------------------------
    # Artifact writers
    # ------------------------------------------------------------------
    def write_json_artifacts(self, out_dir: Path | str) -> List[Path]:
        """Write standard catalog JSON artifacts into out_dir.

        Creates (overwriting):
          - catalog.json        (full serialized mapping)
          - index.json          (lightweight summary list)
          - relationships.json  (simplified relationship graph)
        Returns list of written file paths.
        """
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "catalog.json": self.as_dict(),
            "index.json": self.index(),
            "relationships.json": self.relationships(),
        }
        written: List[Path] = []
        for filename, payload in artifacts.items():
            path = out / filename
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=False)
            written.append(path)
        return written


# ----------------------------------------------------------------------
# CLI entrypoint
# ----------------------------------------------------------------------
@click.command(name="build_catalog")
@click.argument("root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument(
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("imas_standard_names/resources/artifacts"),
)
@click.option("--quiet", is_flag=True, help="Suppress non-error output")
def build_catalog_cli(root: Path, out_dir: Path, quiet: bool):
    """Build JSON catalog artifacts from ROOT directory into OUT_DIR.

    Example:
      build_catalog resources/standard_names imas_standard_names/resources/artifacts
    """
    catalog = StandardNameCatalog(root).load()
    written = catalog.write_json_artifacts(out_dir)
    if not quiet:
        for path in written:
            click.echo(f"Wrote {path}")


__all__ = [
    "StandardNameCatalog",
    "build_catalog_cli",
]


def _main():  # pragma: no cover - convenience runtime entry
    """Load catalog from packaged resources and write JSON artifacts.

    This allows:  python -m imas_standard_names.catalog
    to quickly materialize/update JSON artifacts for downstream tools.
    """
    pkg_root = Path(__file__).parent
    root = pkg_root / "resources" / "standard_names"
    out_dir = pkg_root / "resources" / "artifacts"
    catalog = StandardNameCatalog(root).load()
    written = catalog.write_json_artifacts(out_dir)
    print(f"Loaded {len(catalog.entries)} standard names from {root}")
    for w in written:
        print(f"Wrote {w}")


if __name__ == "__main__":  # pragma: no cover
    print(StandardNameCatalog("equilibrium").load())
