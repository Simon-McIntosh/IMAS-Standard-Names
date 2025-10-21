"""Path resolution utilities for IMAS standard names data.

The :class:`CatalogPaths` value object normalizes two user inputs into two
resolved outputs:

Inputs
======
* ``yaml``: directory or pattern (``None`` -> packaged ``resources/standard_names``)
* ``catalog``: directory or explicit ``.db`` file (``None`` -> `<yaml_path>/.catalog/catalog.db`)

Outputs
=======
* ``yaml_path``: resolved directory containing YAML definition files
* ``catalog_path``: absolute path to the SQLite catalog file (always includes filename)

Rules
=====
* Wildcards (``* ? []``) are supported only for ``yaml`` and are matched
    against subdirectories of the packaged ``standard_names`` tree.
* If ``catalog`` is a directory (exists or not) the filename ``catalog.db`` (or
    the provided ``catalog_filename`` override) is appended.
* If ``catalog`` ends with ``.db`` it is treated as the final file path. A
    relative ``.db`` filename is interpreted relative to ``yaml_path``.
* No filesystem changes are performed automatically; call
    :meth:`ensure_catalog_dir` to create the parent directory of the catalog file.

This design keeps construction side‑effect free and explicit while allowing a
concise interface for common defaults and overrides.
"""

from __future__ import annotations

import fnmatch
import importlib.resources as ir
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

RESOURCES_DIRNAME = "resources"
STANDARD_NAMES_DIRNAME = "standard_names"
CATALOG_DIRNAME = ".catalog"


