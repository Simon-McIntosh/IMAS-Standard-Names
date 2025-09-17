from pathlib import Path
import yaml
from imas_standard_names.schema import create_standard_name
from imas_standard_names.rendering import render_html


def test_render_html_basic(tmp_path: Path):
    yml = tmp_path / "entry.yml"
    yml.write_text(
        """name: velocity
kind: vector
status: active
unit: m.s^-1
description: Flow velocity.
frame: cylindrical_r_tor_z
components:
  r: r_component_of_velocity
  tor: tor_component_of_velocity
""",
        encoding="utf-8",
    )
    # component files
    (tmp_path / "r_component_of_velocity.yml").write_text(
        """name: r_component_of_velocity
kind: scalar
status: active
    unit: m.s^-1
description: Radial component of velocity.
""",
        encoding="utf-8",
    )
    (tmp_path / "tor_component_of_velocity.yml").write_text(
        """name: tor_component_of_velocity
kind: scalar
status: active
    unit: m.s^-1
description: Toroidal component of velocity.
""",
        encoding="utf-8",
    )
    data = yaml.safe_load(yml.read_text(encoding="utf-8"))
    entry = create_standard_name(data)
    html = render_html(entry)
    assert "velocity" in html
    assert "Flow velocity" in html
    assert "Magnitude" in html or "magnitude_of_velocity" in html
