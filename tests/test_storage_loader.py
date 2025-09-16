from pathlib import Path
from imas_standard_names.storage.loader import load_standard_name_file, load_catalog


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
    entry = load_standard_name_file(f)
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
    catalog = load_catalog(tmp_path)
    assert set(catalog.keys()) == {"quantity_a", "quantity_b"}
