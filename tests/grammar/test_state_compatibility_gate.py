"""Gates for the `state` segment: it requires a species subject, and the
state token must be compatible with that species.

- charge_state resolves the ionization state of an ion — valid on ion-like
  subjects (ion, impurity_ion, and element/isotope species like argon).
- internal_state resolves the internal (electronic/vibrational/rotational)
  degrees of freedom of a neutral — valid on neutral-like subjects (and, as a
  future-legal pairing, on ions for molecular ions).
- A bare state token with no species subject has no referent and is rejected.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    StandardName,
    compose_standard_name,
    parse_standard_name,
)


def test_state_without_subject_rejected() -> None:
    with pytest.raises(ValueError, match="requires a species subject"):
        compose_standard_name(
            StandardName(state="charge_state", physical_base="density")
        )


def test_charge_state_on_ion_ok() -> None:
    name = compose_standard_name(
        StandardName(subject="ion", state="charge_state", physical_base="density")
    )
    assert name == "ion_charge_state_density"


def test_internal_state_on_neutral_ok() -> None:
    p = parse_standard_name("neutral_internal_state_density")
    assert p.state.value == "internal_state"
    assert p.subject.value == "neutral"


def test_charge_state_on_neutral_rejected() -> None:
    with pytest.raises(ValueError, match="not valid on subject 'neutral'"):
        compose_standard_name(
            StandardName(
                subject="neutral", state="charge_state", physical_base="density"
            )
        )


def test_charge_state_on_element_species_ok() -> None:
    # Element/isotope species count as ion-like for charge_state resolution —
    # the impurity-transport customer (argon_charge_state_density, etc.).
    name = compose_standard_name(
        StandardName(subject="argon", state="charge_state", physical_base="density")
    )
    assert name == "argon_charge_state_density"


def test_internal_state_on_ion_allowed_future_pairing() -> None:
    # Molecular ions carry internal states; the compatibility map permits
    # ion + internal_state even though no catalog name needs it yet.
    name = compose_standard_name(
        StandardName(subject="ion", state="internal_state", physical_base="density")
    )
    assert name == "ion_internal_state_density"
