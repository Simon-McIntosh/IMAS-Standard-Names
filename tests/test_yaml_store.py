import importlib.resources as resources
from pathlib import Path

import yaml

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.yaml_store import (
    YamlStore,
    dump_catalog_yaml,
    write_catalog_yaml,
)


def test_yaml_store_load(tmp_path: Path):
    store = YamlStore(tmp_path)
    # Write a YAML file directly to test load
    (tmp_path / "plasma_current.yml").write_text(
        "name: plasma_current\n"
        "kind: scalar\n"
        "description: Plasma current.\n"
        "documentation: Total plasma current in the tokamak.\n"
        "unit: A\n"
        ""
    )
    loaded = {mm.name: mm for mm in store.load()}
    assert "plasma_current" in loaded


def test_catalog_yaml_separates_consecutive_entries() -> None:
    rendered = dump_catalog_yaml(
        [
            {"name": "plasma_current", "description": "Plasma current."},
            {"name": "electron_density", "description": "Electron density."},
        ]
    )

    assert "description: Plasma current.\n\n- name: electron_density" in rendered
    assert "\n\n\n- name:" not in rendered


def test_catalog_yaml_preserves_unicode_and_wraps_prose() -> None:
    rendered = dump_catalog_yaml(
        [
            {
                "name": "toroidal_coordinate",
                "description": (
                    "Toroidal angle φ follows the right-handed convention and is "
                    "reviewed as readable prose rather than an escaped byte sequence."
                ),
            }
        ]
    )

    assert "φ" in rendered
    assert "\\u03c6" not in rendered.lower()
    assert "readable\n    prose" in rendered
    assert "\\\n" not in rendered


def test_catalog_yaml_round_trips_input_structure() -> None:
    entries = [
        {
            "name": "safety_factor",
            "description": "Safety factor q at normalized poloidal flux ψ.",
            "documentation": "The angle φ is measured in radians.",
            "status": "draft",
            "kind": "scalar",
            "unit": "1",
            "links": ["magnetic_field", "poloidal_flux"],
        },
        {
            "name": "magnetic_axis",
            "description": "Magnetic axis position.",
            "status": "active",
            "kind": "metadata",
        },
    ]

    assert yaml.safe_load(dump_catalog_yaml(entries)) == entries


def test_existing_catalog_rewrite_preserves_data(tmp_path: Path) -> None:
    source = (
        resources.files("imas_standard_names")
        / "resources"
        / "standard_name_examples"
        / "equilibrium.yml"
    )
    existing = yaml.safe_load(source.read_text(encoding="utf-8"))
    rewritten = tmp_path / "equilibrium.yml"

    write_catalog_yaml(rewritten, existing)

    assert yaml.safe_load(rewritten.read_text(encoding="utf-8")) == existing
