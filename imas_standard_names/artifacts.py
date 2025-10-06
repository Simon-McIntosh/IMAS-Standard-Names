"""Artifact builder utilities wrapping repository snapshots.

Provides a stable function to emit JSON artifacts (catalog/index/relationships)
from any StandardNameRepository implementation, decoupling higher-level
commands from storage specifics.
"""

from __future__ import annotations

from pathlib import Path

from .repository import StandardNameRepository
from .storage.writer import write_catalog_artifacts

__all__ = ["build_artifacts"]


def build_artifacts(repo: StandardNameRepository, out_dir: Path | str):
    """Write standard JSON artifacts for the current repository snapshot.

    Returns list of written Path objects.
    """
    entries = {m.name: m for m in repo.list()}
    return write_catalog_artifacts(entries, out_dir)
