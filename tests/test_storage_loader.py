from pathlib import Path

import yaml

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.yaml_store import YamlStore


def test_load_single_entry(tmp_path: Path, example_scalars, write_yaml):
    # Use example from catalog
    example = example_scalars[0]
    write_yaml(tmp_path, example)

    # Load and verify (write_yaml writes to domain.yml as a list)
    domain = getattr(example, "physics_domain", "general") or "general"
    f = tmp_path / f"{domain}.yml"
    entries = yaml.safe_load(f.read_text(encoding="utf-8"))
    assert isinstance(entries, list)
    data = entries[0]
    entry = create_standard_name_entry(data)
    # Basic sanity: required attributes present
    assert hasattr(entry, "name") and hasattr(entry, "kind")
    assert entry.name == example.name
    assert entry.unit == example.unit


def test_load_catalog(tmp_path: Path, example_scalars, write_yaml):
    # Use examples from catalog — write all to same root
    for example in example_scalars[:2]:
        write_yaml(tmp_path, example)

    # Manual load of domain files
    names = set()
    for p in tmp_path.glob("*.yml"):
        loaded = yaml.safe_load(p.read_text(encoding="utf-8"))
        entries = loaded if isinstance(loaded, list) else [loaded]
        for d in entries:
            if isinstance(d.get("unit"), int | float):
                d["unit"] = str(d["unit"])
            entry = create_standard_name_entry(d)
            names.add(entry.name)
    expected_names = {ex.name for ex in example_scalars[:2]}
    assert names == expected_names
