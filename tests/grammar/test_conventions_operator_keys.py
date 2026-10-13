"""Convention selection for indexed and binary operator names."""

import shutil
from pathlib import Path

from imas_standard_names.grammar import vocab_loaders
from imas_standard_names.grammar.parser import parse
from imas_standard_names.grammar.terms import _ir_tokens, select_conventions
from imas_standard_names.grammar.vocab_loaders import load_conventions

DERIVATIVE = (
    "derivative_of_volume_of_flux_surface_with_respect_to_"
    "poloidal_magnetic_flux_coordinate"
)
RATIO = "ratio_of_line_averaged_electron_density_to_greenwald_density"


def test_indexed_derivative_selects_its_operator_concept():
    applied = select_conventions(DERIVATIVE)
    assert "derivative_with_respect_to" in {
        concept.token for concept in applied.concepts
    }


def test_ratio_selects_its_operator_concept():
    applied = select_conventions(RATIO)
    assert "ratio" in {concept.token for concept in applied.concepts}


def test_ratio_template_matches_the_operator_key(tmp_path: Path):
    directory = tmp_path / "conventions"
    shutil.copytree(vocab_loaders._CONVENTIONS_DIR, directory)
    templates = directory / "templates.yml"
    with templates.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n  - base: ratio\n"
            "    description: Ratio of {modifiers}\n"
            "    documentation: Ratio of {modifiers}\n"
        )
    registry = load_conventions(directory=directory)

    assert "ratio" in {
        template.base
        for template in select_conventions(RATIO, registry=registry).templates
    }
    assert "ratio" not in {
        template.base
        for template in select_conventions(
            "electron_density", registry=registry
        ).templates
    }


def test_binary_placeholder_is_not_a_selected_token():
    tokens = _ir_tokens(parse(RATIO, strict=True).ir)
    assert "ratio" in tokens
    assert "placeholder" not in tokens
