import pytest

from imas_standard_names.grammar.parser import ParseError, parse
from imas_standard_names.grammar.render import compose


@pytest.mark.parametrize(
    "name, expected_qualifiers",
    [
        ("emissivity_half_width", ["emissivity"]),
        ("hard_xray_emissivity_half_width", ["hard_xray", "emissivity"]),
        (
            "inner_hard_xray_emissivity_half_width",
            ["inner", "hard_xray", "emissivity"],
        ),
    ],
)
def test_emissivity_half_width_round_trips(
    name: str, expected_qualifiers: list[str]
) -> None:
    result = parse(name, strict=True)

    assert result.ir.base.token == "half_width"
    assert [
        qualifier.token for qualifier in result.ir.qualifiers
    ] == expected_qualifiers
    assert compose(result.ir) == name


def test_terminal_emissivity_retains_physical_base_role() -> None:
    name = "hard_xray_emissivity"

    result = parse(name, strict=True)

    assert result.ir.base.token == "emissivity"
    assert [qualifier.token for qualifier in result.ir.qualifiers] == ["hard_xray"]
    assert compose(result.ir) == name


@pytest.mark.parametrize(
    "name",
    [
        "half_width_of_hard_xray_emissivity_peak",
        "half_width_of_emissivity_peak",
        "half_width_of_normalized_toroidal_flux_coordinate",
    ],
)
def test_unrelated_half_width_constructions_remain_rejected(name: str) -> None:
    with pytest.raises(ParseError):
        parse(name, strict=True)


def test_detector_width_of_construction_remains_parseable() -> None:
    name = "first_local_tangential_width_of_hard_xray_detector"

    assert compose(parse(name, strict=True).ir) == name
