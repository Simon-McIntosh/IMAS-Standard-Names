"""Minimal validator stub for uniform component-of naming system.

This script performs *lightweight* checks so contributors get quick
feedback even before a full schema & semantic engine exist.

Current checks (incremental roadmap):
  1. Presence of `standard_names/` directory.
  2. Parse all `.yml` / `.yaml` files under domain subdirectories.
  3. Classify entries by `kind`.
  4. Detect component naming pattern violations.
    5. Ensure vector entries list components that exist.
    6. Check magnitude reduction provenance base is the vector and no spurious components missing.

Planned (not implemented):
  * Operator rank validation
  * Nested operator chain parsing
    * Frame axis conformity
    * Derived vector component consistency
    * Operator rank validation (supersedes simple pattern checks)

Usage:
  python tools/validate_catalog.py

Exit code 0 => no errors found (within current check scope).
Non-zero => at least one error printed.
"""

from __future__ import annotations

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set
import re

ROOT = Path(__file__).resolve().parent.parent
# Updated path: standard names now reside inside the package resources directory
STD_DIR = ROOT / "imas_standard_names" / "resources" / "standard_names"


def iter_yaml_files() -> List[Path]:
    if not STD_DIR.exists():
        return []
    return [p for p in STD_DIR.rglob("*.yml") if p.is_file()] + [
        p for p in STD_DIR.rglob("*.yaml") if p.is_file()
    ]


def load_yaml(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:  # pragma: no cover (defensive)
        return {"__load_error__": str(e)}


def is_component_name(name: str) -> bool:
    return "_component_of_" in name


def main() -> int:
    errors: List[str] = []

    if not STD_DIR.exists():
        print(
            "[INFO] No resources/standard_names/ directory present yet – nothing to validate."
        )
        return 0

    files = iter_yaml_files()
    if not files:
        print("[WARN] resources/standard_names/ contains no YAML files.")
        return 0

    entries: Dict[str, dict] = {}
    name_to_file: Dict[str, Path] = {}

    for f in files:
        data = load_yaml(f)
        if not isinstance(data, dict):
            errors.append(f"FILE {f}: top-level YAML must be a mapping")
            continue
        name = data.get("name")
        if not name:
            errors.append(f"FILE {f}: missing 'name'")
            continue
        if name in entries:
            errors.append(
                f"DUPLICATE name '{name}' in {f} (already defined in {name_to_file[name]})"
            )
            continue
        entries[name] = data
        name_to_file[name] = f

    # Index vectors -> component set; and collect component backlinks
    vector_components: Dict[str, Set[str]] = {}
    component_files: Dict[str, dict] = {}

    for name, data in entries.items():
        kind = data.get("kind")
        if kind == "vector" or kind == "derived_vector":
            comps = data.get("components") or {}
            if not isinstance(comps, dict) or len(comps) < 2:
                errors.append(
                    f"VECTOR {name}: must declare >=2 components (found {len(comps)})"
                )
            else:
                vector_components[name] = set(comps.values())
        # record components
        if kind in {"scalar", "derived_scalar"} and is_component_name(name):
            component_files[name] = data

        # DIAG001: forbid hard-coded instrument indices (e.g. magnetic_probe_23_normal_field)
        # Allowed pattern: trailing numeric IDs ONLY for established equipment sets (future allowlist).
        if re.search(
            r"\b(magnetic_probe|flux_loop|diagnostic_probe|pf_coil)_[0-9]+_", name
        ):
            errors.append(
                f"DIAG001 {name}: hard-coded instrument index detected; remove numeric id from standard name."
            )

    # Validate component naming pattern
    axis_prefixes = (
        "radial_",
        "toroidal_",
        "vertical_",
        "poloidal_",
        "parallel_",
        "perpendicular1_",
        "perpendicular2_",
        "x_",
        "y_",
        "z_",
    )
    for comp_name in component_files:
        if not comp_name.startswith(axis_prefixes):
            errors.append(
                f"COMPONENT {comp_name}: axis prefix not in approved list (extend validator if intended)."
            )

    # Cross-check vectors reference existing components
    for vec, comps in vector_components.items():
        for cname in comps:
            if cname not in entries:
                errors.append(
                    f"VECTOR {vec}: component '{cname}' file not found (expect scalar YAML)."
                )
            else:
                if not is_component_name(cname):
                    errors.append(
                        f"VECTOR {vec}: listed component '{cname}' does not follow component pattern."
                    )
                # Backlink field removed from schema: membership inferred solely from listing.

    # Magnitude coverage via provenance (mode: reduction, reduction: magnitude)
    for name, data in entries.items():
        prov = data.get("provenance") or {}
        if (
            isinstance(prov, dict)
            and prov.get("mode") == "reduction"
            and prov.get("reduction") == "magnitude"
        ):
            base = prov.get("base")
            if base not in vector_components:
                errors.append(
                    f"MAGNITUDE {name}: reduction base '{base}' is not a declared vector"
                )

    if errors:
        print("Validation FAILED (stub checks):")
        for e in errors:
            print("  -", e)
        return 1
    print("Validation PASSED (stub checks only).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
