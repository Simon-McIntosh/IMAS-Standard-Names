"""Path carriers require an object or geometry entity qualifier."""

import pytest

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.validation.semantic import run_semantic_checks


def _entry(name: str) -> dict:
    return {
        "name": name,
        "kind": "scalar",
        "physics_domain": "general",
        "status": "draft",
        "unit": "m",
        "description": "Path qualification semantic validation fixture.",
        "documentation": "Path qualification semantic validation fixture.",
    }


def _issues_for(name: str) -> list[str]:
    entry = create_standard_name_entry(_entry(name))
    return [issue for issue in run_semantic_checks({name: entry}) if name in issue]


@pytest.mark.parametrize(
    "name",
    (
        "radial_outline_of_plasma_boundary",
        "radial_outline_of_wall",
        "vertical_outline_of_plasma_boundary",
    ),
)
def test_geometry_qualified_outlines_do_not_raise_path_issue(name: str) -> None:
    issues = _issues_for(name)

    assert not any(
        "must specify what entity's path/boundary" in issue for issue in issues
    )


@pytest.mark.parametrize("name", ("outline", "trajectory"))
def test_bare_path_carriers_still_raise_path_issue(name: str) -> None:
    issues = _issues_for(name)

    assert any("must specify what entity's path/boundary" in issue for issue in issues)
