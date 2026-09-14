import pytest

from imas_standard_names.grammar.ir import LocusRelation, LocusType
from imas_standard_names.grammar.parser import ParseError, parse
from imas_standard_names.grammar.render import compose


@pytest.mark.parametrize(
    "name, expected_qualifiers",
    [
        ("half_width_of_emissivity_peak", []),
        (
            "inner_hard_xray_half_width_of_emissivity_peak",
            ["inner", "hard_xray"],
        ),
    ],
)
def test_half_width_of_emissivity_peak_round_trips(
    name: str, expected_qualifiers: list[str]
) -> None:
    result = parse(name, strict=True)

    assert result.ir.base.token == "half_width"
    assert [
        qualifier.token for qualifier in result.ir.qualifiers
    ] == expected_qualifiers
    assert result.ir.locus is not None
    assert result.ir.locus.token == "emissivity_peak"
    assert result.ir.locus.type is LocusType.POSITION
    assert result.ir.locus.relation is LocusRelation.OF
    assert compose(result.ir) == name


def test_emissivity_remains_only_a_physical_base() -> None:
    name = "hard_xray_emissivity"

    result = parse(name, strict=True)

    assert result.ir.base.token == "emissivity"
    assert [qualifier.token for qualifier in result.ir.qualifiers] == ["hard_xray"]
    assert compose(result.ir) == name

    with pytest.raises(ParseError):
        parse("emissivity_half_width", strict=True)


@pytest.mark.parametrize(
    "name",
    [
        "half_width_of_hard_xray_emissivity_peak",
        "hard_xray_emissivity_half_width",
        "half_width_of_normalized_toroidal_flux_coordinate",
    ],
)
def test_unrelated_half_width_constructions_remain_rejected(name: str) -> None:
    with pytest.raises(ParseError):
        parse(name, strict=True)


def test_detector_width_of_construction_remains_parseable() -> None:
    name = "first_local_tangential_width_of_hard_xray_detector"

    assert compose(parse(name, strict=True).ir) == name
