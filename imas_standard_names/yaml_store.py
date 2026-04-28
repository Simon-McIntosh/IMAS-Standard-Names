"""YAML persistence utilities (authoritative storage)."""

import logging
import warnings
from pathlib import Path

import yaml

from .models import (
    StandardNameEntry,
    StandardNameScalarEntry,
    create_standard_name_entry,
)
from .services import validate_models

logger = logging.getLogger(__name__)

# Fields that are no longer part of the catalog entry model.
# They are stripped from loaded YAML data to support clean schema migration.
_STRIPPED_FIELDS = {"physics_domain", "dd_paths"}


class CatalogMigrationError(Exception):
    """Raised when a legacy catalog layout is detected."""


class YamlStore:
    def __init__(self, root: str | Path, permissive: bool = False):
        self.root = Path(root).expanduser().resolve()
        self.permissive = permissive
        self.validation_warnings: list[str] = []

    # Discovery ---------------------------------------------------------------
    def yaml_files(self):
        return sorted(list(self.root.rglob("*.yml")) + list(self.root.rglob("*.yaml")))

    # Load --------------------------------------------------------------------
    def load(self) -> list[StandardNameEntry]:
        models: list[StandardNameEntry] = []
        for f in self.yaml_files():
            # Detect nested paths (legacy per-file layout)
            relative = f.relative_to(self.root)
            if len(relative.parts) > 1:
                if not self.permissive:
                    raise CatalogMigrationError(
                        f"Legacy per-file YAML detected at {f}; catalog has migrated "
                        "to per-domain list format (plan 40). Re-run `sn publish` "
                        "from imas-codex to regenerate."
                    )
                # In permissive mode, fall through and process as single-entry dict

            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}

            # Determine entries to process from this file
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                if "name" in data:
                    entries = [data]
                elif not self.permissive:
                    raise CatalogMigrationError(
                        f"Legacy per-file YAML detected at {f}; catalog has migrated "
                        "to per-domain list format (plan 40). Re-run `sn publish` "
                        "from imas-codex to regenerate."
                    )
                else:
                    continue
            else:
                continue

            for entry_data in entries:
                if not isinstance(entry_data, dict) or "name" not in entry_data:
                    continue

                unit_val = entry_data.get("unit")
                if isinstance(unit_val, int | float):
                    entry_data["unit"] = str(unit_val)

                # Strip fields no longer in the catalog entry model
                for field in _STRIPPED_FIELDS:
                    entry_data.pop(field, None)

                # Handle Pydantic validation errors in permissive mode
                try:
                    m = create_standard_name_entry(entry_data)
                    models.append(m)
                except Exception as e:
                    if self.permissive:
                        # Load invalid entry anyway by creating object without validation
                        # Use object.__new__ to bypass __init__ and all validators
                        m = object.__new__(StandardNameScalarEntry)
                        # Manually set fields from data
                        for key, value in entry_data.items():
                            object.__setattr__(m, key, value)
                        # Set defaults for missing required fields
                        for attr, default in [
                            ("kind", "scalar"),
                            ("status", "draft"),
                            ("unit", ""),
                            ("tags", []),
                            ("links", []),
                            ("constraints", []),
                            ("documentation", ""),
                            ("validity_domain", ""),
                            ("deprecates", ""),
                            ("superseded_by", ""),
                            ("provenance", None),
                            ("arguments", None),
                            ("error_variants", None),
                        ]:
                            if not hasattr(m, attr):
                                object.__setattr__(m, attr, default)
                        models.append(m)
                        warning = f"Validation error in {f.name}: {e}"
                        self.validation_warnings.append(warning)
                    else:
                        raise  # Re-raise in strict mode

        # Cross-reference warnings for arguments and error_variants
        all_names = {m.name for m in models}
        for m in models:
            args = getattr(m, "arguments", None)
            if args:
                for arg in args:
                    arg_name = (
                        getattr(arg, "name", None) if not isinstance(arg, str) else arg
                    )
                    if arg_name and arg_name not in all_names:
                        w = (
                            f"Entry '{m.name}': argument reference "
                            f"'{arg_name}' not found in catalog"
                        )
                        self.validation_warnings.append(w)
                        warnings.warn(w, stacklevel=1)
            evars = getattr(m, "error_variants", None)
            if evars and isinstance(evars, dict):
                for error_key, target in evars.items():
                    if target not in all_names:
                        w = (
                            f"Entry '{m.name}': error_variant '{error_key}' "
                            f"target '{target}' not found in catalog"
                        )
                        self.validation_warnings.append(w)
                        warnings.warn(w, stacklevel=1)

        # Handle structural validation errors in permissive mode
        issues = validate_models({m.name: m for m in models})
        if issues:
            if self.permissive:
                self.validation_warnings.extend(
                    [f"Structural: {issue}" for issue in issues]
                )
            else:
                raise ValueError(
                    "Structural validation failed on load:\n" + "\n".join(issues)
                )
        return models


__all__ = ["CatalogMigrationError", "YamlStore"]
