"""Value-provenance (estimator) controlled vocabulary.

Captures HOW a value of a physical quantity was obtained — measured by a
diagnostic, reconstructed by analysis/fit, or a requested control reference.

This is **metadata attached to the source -> standard-name link** in a
consuming catalog graph, NOT a standard-name segment. Value-provenance facets
COLLAPSE onto the base quantity name: the measured, reconstructed, and
reference values of the plasma current all map to ``plasma_current``; the
estimator is recorded on the link, never emitted in the name. (Contrast a
*physical-locus* difference such as ``_of_plasma_boundary`` vs
``_of_flux_surface``, which DOES de-conflate into distinct names.)

Distinct from the derivation provenance models in :mod:`imas_standard_names.provenance`
(operator / expression / reduction chains), which describe how a *derived* name
was built. This module describes which *estimate* of a quantity a value is.

Grounded in the IMAS Data Dictionary facet vocabulary: the ``.../measured`` and
``.../reconstructed`` reconstruction-constraint facets, and the
``.../reference`` control setpoints.
"""

from __future__ import annotations

from pydantic import BaseModel


class ValueProvenanceTerm(BaseModel, extra="forbid"):
    """A single value-provenance term."""

    description: str
    dd_facets: list[str]


# Closed controlled vocabulary — token -> definition. Extend only by governed
# addition (a new estimator kind), never ad hoc in consumers.
VALUE_PROVENANCE: dict[str, ValueProvenanceTerm] = {
    "measured": ValueProvenanceTerm(
        description="Value obtained directly from a diagnostic measurement.",
        dd_facets=["measured"],
    ),
    "reconstructed": ValueProvenanceTerm(
        description=(
            "Value produced by analysis, equilibrium reconstruction, or a fit "
            "to measurements."
        ),
        dd_facets=["reconstructed"],
    ),
    "reference": ValueProvenanceTerm(
        description=(
            "Requested control setpoint / target value (e.g. a pulse-schedule "
            "reference waveform)."
        ),
        dd_facets=["reference", "target"],
    ),
}


# DD path facet suffix -> canonical value-provenance term (path-based detection).
_DD_FACET_TO_TERM: dict[str, str] = {
    facet: term for term, defn in VALUE_PROVENANCE.items() for facet in defn.dd_facets
}


def get_value_provenance() -> dict[str, ValueProvenanceTerm]:
    """Return the value-provenance controlled vocabulary (token -> definition)."""
    return dict(VALUE_PROVENANCE)


def value_provenance_terms() -> frozenset[str]:
    """Return the set of registered value-provenance tokens."""
    return frozenset(VALUE_PROVENANCE)


def is_value_provenance(token: str) -> bool:
    """Return ``True`` if *token* is a registered value-provenance term."""
    return token in VALUE_PROVENANCE


def provenance_for_dd_facet(facet: str) -> str | None:
    """Map a DD path facet suffix (e.g. ``measured``, ``reference``) to its term.

    Returns ``None`` when the facet is not a value-provenance facet.
    """
    return _DD_FACET_TO_TERM.get(facet)


__all__ = [
    "VALUE_PROVENANCE",
    "ValueProvenanceTerm",
    "get_value_provenance",
    "is_value_provenance",
    "provenance_for_dd_facet",
    "value_provenance_terms",
]
