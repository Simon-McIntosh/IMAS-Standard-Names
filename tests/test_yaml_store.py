from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.yaml_store import YamlStore


def test_yaml_store_round_trip(tmp_path: Path):
    store = YamlStore(tmp_path)
    m = create_standard_name_entry(
        {
            "name": "plasma_current",
            "kind": "scalar",
            "description": "Plasma current.",
            "unit": "A",
        }
    )
    store.write(m)
    assert any(p.stem == "plasma_current" for p in store.yaml_files())
    loaded = {mm.name: mm for mm in store.load()}
    assert "plasma_current" in loaded
    store.delete("plasma_current")
    assert all(p.stem != "plasma_current" for p in store.yaml_files())
