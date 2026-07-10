"""regions.yml must mirror the ``type: region`` loci in locus_registry.yml.

The locus registry is the authoritative typing source. A locus typed
``region`` there is a region (``over_<region>``); one typed ``position`` (e.g.
halo_boundary, sampled as ``at_halo_boundary``) is not. Keeping regions.yml in
lockstep prevents the region-vs-position typing conflict from reappearing.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_VOCAB = (
    Path(__file__).resolve().parents[1]
    / "imas_standard_names"
    / "grammar"
    / "vocabularies"
)


def _regions() -> set[str]:
    data = yaml.safe_load((_VOCAB / "regions.yml").read_text(encoding="utf-8"))
    return {token for token in data if isinstance(token, str)}


def _region_typed_loci() -> set[str]:
    data = yaml.safe_load((_VOCAB / "locus_registry.yml").read_text(encoding="utf-8"))
    return {
        token
        for token, entry in data["loci"].items()
        if entry.get("type") == "region"
    }


def test_regions_match_region_typed_loci():
    assert _regions() == _region_typed_loci()


def test_halo_boundary_is_position_not_region():
    # halo_boundary is sampled as at_halo_boundary (a position), so it must not
    # be classified as a region.
    assert "halo_boundary" not in _regions()
