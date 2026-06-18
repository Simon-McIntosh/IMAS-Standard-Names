"""Tests for the value-provenance (estimator) controlled vocabulary."""

from __future__ import annotations

import imas_standard_names as isn
from imas_standard_names.value_provenance import (
    VALUE_PROVENANCE,
    get_value_provenance,
    is_value_provenance,
    provenance_for_dd_facet,
    value_provenance_terms,
)


def test_closed_vocabulary_members():
    assert value_provenance_terms() == frozenset(
        {"measured", "reconstructed", "reference"}
    )


def test_public_api_reexport():
    # Importable from the package root (consumer boundary).
    assert isn.value_provenance_terms() == value_provenance_terms()
    assert isn.is_value_provenance("measured")
    assert not isn.is_value_provenance("plasma_current")


def test_each_term_has_description_and_facets():
    for term, defn in get_value_provenance().items():
        assert defn.description.strip()
        assert defn.dd_facets
        assert term in VALUE_PROVENANCE


def test_dd_facet_mapping():
    assert provenance_for_dd_facet("measured") == "measured"
    assert provenance_for_dd_facet("reconstructed") == "reconstructed"
    # The DD spells the control setpoint 'reference'; 'target' is an alias.
    assert provenance_for_dd_facet("reference") == "reference"
    assert provenance_for_dd_facet("target") == "reference"


def test_non_provenance_facets_return_none():
    # Fit metrics / generic holders are NOT value-provenance.
    for facet in (
        "weight",
        "chi_squared",
        "time_measurement",
        "exact",
        "data",
        "value",
    ):
        assert provenance_for_dd_facet(facet) is None


def test_get_value_provenance_returns_copy():
    v = get_value_provenance()
    v.clear()
    assert value_provenance_terms()  # original unchanged
