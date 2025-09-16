from pathlib import Path
from imas_standard_names.storage.loader import load_catalog
from imas_standard_names.validation.structural import run_structural_checks
from imas_standard_names.validation.semantic import run_semantic_checks


def test_structural_and_semantic_checks(tmp_path: Path):
    # base vector and component but missing magnitude reference (no issue expected unless referenced)
    (tmp_path / "gradient.yml").write_text(
        """name: gradient_of_temperature
kind: derived_vector
status: draft
unit: K/m
description: Gradient of temperature.
frame: cylindrical_r_tor_z
components:
  r: r_component_of_gradient_of_temperature
  tor: tor_component_of_gradient_of_temperature
provenance:
  mode: operator
  operators: [gradient]
  base: temperature
  operator_id: gradient
""",
        encoding="utf-8",
    )
    (tmp_path / "r_component_of_gradient_of_temperature.yml").write_text(
        """name: r_component_of_gradient_of_temperature
kind: derived_scalar
status: draft
unit: K/m
description: Radial component.
axis: r
parent_vector: gradient_of_temperature
provenance:
  mode: operator
  operators: [gradient]
  base: temperature
  operator_id: gradient
""",
        encoding="utf-8",
    )
    (tmp_path / "tor_component_of_gradient_of_temperature.yml").write_text(
        """name: tor_component_of_gradient_of_temperature
kind: derived_scalar
status: draft
unit: K/m
description: Toroidal component.
axis: tor
parent_vector: gradient_of_temperature
provenance:
  mode: operator
  operators: [gradient]
  base: temperature
  operator_id: gradient
""",
        encoding="utf-8",
    )
    entries = load_catalog(tmp_path)
    structural_issues = run_structural_checks(entries)
    semantic_issues = run_semantic_checks(entries)
    # Semantic heuristic: gradient expects derivative-like units (contains '/' or .m)
    assert not structural_issues
    assert not semantic_issues  # units include /m via K/m
