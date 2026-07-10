"""The measurement-location advisory is suppressed for entity-typed loci.

``<base>_of_<entity>`` is the canonical intrinsic-property form for a
hardware/geometry carrier (the locus matrix maps ``entity -> of``), so the
"may indicate measurement location" advisory must not fire on it.
"""

from __future__ import annotations

from imas_standard_names.validation.semantic import (
    _check_physical_base_with_object,
    _entity_typed_loci,
)

_ADVISORY_MARKER = "may indicate measurement location"


def test_entity_object_does_not_trip_advisory():
    # poloidal_field_coil is an entity locus; power_of_... is a legitimate
    # intrinsic property, not a measurement-location smell.
    name = "nuclear_heating_power_of_poloidal_field_coil"
    issues = _check_physical_base_with_object(name, None)
    assert not any(_ADVISORY_MARKER in msg for msg in issues)


def test_entity_loci_are_registered():
    entities = _entity_typed_loci()
    assert "poloidal_field_coil" in entities
    assert "antenna_strap" in entities
