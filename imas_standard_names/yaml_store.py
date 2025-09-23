"""YAML persistence utilities (authoritative storage)."""

from __future__ import annotations

from pathlib import Path
from typing import List
import yaml

from .schema import create_standard_name, StandardName
from .services import validate_models


class YamlStore:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()

    # Discovery ---------------------------------------------------------------
    def yaml_files(self):
        return sorted(list(self.root.rglob("*.yml")) + list(self.root.rglob("*.yaml")))

    # Load --------------------------------------------------------------------
    def load(self) -> List[StandardName]:
        models: List[StandardName] = []
        for f in self.yaml_files():
            with open(f, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if not isinstance(data, dict) or "name" not in data:
                continue
            unit_val = data.get("unit")
            if isinstance(unit_val, (int, float)):
                data["unit"] = str(unit_val)
            m = create_standard_name(data)
            models.append(m)
        issues = validate_models({m.name: m for m in models})
        if issues:
            raise ValueError(
                "Structural validation failed on load:\n" + "\n".join(issues)
            )
        return models

    # Write / Delete ----------------------------------------------------------
    def write(self, model: StandardName):
        path = self.root / f"{model.name}.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in model.model_dump().items() if v not in (None, [], "")}
        data["name"] = model.name
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False)

    def delete(self, name: str):
        path = self.root / f"{name}.yml"
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass


__all__ = ["YamlStore"]
