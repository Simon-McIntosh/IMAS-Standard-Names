"""Model-level round-trip for postfix operators stacked with a locus,
mechanism, or a prefix transformation.

These real-catalog forms combine a trailing **postfix** decomposition
operator (``magnitude``) with a locus/mechanism suffix, or nest a prefix
transformation with a postfix decomposition. The renderer
(:func:`compose`) already emits all of them — the postfix operator wraps
the ``base + locus + mechanism`` core, so the canonical spelling is
**base + locus/mechanism + postfix-op** (the postfix token sits at the very
end of the string, after the locus/mechanism suffix).

The parse side previously could not recover these IRs:

* Stage-1 mechanism strip and stage-2 locus strip ran BEFORE operator
  peeling and greedily absorbed the trailing postfix token into the
  process/locus token. ``velocity_due_to_pellet_injection_magnitude``
  parsed to a fabricated process token ``pellet_injection_magnitude``
  (silent loss of the ``magnitude`` operator);
  ``magnetic_field_of_iron_core_segment_magnitude`` failed to match any
  locus and then any base.
* The flat :class:`StandardName` model's ``_check_decomposition_exclusivity``
  validator forbade a prefix ``transformation`` and a postfix
  ``decomposition`` from coexisting, so ``maximum_of_magnetic_field_magnitude``
  raised even though the two operators occupy distinct, non-ambiguous slots
  (prefix renders ``maximum_of_<...>``; postfix renders ``<...>_magnitude``).

Canonical-order decisions encoded here:

* postfix-after-locus / postfix-after-mechanism is canonical
  (``..._of_iron_core_segment_magnitude``, ``..._due_to_<process>_magnitude``);
* prefix transformation is outermost, postfix decomposition innermost
  (``maximum_of_<base>_magnitude``);
* a bare-prefix transformation qualifier (``maximum_<base>``) coexists with a
  locus and a postfix operator (``maximum_<base>_of_<locus>_magnitude``).

The lossless-canonical guard remains the safety net: any name the flat
model cannot represent must RAISE, never drop a token.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)

# Postfix decomposition stacked with a locus / mechanism / prefix operator.
# Every token is registered (verified against the live vocabularies):
#   iron_core_segment -> object (entity locus, _of_)
#   flux_surface      -> position/geometry locus (_of_)
#   pellet_injection  -> process (mechanism, _due_to_)
#   magnitude         -> unary_postfix operator
#   maximum           -> unary_prefix operator (and bare-prefix qualifier)
IN_SCOPE = [
    # postfix op after an entity locus
    "magnetic_field_of_iron_core_segment_magnitude",
    # postfix op after a mechanism
    "velocity_due_to_pellet_injection_magnitude",
    # prefix transformation (of-form) wrapping a postfix decomposition
    "maximum_of_magnetic_field_magnitude",
    # bare-prefix transformation qualifier + locus + postfix decomposition
    "maximum_magnetic_field_of_flux_surface_magnitude",
]

# Component pieces that already round-tripped in isolation and must keep
# doing so (regression guard — the staged-parse reorder must not disturb
# the simpler forms).
ALREADY_WORKING = [
    "magnetic_field_magnitude",
    "magnetic_field_of_iron_core_segment",
    "velocity_due_to_pellet_injection",
    "maximum_magnetic_field",
    "maximum_magnetic_field_magnitude",
    "maximum_magnetic_field_of_flux_surface",
    "safety_factor_at_magnetic_axis",
]


@pytest.mark.parametrize("name", IN_SCOPE)
def test_in_scope_operator_locus_round_trips(name: str) -> None:
    model = parse_standard_name(name)
    assert compose_standard_name(model) == name


@pytest.mark.parametrize("name", ALREADY_WORKING)
def test_already_working_names_still_round_trip(name: str) -> None:
    model = parse_standard_name(name)
    assert compose_standard_name(model) == name


def test_mechanism_postfix_does_not_fabricate_process_token() -> None:
    """The postfix operator must NOT be absorbed into the process token.

    The danger case: a greedy mechanism strip swallows ``_magnitude`` into a
    fabricated ``pellet_injection_magnitude`` process token (not in the closed
    process vocabulary). The IR-level parse happened to re-render the same
    string, masking the lost operator. Assert the model carries the real
    process token and a real decomposition slot.
    """
    model = parse_standard_name("velocity_due_to_pellet_injection_magnitude")
    dump = model.model_dump_compact()
    assert dump.get("process") == "pellet_injection"
    assert dump.get("decomposition") == "magnitude"


def test_prefix_postfix_nest_populates_both_slots() -> None:
    """``maximum_of_magnetic_field_magnitude`` carries BOTH operator slots.

    Prefix transformation and postfix decomposition occupy distinct,
    non-ambiguous slots (prefix renders ``maximum_of_<...>``, postfix renders
    ``<...>_magnitude``). The flat model must accept both together.
    """
    model = parse_standard_name("maximum_of_magnetic_field_magnitude")
    dump = model.model_dump_compact()
    assert dump.get("transformation") == "maximum"
    assert dump.get("decomposition") == "magnitude"
    assert dump.get("physical_base") == "magnetic_field"
