"""Model-level round-trip for nested / composed operator names.

These names carry an OUTER unary operator (a prefix transformation like
``time_derivative``/``gradient`` or a postfix ``magnitude``) wrapping an
INNER expression that itself contains a bare-prefix transformation
qualifier (``volume_averaged``, ``flux_surface_averaged``,
``normalized``, ...).

The bug being guarded here lives in the parse-side IR->model adapter
(``_ir_to_model_dict``): the inner bare-prefix qualifier collided with
the outer operator's ``transformation`` slot and reordered tokens, so

    compose_standard_name(parse_standard_name(name)) != name

even though the IR-level round-trip (``compose(parse(name).ir)``) was
always correct. The flat :class:`StandardName` model has a single
``transformation`` and a single ``decomposition`` slot, so the inner
expression (projection + qualifiers + base, minus the outer operator,
locus and mechanism) must be folded into a single ``physical_base``
compound string — mirroring how binary operands are folded.

The flat model cannot represent two structurally distinct unary
operators, nor an inner expression that still carries a projection axis;
those names are a documented limitation and must keep raising rather than
silently dropping tokens.
"""

from __future__ import annotations

import pytest

from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)

# Names that MUST survive a full model-level round-trip after the fix:
# outer unary operator (prefix or postfix) wrapping an inner expression
# whose canonical spelling contains a bare-prefix transformation qualifier,
# optionally with a trailing locus on the outer model.
IN_SCOPE = [
    # of-prefix outer operator + inner bare-transformation + species subject
    "time_derivative_of_volume_averaged_electron_density",
    "time_derivative_of_flux_surface_averaged_pressure",
    "gradient_of_normalized_electron_temperature",
    # postfix outer operator + inner bare-transformation
    "volume_averaged_electron_density_magnitude",
    # outer operator + inner bare-transformation + trailing locus
    "time_derivative_of_volume_averaged_electron_density_at_magnetic_axis",
]

# Single-operator and binary cases that already round-tripped and must
# keep doing so (regression guard — the fold must not disturb them).
ALREADY_WORKING = [
    "time_derivative_of_electron_density",
    "gradient_of_electron_pressure",
    "volume_averaged_electron_density",
    "electron_density_magnitude",
    "ratio_of_electron_to_ion_temperature",
]

# Names the flat model provably cannot represent. Folding the inner
# expression into physical_base loses a token (a projection axis, or a
# second structurally-distinct unary operator), so the strict
# lossless-canonical guard MUST reject them rather than silently emit a
# token-dropped name. Documented limitation; tracked for a future nested
# model. Each entry is (name, the token folding would drop).
OUT_OF_SCOPE = [
    # outer operator wraps a PROJECTION axis: folding drops 'radial'
    "time_derivative_of_radial_electric_field",
    # operator-of-operator: folding drops the inner 'time_derivative'
    "gradient_of_time_derivative_of_electron_temperature",
]


@pytest.mark.parametrize("name", IN_SCOPE)
def test_in_scope_nested_operator_round_trips(name: str):
    model = parse_standard_name(name)
    assert compose_standard_name(model) == name


@pytest.mark.parametrize("name", ALREADY_WORKING)
def test_already_working_names_still_round_trip(name: str):
    model = parse_standard_name(name)
    assert compose_standard_name(model) == name


@pytest.mark.parametrize("name", OUT_OF_SCOPE)
def test_out_of_scope_nested_names_still_reject(name: str):
    """The flat model cannot represent these; they must raise, never
    silently drop a token. The lossless-canonical guard is the safety net.
    """
    with pytest.raises(ValueError):
        parse_standard_name(name)
