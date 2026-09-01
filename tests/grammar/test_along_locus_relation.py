"""``along`` as a first-class locus relation.

A path-like position (``line_of_sight``, ``pellet_path``) that a quantity
varies ALONG — as opposed to a single point it is evaluated AT or an
intrinsic property OF — renders as ``<base>_along_<locus>`` via the new
``path`` model field (:data:`LocusRelation.ALONG`, shared with
``geometry``/``position`` on ``LocusType.POSITION``).

Before this relation existed, the closed vocabulary carried four flat
``along_*`` tokens (``along_beam``, ``along_beam_path``,
``along_line_of_sight``, ``along_pellet_path``) with ``allowed_relations:
[at, of]``. That produced a dangling double preposition when composed as a
suffix (``_of_along_line_of_sight``, ``_at_along_pellet_path``) — the
malformed forms this module asserts are now rejected outright, not silently
canonicalised, because ``_along_<token>`` strips first and leaves an
unparseable residue (``toroidal_angle_of``, ``electron_density_at``).
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name
from imas_standard_names.grammar.support import UnknownBaseTokenError

# ---------------------------------------------------------------------------
# Round-trips
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "locus_token"),
    [
        ("toroidal_angle_along_line_of_sight", "line_of_sight"),
        ("vertical_coordinate_along_line_of_sight", "line_of_sight"),
        ("electron_density_along_pellet_path", "pellet_path"),
        ("temperature_along_pellet_path", "pellet_path"),
    ],
)
def test_along_locus_round_trips(name, locus_token):
    model = parse_standard_name(name)
    assert model.path == locus_token
    assert model.position is None
    assert model.geometry is None
    assert compose_standard_name(model) == name


def test_along_relation_distinct_from_at_and_of():
    """The same locus token under all three relations parses to distinct
    IR/model states and each round-trips on its own spelling."""
    at_model = parse_standard_name("pressure_at_line_of_sight")
    of_model = parse_standard_name("pressure_of_line_of_sight")
    along_model = parse_standard_name("pressure_along_line_of_sight")

    assert at_model.position == "line_of_sight"
    assert at_model.path is None
    assert of_model.geometry == "line_of_sight"
    assert of_model.path is None
    assert along_model.path == "line_of_sight"
    assert along_model.position is None
    assert along_model.geometry is None

    assert compose_standard_name(at_model) == "pressure_at_line_of_sight"
    assert compose_standard_name(of_model) == "pressure_of_line_of_sight"
    assert compose_standard_name(along_model) == "pressure_along_line_of_sight"


# ---------------------------------------------------------------------------
# Legacy flat tokens are gone
# ---------------------------------------------------------------------------


def test_legacy_flat_along_tokens_removed_from_registry():
    from imas_standard_names.grammar import vocab_loaders

    loci = set(vocab_loaders.load_locus_registry().loci)
    for removed in (
        "along_beam",
        "along_beam_path",
        "along_line_of_sight",
        "along_pellet_path",
    ):
        assert removed not in loci, (
            f"{removed} should be composed via the along relation, not a flat token"
        )


# ---------------------------------------------------------------------------
# Malformed double-preposition forms are rejected, not canonicalised
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "toroidal_angle_of_along_line_of_sight",
        "electron_density_at_along_pellet_path",
        "major_radius_at_along_line_of_sight",
        "vertical_coordinate_at_along_line_of_sight",
    ],
)
def test_dangling_of_along_and_at_along_forms_rejected(name):
    # _along_<token> strips first (relation stripping tries "along" before
    # "of"), leaving a residue ending in a bare "_of"/"_at" that matches no
    # registered base — a hard parse failure, not a canonicalisation redirect
    # (these forms never produced a valid IR to canonicalise from).
    with pytest.raises(UnknownBaseTokenError):
        parse_standard_name(name)


def test_unregistered_along_locus_rejected():
    # `along` requires a registered position-typed locus, same strictness as
    # `over` for region — no vocab_gap fallback that would fabricate a locus.
    with pytest.raises(ValueError, match="made_up_path"):
        parse_standard_name("electron_temperature_along_made_up_path")


# ---------------------------------------------------------------------------
# path field participates in the shared locus invariants
# ---------------------------------------------------------------------------


def test_path_and_position_and_geometry_are_mutually_exclusive():
    from imas_standard_names.grammar.model import StandardName

    with pytest.raises(ValueError):
        StandardName(
            physical_base="temperature",
            path="line_of_sight",
            position="magnetic_axis",
        )


def test_path_satisfies_generic_physical_base_qualification():
    # 'temperature' is a generic physical_base that requires qualification;
    # a path locus alone must satisfy that requirement.
    model = parse_standard_name("temperature_along_pellet_path")
    assert model.path == "pellet_path"


def test_major_radius_cannot_take_along_locus():
    # Mirrors the existing major_radius + position/geometry restriction (§6):
    # a point's radial coordinate along a path is radial_coordinate_along_<X>,
    # not major_radius_along_<X>.
    from imas_standard_names.grammar.model import StandardName

    with pytest.raises(ValueError, match="major_radius"):
        StandardName(physical_base="major_radius", path="line_of_sight")
