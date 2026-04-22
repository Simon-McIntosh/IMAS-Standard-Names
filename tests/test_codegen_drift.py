"""Ensure committed generated grammar files stay in sync with YAML specs.

The check protects against:
- editing ``grammar/vocabularies/*.yml`` without regenerating ``model_types.py``
  / ``constants.py`` / ``tag_types.py`` / ``field_schemas.py``;
- manual edits to generated files that would be overwritten by a regen.

Mirrors the CI ``uv run build-grammar --check`` step so drift is caught locally
via pytest as well.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import Transformation, parse_standard_name


def test_build_grammar_check_passes():
    """Run the codegen drift check; fail the test on any drift."""
    from imas_standard_names.grammar_codegen import generate as codegen

    try:
        codegen.main(format_code=False, check=True)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            pytest.fail(
                "Generated grammar files are out of date. "
                "Run `uv run build-grammar` and commit the result."
            )


def test_build_grammar_check_returns_cleanly_when_in_sync():
    """Direct happy-path assertion — check mode returns without raising."""
    from imas_standard_names.grammar_codegen import generate as codegen

    try:
        codegen.main(format_code=False, check=True)
    except SystemExit as exc:
        if exc.code not in (None, 0):
            pytest.fail(
                "Generated grammar files drift from YAML specs. "
                "Run `uv run build-grammar` and commit the result."
            )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "rc20 token forms (magnitude_of, real_part_of, imaginary_part_of, phase_of)"
        " replaced by bare tokens in vNext grammar (plan 38 §A7)"
    ),
)
def test_transformation_enum_includes_complex_tokens():
    """R1 F1 / ADR-4: magnitude_of / real_part_of / imaginary_part_of /
    phase_of must be declared in the runtime Transformation enum."""
    tokens = {t.value for t in Transformation}
    assert {"magnitude_of", "real_part_of", "imaginary_part_of", "phase_of"} <= tokens


@pytest.mark.xfail(
    strict=True,
    reason="rc20 token form 'magnitude_of' replaced by bare 'magnitude' in vNext grammar (plan 38 §A7)",
)
def test_magnitude_of_magnetic_field_parses():
    """R1 F1: magnitude_of_magnetic_field must parse with transformation slot set."""
    parsed = parse_standard_name("magnitude_of_magnetic_field")
    assert parsed.transformation is not None
    assert parsed.transformation.value == "magnitude_of"
    assert parsed.physical_base == "magnetic_field"


@pytest.mark.xfail(
    strict=True,
    reason="rc20 token forms (real_part_of, imaginary_part_of, phase_of) replaced by bare tokens in vNext grammar (plan 38 §A7)",
)
@pytest.mark.parametrize(
    "name,token",
    [
        ("real_part_of_electron_temperature", "real_part_of"),
        ("imaginary_part_of_electron_temperature", "imaginary_part_of"),
        ("phase_of_electron_temperature", "phase_of"),
    ],
)
def test_complex_transformation_prefixes_parse(name: str, token: str) -> None:
    parsed = parse_standard_name(name)
    assert parsed.transformation is not None
    assert parsed.transformation.value == token
