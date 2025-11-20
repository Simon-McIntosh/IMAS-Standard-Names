"""YAML persistence utilities (authoritative storage)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import (
    StandardNameEntry,
    StandardNameScalarEntry,
    create_standard_name_entry,
)
from .services import validate_models


def _represent_literal_str(dumper, data):
    """Represent multiline strings using literal block scalar style (|)."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


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
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if not isinstance(data, dict) or "name" not in data:
                continue
            unit_val = data.get("unit")
            if isinstance(unit_val, int | float):
                data["unit"] = str(unit_val)

            # Handle Pydantic validation errors in permissive mode
            try:
                m = create_standard_name_entry(data)
                models.append(m)
            except Exception as e:
                if self.permissive:
                    # Load invalid entry anyway by creating object without validation
                    # Use object.__new__ to bypass __init__ and all validators
                    m = object.__new__(StandardNameScalarEntry)
                    # Manually set fields from data
                    for key, value in data.items():
                        object.__setattr__(m, key, value)
                    # Set defaults for missing required fields
                    if not hasattr(m, "kind"):
                        object.__setattr__(m, "kind", "scalar")
                    if not hasattr(m, "status"):
                        object.__setattr__(m, "status", "draft")
                    if not hasattr(m, "unit"):
                        object.__setattr__(m, "unit", "")
                    if not hasattr(m, "tags"):
                        object.__setattr__(m, "tags", [])
                    if not hasattr(m, "links"):
                        object.__setattr__(m, "links", [])
                    if not hasattr(m, "constraints"):
                        object.__setattr__(m, "constraints", [])
                    if not hasattr(m, "documentation"):
                        object.__setattr__(m, "documentation", "")
                    if not hasattr(m, "validity_domain"):
                        object.__setattr__(m, "validity_domain", "")
                    if not hasattr(m, "deprecates"):
                        object.__setattr__(m, "deprecates", "")
                    if not hasattr(m, "superseded_by"):
                        object.__setattr__(m, "superseded_by", "")
                    if not hasattr(m, "provenance"):
                        object.__setattr__(m, "provenance", None)
                    models.append(m)
                    warning = f"Validation error in {f.name}: {e}"
                    self.validation_warnings.append(warning)
                else:
                    raise  # Re-raise in strict mode

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

    # Write / Delete ----------------------------------------------------------
    def write(self, model: StandardNameEntry):
        # Organize by primary tag (tags[0]) if present
        if model.tags and len(model.tags) > 0:
            primary_tag = model.tags[0]
            path = self.root / primary_tag / f"{model.name}.yml"
        else:
            # Fallback to root if no tags
            path = self.root / f"{model.name}.yml"

        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in model.model_dump().items() if v not in (None, [], "")}
        data["name"] = model.name

        # Configure YAML dumper to use literal block scalar (|) for multiline strings
        yaml.add_representer(str, _represent_literal_str, Dumper=yaml.SafeDumper)

        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, width=80)

    def delete(self, name: str):
        # Search in subdirectories first, then root
        candidates = list(self.root.rglob(f"{name}.yml"))
        for path in candidates:
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
                break


__all__ = ["YamlStore"]
