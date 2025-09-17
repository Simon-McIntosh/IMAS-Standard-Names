"""Writers for persisting standard name models and catalog artifacts."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Mapping
import json
from ..schema import StandardNameBase, save_standard_name

__all__ = ["save_standard_name", "write_catalog_artifacts"]


def write_catalog_artifacts(
    entries: Mapping[str, StandardNameBase], out_dir: Path | str
) -> List[Path]:
    """Write JSON artifacts replicating catalog outputs.

    Creates (overwriting):
      - catalog.json        (full serialized mapping)
      - index.json          (lightweight summary list)
      - relationships.json  (simplified relationship graph)
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    catalog_payload: Dict[str, Dict[str, Any]] = {
        name: e.model_dump(exclude_none=True, exclude_defaults=True)
        for name, e in entries.items()
    }
    index_payload = [
        {
            "name": e.name,
            "kind": getattr(e, "kind", None),
            "status": getattr(e, "status", None),
            "unit": getattr(e, "unit", ""),
            "tags": getattr(e, "tags", []),
        }
        for e in entries.values()
    ]
    relationships_payload = {
        name: {
            "components": getattr(e, "components", {}) or {},
            "magnitude": getattr(e, "magnitude", None),
            "provenance": getattr(e, "provenance", None),
        }
        for name, e in entries.items()
    }

    written: List[Path] = []
    for filename, payload in (
        ("catalog.json", catalog_payload),
        ("index.json", index_payload),
        ("relationships.json", relationships_payload),
    ):
        path = out_path / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=False)
        written.append(path)
    return written
