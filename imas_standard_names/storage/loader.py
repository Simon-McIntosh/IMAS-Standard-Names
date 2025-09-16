"""Load Standard Name YAML resources into schema models."""

from __future__ import annotations
from pathlib import Path
from typing import Dict
from .. import schema

load_standard_name_file = schema.load_standard_name_file


def load_catalog(root: Path) -> Dict[str, schema.StandardName]:
    """Load all per-file YAML standard names under a root directory.

    Thin wrapper so callers can import from imas_standard_names.storage.
    """
    return schema.load_catalog(root)