@dataclass
class CatalogPaths:
    """Resolve source YAML directory and catalog SQLite file path.

    Parameters
    ----------
    yaml : Path | str | None
        Directory, pattern, or ``None`` (use packaged standard names).
    catalog : Path | str | None
        Directory or explicit ``.db`` file path. ``None`` -> default under
        ``yaml_path``: ``.catalog/catalog.db``.
    catalog_filename : str
        Filename used when ``catalog`` is a directory (default ``catalog.db``).

    Attributes
    ----------
    yaml_path : Path
        Resolved YAML directory.
    catalog_path : Path
        Absolute path to catalog SQLite file (always includes filename).
    catalog_filename : str
        Final filename component (updated if an explicit file path was given).
    """

    yaml: Path | str | None = None
    catalog: Path | str | None = None
    catalog_filename: str = "catalog.db"

    yaml_path: Path = field(init=False)
    catalog_path: Path = field(init=False)

    # ---------------------------------------------------------------------
    def __post_init__(self) -> None:
        self.yaml_path = self._resolve_yaml(self.yaml)
        self.catalog_path = self._resolve_catalog(self.catalog, self.catalog_filename)

    # Public helper -------------------------------------------------------
    def ensure_catalog_dir(self) -> CatalogPaths:
        """Create the parent directory for `catalog_path` if missing."""
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        return self

    # Resource roots ------------------------------------------------------
    # Simple instance attributes instead of cached_property
    @property
    def resources_root(self) -> Path:
        files_obj = ir.files(__package__) / RESOURCES_DIRNAME
        with ir.as_file(files_obj) as p:
            path = Path(p)
            if not path.exists():  # pragma: no cover
                # Create if missing - allows tests to run with empty package
                path.mkdir(parents=True, exist_ok=True)
            if not path.is_dir():  # pragma: no cover
                raise FileNotFoundError(
                    f"Resources path exists but is not a directory: {path}"
                )
            return path

    @property
    def standard_names_root(self) -> Path:
        std = self.resources_root / STANDARD_NAMES_DIRNAME
        if not std.exists():  # pragma: no cover
            # Create the directory if it doesn't exist to avoid startup errors
            std.mkdir(parents=True, exist_ok=True)
        if not std.is_dir():  # pragma: no cover
            raise FileNotFoundError(
                f"Standard names directory '{STANDARD_NAMES_DIRNAME}' exists but is not a directory: {std}"
            )
        return std

    # Internal resolution helpers -----------------------------------------
    @staticmethod
    def _iter_tree(base: Path, include_files: bool) -> Iterable[Path]:
        for p in base.rglob("*"):
            if p.is_dir() or (include_files and p.is_file()):
                yield p

    @classmethod
    def _first_match(cls, pattern: str, base: Path, include_files: bool) -> Path:
        norm = pattern.replace("\\", "/")
        matches: list[Path] = []
        for p in cls._iter_tree(base, include_files):
            rel = p.relative_to(base).as_posix()
            if fnmatch.fnmatch(rel, norm) or fnmatch.fnmatch(p.name, norm):
                matches.append(p)
        if not matches:
            raise ValueError(f"Could not resolve pattern '{pattern}' inside '{base}'")
        return sorted(matches)[0]

    @classmethod
    def _resolve_under(cls, base: Path, spec: str, include_files: bool) -> Path:
        if not any(ch in spec for ch in "*?[]"):
            candidate = base / spec if spec not in ("", ".") else base
            if candidate.exists():
                return candidate.resolve()
            # Non-wildcard but non-existing -> return candidate (allow creation)
            return candidate.resolve()
        # Wildcard case
        return cls._first_match(spec, base, include_files).resolve()

    def _resolve_yaml(self, value: Path | str | None) -> Path:
        if value is None:
            return self.standard_names_root
        if isinstance(value, Path):
            return value.expanduser().resolve()
        s = value.strip()
        if s == "":
            return self.standard_names_root

        # Check if it's an absolute path
        if Path(s).is_absolute():
            p = Path(s).expanduser().resolve()
            return p

        # For relative paths (../, ./), resolve relative to the project root
        # (parent of the package directory) instead of CWD
        if s.startswith(("../", "./", "..\\", ".\\")):
            # Get project root: go up from package directory
            package_dir = Path(__file__).parent  # imas_standard_names/
            project_root = package_dir.parent  # imas-standard-names/
            p = (project_root / s).expanduser().resolve()
            return p

        # Allow shorthand "standard_names/..."
        if s.startswith(f"{STANDARD_NAMES_DIRNAME}/"):
            rel = s[len(STANDARD_NAMES_DIRNAME) + 1 :]
        elif s == STANDARD_NAMES_DIRNAME:
            rel = ""
        else:
            # For other cases, treat as pattern or subdir within packaged resources
            rel = s
        base = self.standard_names_root
        if rel in ("", "."):
            return base
        if any(ch in rel for ch in "*?[]"):
            return self._first_match(rel, base, include_files=False).resolve()
        return (
            (base / rel).resolve() if (base / rel).exists() else (base / rel).resolve()
        )

    def _resolve_catalog(self, value: Path | str | None, default_name: str) -> Path:
        # If user gives None -> default directory inside yaml_root
        if value is None:
            target_dir = self.yaml_path / CATALOG_DIRNAME
            return (target_dir / default_name).resolve()
        if isinstance(value, Path):
            p = value.expanduser().resolve()
            if p.is_dir():
                return (p / default_name).resolve()
            if p.suffix == ".db":
                self.catalog_filename = p.name
                return p
            return (p / default_name).resolve()
        s = value.strip()
        if s == "":
            return (self.yaml_path / CATALOG_DIRNAME / default_name).resolve()
        # If it looks like a filename
        if s.endswith(".db"):
            raw_path = Path(s).expanduser()
            if raw_path.is_absolute():
                return raw_path.resolve()
            # Treat relative filename as under yaml_path
            return (self.yaml_path / raw_path).resolve()
        # Treat as directory (relative -> under yaml_root)
        d = Path(s).expanduser()
        if not d.is_absolute():
            d = (self.yaml_path / d).resolve()
        else:
            d = d.resolve()
        return (d / default_name).resolve()


__all__ = ["CatalogPaths", "STANDARD_NAMES_DIRNAME", "CATALOG_DIRNAME"]
