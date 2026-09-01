"""The minimum-absolute-safety-factor surface has an unambiguous locus token."""

import pytest

from imas_standard_names import ParseError, compose, parse
from imas_standard_names.grammar.ir import LocusRelation, LocusType
from imas_standard_names.grammar.vocab_loaders import load_locus_registry


def test_minimum_absolute_safety_factor_is_a_position_locus() -> None:
    registry = load_locus_registry()

    assert "minimum_safety_factor" not in registry.loci
    locus = registry.loci["minimum_absolute_safety_factor"]
    assert locus.type == "position"
    assert locus.allowed_relations == ["at", "of"]
    assert (
        locus.definition
        == "The surface where the absolute value of the safety factor is minimum."
    )


def test_minimum_absolute_safety_factor_parses_as_at_locus() -> None:
    name = "radial_coordinate_at_minimum_absolute_safety_factor"
    parsed = parse(name, strict=True)

    assert parsed.ir.locus is not None
    assert parsed.ir.locus.token == "minimum_absolute_safety_factor"
    assert parsed.ir.locus.type is LocusType.POSITION
    assert parsed.ir.locus.relation is LocusRelation.AT


def test_minimum_safety_factor_no_longer_resolves_as_locus() -> None:
    with pytest.raises(ParseError):
        parse("safety_factor_at_minimum_safety_factor", strict=True)


def test_safety_factor_at_minimum_absolute_safety_factor_round_trips() -> None:
    name = "safety_factor_at_minimum_absolute_safety_factor"

    assert compose(parse(name, strict=True).ir) == name
