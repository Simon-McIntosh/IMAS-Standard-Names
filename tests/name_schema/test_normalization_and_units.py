import pytest

from imas_standard_names.models import create_standard_name_entry


def test_unit_dimensionless_normalization():
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "beta_pol",
            "description": "Dimensionless plasma beta",
            "unit": "1",
            "status": "active",
        }
    )
    assert sn.unit == ""
    assert sn.is_dimensionless


def test_unit_whitespace_rejected():
    with pytest.raises(ValueError):
        create_standard_name_entry(
            {
                "kind": "scalar",
                "name": "some_quantity",
                "description": "whitespace unit",
                "unit": "m / s",
                "status": "draft",
            }
        )


@pytest.mark.parametrize(
    "style,expected_variants",
    [
        # Plain (~P) may emit Unicode superscript or caret fallback; both accepted
        ("plain", ("m/s²", "m/s^2")),
        # Canonical fused dot-exponent short-symbol style
        ("dotexp", ("m.s^-2",)),
        # LaTeX expanded symbols
        ("latex", ("$`\\frac{\\mathrm{meter}}{\\mathrm{second}^{2}}`$",)),
    ],
)
def test_formatted_unit_styles(style, expected_variants):
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "acceleration",
            "description": "Acceleration",
            "unit": "m.s^-2",
            "status": "active",
        }
    )
    formatted = sn.formatted_unit(style=style)
    assert formatted in expected_variants, (
        f"Got {formatted!r} not in {expected_variants}"
    )


def test_formatted_unit_unknown_style():
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "electron_density",
            "description": "Electron density",
            "unit": "m^-3",
            "status": "draft",
        }
    )
    with pytest.raises(ValueError):
        sn.formatted_unit(style="bogus")


def test_tags_and_links_normalization():
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "ion_temperature",
            "description": "Ion T",
            "unit": "eV",
            "status": "active",
            "tags": [" fundamental ", "time-dependent", ""],
            "links": ["  https://example.com/ref  ", "", "https://example.com/ref"],
            "constraints": [" Ti >= 0 ", ""],
        }
    )
    assert sn.tags == ["fundamental", "time-dependent"]
    assert sn.links == [
        "https://example.com/ref",
        "https://example.com/ref",
    ]  # duplication not removed (documented)
    assert sn.constraints == ["Ti >= 0"]


def test_deprecated_without_superseded_by_error():
    with pytest.raises(ValueError):
        create_standard_name_entry(
            {
                "kind": "scalar",
                "name": "old_quantity",
                "description": "Deprecated item",
                "unit": "eV",
                "status": "deprecated",
            }
        )


def test_deprecated_with_superseded_by_ok():
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "old_quantity2",
            "description": "Deprecated item",
            "unit": "eV",
            "status": "deprecated",
            "superseded_by": "new_quantity",
        }
    )
    assert sn.superseded_by == "new_quantity"


def test_unit_auto_canonical_ordering():
    """Test that units are automatically reordered to canonical lexicographic form."""
    # Test case 1: s^-2.m should be auto-corrected to m.s^-2
    sn1 = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "acceleration_test",
            "description": "Test acceleration",
            "unit": "s^-2.m",  # Non-canonical order
            "status": "draft",
        }
    )
    assert sn1.unit == "m.s^-2", f"Expected 'm.s^-2', got '{sn1.unit}'"

    # Test case 2: keV.m^-1 should remain keV.m^-1 (already canonical)
    sn2 = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "energy_gradient",
            "description": "Energy gradient",
            "unit": "keV.m^-1",
            "status": "draft",
        }
    )
    assert sn2.unit == "keV.m^-1"

    # Test case 3: Complex non-canonical order
    sn3 = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "complex_quantity",
            "description": "Complex quantity",
            "unit": "T.m^-2.A",  # Should become A.T.m^-2
            "status": "draft",
        }
    )
    assert sn3.unit == "A.T.m^-2", f"Expected 'A.T.m^-2', got '{sn3.unit}'"

    # Test case 4: Multiple tokens out of order
    sn4 = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "another_quantity",
            "description": "Another quantity",
            "unit": "s.kg.m^2",  # Should become kg.m^2.s
            "status": "draft",
        }
    )
    assert sn4.unit == "kg.m^2.s", f"Expected 'kg.m^2.s', got '{sn4.unit}'"
