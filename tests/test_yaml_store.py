from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.yaml_store import YamlStore


def test_yaml_store_load(tmp_path: Path):
    store = YamlStore(tmp_path)
    # Write a YAML file directly to test load
    (tmp_path / "plasma_current.yml").write_text(
        "name: plasma_current\n"
        "kind: scalar\n"
        "description: Plasma current.\n"
        "documentation: Total plasma current in the tokamak.\n"
        "unit: A\n"
        "physics_domain: general\n"
    )
    loaded = {mm.name: mm for mm in store.load()}
    assert "plasma_current" in loaded
