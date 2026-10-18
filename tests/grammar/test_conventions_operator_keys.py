"""Convention selection for indexed and binary operator names."""

from imas_standard_names.grammar.parser import parse
from imas_standard_names.grammar.terms import _ir_tokens, select_conventions

DERIVATIVE = (
    "derivative_of_volume_of_flux_surface_with_respect_to_"
    "poloidal_magnetic_flux_coordinate"
)
RATIO = "ratio_of_line_averaged_electron_density_to_greenwald_density"
DIFFERENCE = "difference_of_total_pressure_and_electron_pressure"
PRODUCT = "product_of_density_and_temperature"
PLAIN = "electron_density"

TEMPLATE_BASES = {"ratio", "difference", "product"}


def test_indexed_derivative_selects_its_operator_concept():
    applied = select_conventions(DERIVATIVE)
    assert "derivative_with_respect_to" in {
        concept.token for concept in applied.concepts
    }


def test_binary_operator_key_reaches_the_convention_tokens():
    tokens = _ir_tokens(parse(RATIO, strict=True).ir)
    assert "ratio" in tokens
    assert "ratio" in {concept.token for concept in select_conventions(RATIO).concepts}


def test_shipped_templates_are_selected_for_their_operator_names():
    for name, base in (
        (RATIO, "ratio"),
        (DIFFERENCE, "difference"),
        (PRODUCT, "product"),
    ):
        bases = {template.base for template in select_conventions(name).templates}
        assert base in bases, f"{name} did not select its {base} template"


def test_plain_name_selects_no_operator_template():
    bases = {template.base for template in select_conventions(PLAIN).templates}
    assert not (bases & TEMPLATE_BASES)


def test_binary_placeholder_is_not_a_selected_token():
    tokens = _ir_tokens(parse(RATIO, strict=True).ir)
    assert "ratio" in tokens
    assert "placeholder" not in tokens
