"""Locus definitions describe physical locations without source-schema wording."""

import re

import pytest

from imas_standard_names.grammar.vocab_loaders import (
    load_concepts,
    load_locus_registry,
)

DICTIONARY_REFERENCE = re.compile(
    r"\bDD\b|\bmidplane_identifier\b|\bdr_dz_zero_sep\b|"
    r"\boption\s+['\"]|\b(?:[a-z][a-z0-9_]*\/){2,}[a-z*][a-z0-9_*]*",
    re.IGNORECASE,
)
MIDPLANE_LOCI = (
    "outboard_midplane",
    "inboard_midplane",
    "outboard_midplane_separatrix",
)


def test_locus_definitions_exclude_dictionary_references() -> None:
    """All definitions stay independent of field paths and option spellings."""
    loci = load_locus_registry().loci
    references = [
        name
        for name, entry in loci.items()
        if entry.definition and DICTIONARY_REFERENCE.search(entry.definition)
    ]
    assert not references, f"Dictionary wording in: {', '.join(references)}"
    derivatives = [
        name
        for name in MIDPLANE_LOCI
        if re.search(r"dR/dZ", loci[name].definition, re.IGNORECASE)
    ]
    assert not derivatives, f"Derivative wording in: {', '.join(derivatives)}"


@pytest.mark.parametrize(
    ("name", "side", "extremum"),
    (
        ("outboard_midplane", "low-field", "maximum"),
        ("inboard_midplane", "high-field", "minimum"),
    ),
)
def test_midplane_definitions_state_the_major_radius_relation(
    name: str, side: str, extremum: str
) -> None:
    """Each midplane is the extremum of the major radius on its field side."""
    definition = load_locus_registry().loci[name].definition.casefold()
    assert f"{side}-side equatorial midplane" in definition
    assert f"point of {extremum} major radius" in definition


def test_outboard_midplane_separatrix_is_the_maximum_radius_point() -> None:
    """The separatrix locus is where the separatrix reaches its largest radius."""
    definition = load_locus_registry().loci["outboard_midplane_separatrix"]
    lowered = definition.definition.casefold()
    assert "separatrix" in lowered
    assert "maximum major radius" in lowered


@pytest.mark.parametrize(
    ("name", "relation"),
    (
        ("outboard_midplane", r"R = \max_{S} R,\quad R > R_{\mathrm{axis}}"),
        ("inboard_midplane", r"R = \min_{S} R,\quad R < R_{\mathrm{axis}}"),
    ),
)
def test_midplane_concepts_state_the_major_radius_relation(
    name: str, relation: str
) -> None:
    """Each midplane concept equation states its major-radius extremum."""
    assert load_concepts().concepts[name].equation == relation
