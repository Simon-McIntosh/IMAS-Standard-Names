"""Locus definitions describe physical locations without source-schema wording."""

import re

import pytest

from imas_standard_names.grammar.vocab_loaders import load_locus_registry

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
    ("name", "side"),
    (("outboard_midplane", "greater"), ("inboard_midplane", "less")),
)
def test_midplane_definitions_state_height_and_side(name: str, side: str) -> None:
    """Each midplane uses the selected height and its side of the axis."""
    definition = load_locus_registry().loci[name].definition.casefold()
    assert "midplane height" in definition
    assert "data's midplane identifier" in definition
    assert "magnetic-axis height when none is given" in definition
    assert f"major radius {side} than the magnetic-axis radius" in definition
