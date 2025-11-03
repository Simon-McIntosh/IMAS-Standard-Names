from pathlib import Path

import yaml

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.yaml_store import YamlStore


def test_load_single_entry(tmp_path: Path, example_scalars):
    # Use example from catalog
    example = example_scalars[0]
    store = YamlStore(tmp_path)
    store.write(example)

    # Load and verify (file is written to primary_tag subdirectory)
    primary_tag = example.tags[0] if example.tags else ""
    f = tmp_path / primary_tag / f"{example.name}.yml"
    data = yaml.safe_load(f.read_text(encoding="utf-8"))
    entry = create_standard_name_entry(data)
    # Basic sanity: required attributes present
    assert hasattr(entry, "name") and hasattr(entry, "kind")
    assert entry.name == example.name
    assert entry.unit == example.unit


def test_load_catalog(tmp_path: Path, example_scalars):
    # Use examples from catalog
    (tmp_path / "sub").mkdir()
    store = YamlStore(tmp_path)

    # Write two examples
    for i, example in enumerate(example_scalars[:2]):
        if i == 1:
            # Write second example to subdirectory
            store_sub = YamlStore(tmp_path / "sub")
            store_sub.write(example)
        else:
            store.write(example)

    # Manual load of directory entries
    names = set()
    for p in tmp_path.rglob("*.yml"):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(d.get("unit"), int | float):
            d["unit"] = str(d["unit"])
        entry = create_standard_name_entry(d)
        names.add(entry.name)
    expected_names = {ex.name for ex in example_scalars[:2]}
    assert names == expected_names
