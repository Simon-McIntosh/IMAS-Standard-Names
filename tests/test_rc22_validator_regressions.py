"""Regression tests for rc22 validator fixes (plan 39 §A3).

These tests verify that vNext-valid standard names that produced false-positive
ValidationErrors under the rc20 vocabulary checks (Component/Position/Process
enums) now pass without error after the rc22 rewrite of
``_check_grammar_vocabulary_consistency`` in ``models.py``.

The four names below were quarantined during the rc21 bootstrap cycle due to
false-positive ValidationErrors:
- vertical_coordinate_of_plasma_boundary_outline_point
  → rc20 bug: coordinate prefix check captured compound token
    "vertical_coordinate_of_plasma_boundary" and flagged it as missing from
    Component vocabulary.
- normalized_of_parallel_component_of_gyrocenter_current_density_eigenmode
  → rc20 bug: component_of check captured compound token
    "normalized_of_parallel" (contains _of_) and flagged it as missing from
    Component vocabulary.
- normalized_pressure_gradient_at_gyrokinetic_flux_surface
  → rc20 bug: at_ check required token to be in rc20 Position enum;
    "gyrokinetic_flux_surface" is absent from that enum but valid in vNext
    (VocabGap token accepted by parser).
- parallel_current_density_due_to_wave_per_toroidal_mode
  → rc20 bug: due_to_ check required token in rc20 Process enum;
    "wave_per_toroidal_mode" is a compound indexed-process expression
    accepted by the parser but not in the flat enum list.
"""

import pytest
from pydantic import ValidationError

from imas_standard_names.models import (
    StandardNameScalarEntry,
    StandardNameVectorEntry,
    create_standard_name_entry,
)

# ---------------------------------------------------------------------------
# Minimal metadata helpers
# ---------------------------------------------------------------------------

_SCALAR_META = {
    "kind": "scalar",
    "unit": "1",
    "description": "Regression test entry.",
    "documentation": "Regression test — no physical meaning intended.",
}

_VECTOR_META = {
    "kind": "vector",
    "unit": "1",
    "description": "Regression test entry.",
    "documentation": "Regression test — no physical meaning intended.",
}


def _scalar(name: str) -> StandardNameScalarEntry:
    return StandardNameScalarEntry(name=name, **_SCALAR_META)  # type: ignore[arg-type]


def _vector(name: str) -> StandardNameVectorEntry:
    return StandardNameVectorEntry(name=name, **_VECTOR_META)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Quarantined-name regressions (all must pass without ValidationError)
# ---------------------------------------------------------------------------


def test_vertical_coordinate_of_plasma_boundary_outline_point():
    """rc20 false-positive: coordinate prefix check over-matched compound token.

    'vertical_coordinate_of_plasma_boundary' was captured before '_outline_'
    and flagged as missing from Component vocabulary.  The rc22 fix skips the
    check when the captured prefix contains '_of_'.
    """
    entry = _scalar("vertical_coordinate_of_plasma_boundary_outline_point")
    assert entry.name == "vertical_coordinate_of_plasma_boundary_outline_point"


def test_normalized_of_parallel_component_of_gyrocenter_current_density_eigenmode():
    """rc20 false-positive: component_of check captured compound operator-nested token.

    'normalized_of_parallel' (contains '_of_') was captured before '_component_of_'
    and flagged as missing from Component vocabulary.  The rc22 fix skips the
    check when the captured prefix contains '_of_'.
    """
    entry = _scalar(
        "normalized_of_parallel_component_of_gyrocenter_current_density_eigenmode"
    )
    assert (
        entry.name
        == "normalized_of_parallel_component_of_gyrocenter_current_density_eigenmode"
    )


def test_normalized_pressure_gradient_at_gyrokinetic_flux_surface():
    """rc20 false-positive: at_ check required token in rc20 Position enum.

    'gyrokinetic_flux_surface' is absent from the rc20 Position enum but is
    a valid vNext locus token (VocabGap path in parser).  The rc22 fix only
    flags tokens that ARE in the locus_registry with an incompatible relation.
    """
    entry = _scalar("normalized_pressure_gradient_at_gyrokinetic_flux_surface")
    assert entry.name == "normalized_pressure_gradient_at_gyrokinetic_flux_surface"


def test_parallel_current_density_due_to_wave_per_toroidal_mode():
    """rc20 false-positive: due_to_ check required token in rc20 Process enum.

    'wave_per_toroidal_mode' is a compound indexed-process expression not
    present in the flat Process enum.  The rc22 fix drops the due_to_ check
    entirely — process token validation is handled by the parser's VocabGap
    mechanism, not the Pydantic validator.
    """
    entry = _scalar("parallel_current_density_due_to_wave_per_toroidal_mode")
    assert entry.name == "parallel_current_density_due_to_wave_per_toroidal_mode"


# ---------------------------------------------------------------------------
# Forward-looking test: vNext coordinate_axis + operator combination
# ---------------------------------------------------------------------------


def test_vnext_radial_gradient_of_electron_temperature():
    """Novel vNext-valid name: coordinate_axis (radial) + operator (gradient_of).

    'radial' is in coordinate_axes.yml.  'gradient_of_electron_temperature'
    uses the unary_prefix operator 'gradient'.  This name exercises both the
    coordinate-axis vocabulary path and the operator nesting path.
    """
    entry = _vector("radial_gradient_of_electron_temperature")
    assert entry.name == "radial_gradient_of_electron_temperature"


# ---------------------------------------------------------------------------
# Sanity check: legitimate invalid names still fail
# ---------------------------------------------------------------------------


def test_nonexistent_component_still_fails():
    """The component_of validator must still reject genuinely unknown tokens.

    'completely_unknown_xyz' is not in components.yml, is not compound (no
    '_of_'), and should still raise a ValidationError.
    """
    with pytest.raises(ValidationError, match="Grammar vocabulary"):
        _scalar("completely_unknown_xyz_component_of_magnetic_field")
