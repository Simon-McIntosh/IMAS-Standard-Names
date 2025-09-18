from __future__ import annotations

from pathlib import Path
import pytest

from imas_standard_names.paths import resolve_root


def test_resolve_root_none_defaults_to_packaged():
    base = resolve_root(None)
    assert base.exists() and base.is_dir()
    # Should contain at least one YAML or directory for standard names content
    has_content = any(base.rglob("*.yml")) or any(p.is_dir() for p in base.iterdir())
    assert has_content, "Packaged standard_names directory appears empty"


def test_resolve_root_existing_path(tmp_path: Path):
    custom = tmp_path / "my_names"
    custom.mkdir()
    resolved = resolve_root(str(custom))  # pass as str
    assert resolved == custom.resolve()


def test_resolve_root_pattern_matches_first_dir():
    base = resolve_root(None)
    # Collect all subdirectories (recursive) for pattern selection
    all_dirs = sorted([d for d in base.rglob("*") if d.is_dir()])
    assert all_dirs, "No directories found under packaged standard names"
    # Choose the first directory and derive a prefix pattern that should match it
    target = all_dirs[0]
    # Use half the name (at least 1 char) to build a broad prefix pattern
    prefix_len = max(1, len(target.name) // 2)
    prefix = target.name[:prefix_len]
    pattern = prefix + "*"
    # Compute expected match set per algorithm (fnmatch on relative path)
    base_root = resolve_root(None)
    candidates = []
    for d in all_dirs:
        rel = d.relative_to(base_root).as_posix()
        # Equivalent to fnmatch(rel, pattern) when pattern is prefix + '*'
        if rel.startswith(prefix):
            candidates.append(d)
    expected = sorted(candidates)[0]
    matched = resolve_root(pattern)
    assert matched == expected


def test_resolve_root_pattern_not_found():
    with pytest.raises(ValueError):
        resolve_root("___no_such_directory_pattern___")
