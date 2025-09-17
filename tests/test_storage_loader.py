from pathlib import Path
import yaml
from imas_standard_names.schema import create_standard_name


def test_load_single_entry(tmp_path: Path):
    f = tmp_path / "test_name.yml"
    f.write_text(
        """name: test_quantity
kind: scalar
status: draft
unit: m
description: A test quantity.
""",
        encoding="utf-8",
    )
    data = yaml.safe_load(f.read_text(encoding="utf-8"))
    entry = create_standard_name(data)
    # Basic sanity: required attributes present
    assert hasattr(entry, "name") and hasattr(entry, "kind")
    assert entry.name == "test_quantity"
    assert entry.unit == "m"


def test_load_catalog(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.yml").write_text(
        """name: quantity_a
kind: scalar
status: active
unit: 1
description: A.
""",
        encoding="utf-8",
    )
    (tmp_path / "sub" / "b.yml").write_text(
        """name: quantity_b
kind: scalar
status: draft
unit: s
description: B.
""",
        encoding="utf-8",
    )
    # Manual load of directory entries
    names = set()
    for p in tmp_path.rglob("*.yml"):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(d.get("unit"), (int, float)):
            d["unit"] = str(d["unit"])
        entry = create_standard_name(d)
        names.add(entry.name)
    assert names == {"quantity_a", "quantity_b"}
