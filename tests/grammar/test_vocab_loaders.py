"""Tests for imas_standard_names.grammar.vocab_loaders (plan 38 W1c).

One test per loader asserting the seed file parses and strict-validates
cleanly, plus a cross-registry duplicate-name test.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.vocab_loaders import (
    CoordinateAxesRegistry,
    GeometryCarriersRegistry,
    LocusRegistry,
    OperatorRegistry,
    PhysicalBasesRegistry,
    load_coordinate_axes,
    load_geometry_carriers,
    load_locus_registry,
    load_operators,
    load_physical_bases,
    validate_no_cross_registry_duplicates,
)

# ---------------------------------------------------------------------------
# coordinate_axes.yml
# ---------------------------------------------------------------------------


def test_load_coordinate_axes_returns_registry():
    reg = load_coordinate_axes()
    assert isinstance(reg, CoordinateAxesRegistry)


def test_coordinate_axes_has_seed_entries():
    reg = load_coordinate_axes()
    expected = {
        "radial",
        "vertical",
        "toroidal",
        "poloidal",
        "parallel",
        "perpendicular",
        "x",
        "y",
    }
    assert expected.issubset(reg.axes.keys()), (
        f"Missing seed axes: {expected - reg.axes.keys()}"
    )


def test_coordinate_axes_aliases_parsed():
    reg = load_coordinate_axes()
    assert reg.axes["radial"].aliases == ["r"]
    assert set(reg.axes["toroidal"].aliases) == {"phi", "tor"}
    assert reg.axes["parallel"].aliases == []


# ---------------------------------------------------------------------------
# locus_registry.yml
# ---------------------------------------------------------------------------


def test_load_locus_registry_returns_registry():
    reg = load_locus_registry()
    assert isinstance(reg, LocusRegistry)


def test_locus_registry_has_seed_entries():
    reg = load_locus_registry()
    expected = {
        "plasma_boundary",
        "magnetic_axis",
        "separatrix",
        "x_point",
        "flux_loop",
        "wall",
        "pedestal",
    }
    assert expected.issubset(reg.loci.keys()), (
        f"Missing seed loci: {expected - reg.loci.keys()}"
    )


def test_locus_entry_types_are_valid():
    reg = load_locus_registry()
    valid_types = {"entity", "position", "geometry"}
    for name, entry in reg.loci.items():
        assert entry.type in valid_types, f"Invalid type for '{name}': {entry.type}"


def test_locus_entry_relations_are_valid():
    reg = load_locus_registry()
    valid_rels = {"of", "at", "over"}
    for name, entry in reg.loci.items():
        bad = set(entry.allowed_relations) - valid_rels
        assert not bad, f"Invalid relations for '{name}': {bad}"


def test_plasma_boundary_entity_of_only():
    # plasma_boundary reclassified to position in vNext (plan 38 §A5)
    reg = load_locus_registry()
    pb = reg.loci["plasma_boundary"]
    assert pb.type == "position"
    assert set(pb.allowed_relations) == {"at", "of"}


def test_magnetic_axis_position_at_and_of():
    reg = load_locus_registry()
    ma = reg.loci["magnetic_axis"]
    assert ma.type == "position"
    assert set(ma.allowed_relations) == {"at", "of"}


# ---------------------------------------------------------------------------
# operators.yml
# ---------------------------------------------------------------------------


def test_load_operators_returns_registry():
    reg = load_operators()
    assert isinstance(reg, OperatorRegistry)


def test_operators_has_seed_entries():
    reg = load_operators()
    expected = {
        "magnitude",
        "time_derivative",
        "time_average",
        "root_mean_square",
        "fourier_coefficient",
        "ratio",
        "product",
    }
    assert expected.issubset(reg.operators.keys()), (
        f"Missing seed operators: {expected - reg.operators.keys()}"
    )


def test_operator_kinds_are_valid():
    reg = load_operators()
    valid_kinds = {"unary_prefix", "unary_postfix", "binary"}
    for name, op in reg.operators.items():
        assert op.kind in valid_kinds, f"Invalid kind for '{name}': {op.kind}"


def test_magnitude_is_unary_postfix():
    reg = load_operators()
    mag = reg.operators["magnitude"]
    assert mag.kind == "unary_postfix"
    assert mag.returns == "scalar"
    assert "vector" in (mag.arg_types or [])


def test_fourier_coefficient_is_indexed():
    reg = load_operators()
    fc = reg.operators["fourier_coefficient"]
    assert fc.indexed is True
    assert fc.index_params is not None
    assert set(fc.index_params) == {"m", "n"}


def test_binary_operators_have_separators():
    reg = load_operators()
    for name, op in reg.operators.items():
        if op.kind == "binary":
            assert op.separator is not None, (
                f"Binary operator '{name}' must have a separator"
            )


def test_operator_precedences_are_positive_int():
    reg = load_operators()
    for name, op in reg.operators.items():
        assert isinstance(op.precedence, int) and op.precedence > 0, (
            f"Operator '{name}' has invalid precedence: {op.precedence}"
        )


# ---------------------------------------------------------------------------
# physical_bases.yml  (stub — empty for now)
# ---------------------------------------------------------------------------


def test_load_physical_bases_returns_registry():
    reg = load_physical_bases()
    assert isinstance(reg, PhysicalBasesRegistry)


def test_physical_bases_stub_is_populated():
    """W2a populated physical_bases.yml from corpus mining."""
    reg = load_physical_bases()
    assert len(reg.bases) >= 150


# ---------------------------------------------------------------------------
# geometry_carriers.yml  (stub — empty for now)
# ---------------------------------------------------------------------------


def test_load_geometry_carriers_returns_registry():
    reg = load_geometry_carriers()
    assert isinstance(reg, GeometryCarriersRegistry)


def test_geometry_carriers_stub_is_populated():
    """W2a populated geometry_carriers.yml from corpus mining."""
    reg = load_geometry_carriers()
    assert len(reg.carriers) >= 10


# ---------------------------------------------------------------------------
# Cross-registry: no duplicate token names
# ---------------------------------------------------------------------------


def test_no_cross_registry_duplicates():
    """Token names must be unique across all five vNext registries."""
    # Should not raise
    validate_no_cross_registry_duplicates()


def test_cross_registry_detects_duplicate(monkeypatch):
    """Inject a duplicate and confirm ValueError is raised."""
    import imas_standard_names.grammar.vocab_loaders as _m

    original_load_locus = _m.load_locus_registry

    def _patched_locus():
        reg = original_load_locus()
        # Inject a name that also exists in coordinate_axes
        from imas_standard_names.grammar.vocab_loaders import LocusEntry

        reg.loci["radial"] = LocusEntry(type="entity", allowed_relations=["of"])
        return reg

    monkeypatch.setattr(_m, "load_locus_registry", _patched_locus)

    with pytest.raises(ValueError, match="radial"):
        _m.validate_no_cross_registry_duplicates()
