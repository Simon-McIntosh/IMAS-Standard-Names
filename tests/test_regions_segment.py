"""Tests for the region segment (plan 29 / ADR-4 F4).

Region is a suffix segment that uses the ``over_{token}`` template and is
mutually exclusive with both ``geometry`` (``of_{token}``) and
``position`` (``at_{token}``). It represents a multi-dimensional locus
(volume, banded layer, or extended zone) over which a quantity is
integrated, averaged, or otherwise reduced::

    electron_temperature_over_halo_region
    pressure_over_core_region
    radiated_power_over_divertor_region
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    StandardName,
    compose_standard_name,
    parse_standard_name,
)
from imas_standard_names.grammar.model_types import Position, Region


@pytest.mark.parametrize(
    "name,expected_region,expected_base",
    [
        ("electron_temperature_over_halo_region", Region.HALO_REGION, "temperature"),
        ("pressure_over_core_region", Region.CORE_REGION, "pressure"),
        (
            "radiated_power_over_divertor_region",
            Region.DIVERTOR_REGION,
            "radiated_power",
        ),
        (
            "electron_density_over_scrape_off_layer",
            Region.SCRAPE_OFF_LAYER,
            "density",
        ),
        ("temperature_over_edge_region", Region.EDGE_REGION, "temperature"),
        (
            "magnetic_field_over_halo_boundary",
            Region.HALO_BOUNDARY,
            "magnetic_field",
        ),
    ],
)
def test_region_round_trip(
    name: str, expected_region: Region, expected_base: str
) -> None:
    """Parse then compose should recover the original name for every region token."""
    parsed = parse_standard_name(name)
    assert parsed.region == expected_region
    assert parsed.physical_base == expected_base
    assert compose_standard_name(parsed) == name


def test_region_direct_construction() -> None:
    """A StandardName with region set should compose with the over_ template."""
    sn = StandardName(physical_base="temperature", region=Region.HALO_REGION)
    assert compose_standard_name(sn) == "temperature_over_halo_region"


def test_region_excludes_position() -> None:
    """region and position cannot both be set on the same name."""
    with pytest.raises(
        ValueError, match="'position' and 'region'|'region' and 'position'"
    ):
        StandardName(
            physical_base="temperature",
            position=Position.MAGNETIC_AXIS,
            region=Region.HALO_REGION,
        )


def test_region_excludes_geometry() -> None:
    """region and geometry cannot both be set on the same name."""
    with pytest.raises(
        ValueError, match="'geometry' and 'region'|'region' and 'geometry'"
    ):
        StandardName(
            physical_base="major_radius",
            geometry=Position.PLASMA_BOUNDARY,
            region=Region.CORE_REGION,
        )


def test_region_tokens_not_in_positions_vocabulary() -> None:
    """Region tokens must have been moved out of the positions vocabulary.

    The old-style ``..._at_halo_region`` name must no longer parse as a
    ``position``; instead it falls through to a bare physical_base (no
    suffix recognized). Constructing a StandardName with a Position value
    of ``halo_region`` must fail since the enum no longer contains it.
    """
    parsed = parse_standard_name("electron_temperature_at_halo_region")
    assert parsed.position is None
    assert parsed.region is None

    # Construction with a nonexistent Position value must fail.
    with pytest.raises(ValueError):
        Position("halo_region")


def test_region_requires_physical_base() -> None:
    """region attaches to physical_base; a bare region is not a valid name."""
    with pytest.raises(ValueError):
        StandardName(region=Region.HALO_REGION).model_validate(
            {"region": "halo_region"}
        )


def test_region_with_subject_prefix() -> None:
    """Region segment combines with a subject prefix cleanly."""
    name = "electron_temperature_over_core_region"
    parsed = parse_standard_name(name)
    assert parsed.subject is not None
    assert parsed.region == Region.CORE_REGION
    assert compose_standard_name(parsed) == name
