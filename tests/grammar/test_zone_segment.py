"""Zone segment: ordered plasma-region / geometric sub-selector prefix.

The ``zone`` segment (core, edge, pedestal, separatrix, divertor,
scrape_off_layer; vertical upper/lower; radial inner/outer; PFC face
front_surface/back_surface/wetted) renders between the subject/device and the
refined qualifiers:
``<aggregation>_<orbit>_<population>_<subject>_<device>_<zone...>_<base>``.

Unlike the single-token aggregation/orbit/population segments, a name may carry
MULTIPLE zone tokens (lower_outer). They are stored/rendered in a FIXED
canonical intra-order (vertical, radial, region, face — the Zone enum order),
so:

* a name authored in canonical order parses and round-trips, and
* a name whose zone tokens (or zone-vs-qualifier order) are out of canonical
  order parses at the IR level but is REJECTED by ``parse_standard_name`` with
  the canonical form attached (``NonCanonicalNameError``).
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar import compose_standard_name, parse_standard_name
from imas_standard_names.grammar.model import NonCanonicalNameError

# ---------------------------------------------------------------------------
# Canonical zone names parse → compose round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "zone_tokens"),
    [
        ("core_density_of_pellet", ("core",)),
        ("outer_atomic_count_of_pellet", ("outer",)),
        ("back_surface_curvature_of_optical_element", ("back_surface",)),
        ("lower_triangularity_of_flux_surface", ("lower",)),
        # multi-token zone (vertical precedes radial)
        ("lower_outer_squareness_of_flux_surface", ("lower", "outer")),
        ("upper_inner_squareness_of_flux_surface", ("upper", "inner")),
    ],
)
def test_zone_round_trip(name: str, zone_tokens: tuple[str, ...]) -> None:
    model = parse_standard_name(name)
    assert tuple(z.value for z in model.zone) == zone_tokens
    assert compose_standard_name(model) == name


def test_zone_renders_after_subject_before_base() -> None:
    """Zone tokens sit between the subject and the refined qualifier/base."""
    model = parse_standard_name("core_density_of_pellet")
    assert model.physical_base == "density"
    assert tuple(z.value for z in model.zone) == ("core",)


# ---------------------------------------------------------------------------
# Non-canonical zone order is rejected with the canonical form attached
# ---------------------------------------------------------------------------


def test_zone_out_of_intra_order_rejected() -> None:
    # radial (outer) before vertical (lower) is non-canonical
    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name("outer_lower_squareness_of_flux_surface")
    assert excinfo.value.canonical_form == "lower_outer_squareness_of_flux_surface"


def test_zone_after_qualifier_rejected() -> None:
    # a refined qualifier (minor) authored before the zone (inner) is
    # non-canonical: the zone must render before the base-bound qualifier.
    # (Uses minor_radius — a kept length scalar; major_radius + locus is now
    # §6-rejected outright, see test_major_radius_locus_rejected.)
    with pytest.raises(NonCanonicalNameError) as excinfo:
        parse_standard_name("minor_inner_radius_of_flux_surface")
    assert excinfo.value.canonical_form == "inner_minor_radius_of_flux_surface"


def test_major_radius_locus_rejected() -> None:
    # §6: a point's radial (R) coordinate is radial_coordinate_of_<X>, not
    # major_radius_of_<X>. major_radius carrying a positional/geometry locus
    # is rejected (bare major_radius = R0 and length/operator compounds stay
    # valid). Covers the compound-base form (beam_major_radius) too.
    for name in (
        "major_radius_of_strike_point",
        "inner_major_radius_of_flux_surface",
        "beam_major_radius_of_neutral_beam_injector",
    ):
        with pytest.raises(ValueError):
            parse_standard_name(name)
    # bare R0 reference and non-locus compounds remain valid
    for name in ("major_radius", "reference_major_radius"):
        parse_standard_name(name)


def test_zone_multi_token_canonicalizes_at_compose() -> None:
    """compose() emits zone tokens in canonical intra-order regardless of the
    order they were supplied in (the validator rejects the non-canonical input,
    but the model's compose() is the canonicalizer)."""
    from imas_standard_names.grammar.model import StandardName

    model = StandardName(physical_base="squareness", zone=("outer", "lower"))
    assert compose_standard_name(model) == "lower_outer_squareness"
