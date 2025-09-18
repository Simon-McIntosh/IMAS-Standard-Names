"""Path & resource resolution utilities for standard names.

This module centralises logic for resolving the *root* directory used by
``YamlStore`` / ``StandardNameRepository`` so that repository.py stays lean.

Public API
----------
resolve_root(root: str | Path | None) -> Path
    Resolve a user supplied value into a concrete filesystem directory.
    * ``None`` -> packaged resources/standard_names
    * existing path -> returned as absolute path
    * string pattern -> first directory under packaged tree matching fnmatch

The packaged base path is treated read-only; pattern matching is performed
against the POSIX relative path of each nested directory under the packaged
``standard_names`` tree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union
import importlib.resources as ir
import fnmatch

RESOURCES_PACKAGE = f"{__package__}.resources"
STANDARD_NAMES_DIRNAME = "standard_names"


def _package_standard_names_root() -> Path:
    traversable = ir.files(RESOURCES_PACKAGE).joinpath(STANDARD_NAMES_DIRNAME)
    with ir.as_file(traversable) as base_fs_path:
        return Path(base_fs_path)


def _iter_standard_names_dirs() -> Iterable[Path]:
    base = _package_standard_names_root()
    for d in base.rglob("*"):
        if d.is_dir():
            yield d


def _first_match(pattern: str, base: Path, candidates: Iterable[Path]) -> Path:
    """Return first lexicographically sorted directory matching pattern.

    Raises ValueError if no match.
    """
    norm_pattern = pattern.replace("\\", "/")
    matched: list[Path] = []
    for d in candidates:
        rel = d.relative_to(base).as_posix()
        if fnmatch.fnmatch(rel, norm_pattern):
            matched.append(d)
    if not matched:
        raise ValueError(
            f"Could not resolve pattern '{pattern}' inside packaged '{STANDARD_NAMES_DIRNAME}'"
        )
    return sorted(matched)[0]


def resolve_root(root: Union[str, Path, None]) -> Path:
    """Resolve a repository root.

    Uses structural pattern matching for clarity.

    Cases:
        * None -> packaged base
        * Path  -> absolute, expanded
        * str existing path -> resolved
        * str pattern -> first matching directory under packaged base
    """

    match root:
        case None:
            return _package_standard_names_root()
        case Path() as p:
            return p.expanduser().resolve()
        case str() as s:
            p = Path(s).expanduser()
            if p.exists():
                return p.resolve()
            base = _package_standard_names_root()
            return _first_match(s, base, _iter_standard_names_dirs())
        case _:
            raise TypeError("root must be None, str, or Path")


__all__ = ["resolve_root", "STANDARD_NAMES_DIRNAME", "RESOURCES_PACKAGE"]
