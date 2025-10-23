from pathlib import Path

import yaml

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.rendering import render_html


def test_render_html_basic(tmp_path: Path):
    yml = tmp_path / "entry.yml"
    yml.write_text(
        """name: velocity
kind: vector
status: active
unit: m.s^-1
description: Flow velocity.
""",
        encoding="utf-8",
    )
    # component files
    (tmp_path / "radial_component_of_velocity.yml").write_text(
        """name: radial_component_of_velocity
kind: scalar
status: active
    unit: m.s^-1
description: Radial component of velocity.
""",
        encoding="utf-8",
    )
    (tmp_path / "toroidal_component_of_velocity.yml").write_text(
        """name: toroidal_component_of_velocity
kind: scalar
status: active
    unit: m.s^-1
description: Toroidal component of velocity.
""",
        encoding="utf-8",
    )
    data = yaml.safe_load(yml.read_text(encoding="utf-8"))
    entry = create_standard_name_entry(data)
    html = render_html(entry)
    assert "velocity" in html
    assert "Flow velocity" in html
    assert "vector" in html  # Check kind is rendered
