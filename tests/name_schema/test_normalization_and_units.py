import pytest
from imas_standard_names.schema import create_standard_name


def test_unit_dimensionless_normalization():
    sn = create_standard_name(
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
        create_standard_name(
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
        # Pretty (~P) may emit Unicode superscript or ASCII fallback depending on locale/terminal
        ("plain", ("m/s²", "m/s^2")),
        # Custom registered 'pint' (~F) format should produce dotted with negative exponent form
        ("pint", ("m.s^-2",)),
        # LaTeX form includes full wrapper added in schema ( $`...`$ )
        ("latex", ("$`\\frac{\\mathrm{meter}}{\\mathrm{second}^{2}}`$",)),
    ],
)
def test_formatted_unit_styles(style, expected_variants):
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "acceleration",
            "description": "Acceleration",
            "unit": "m/s^2",
            "status": "active",
        }
    )
    formatted = sn.formatted_unit(style=style)
    assert formatted in expected_variants, (
        f"Got {formatted!r} not in {expected_variants}"
    )


def test_formatted_unit_unknown_style():
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "electron_density",
            "description": "Electron density",
            "unit": "1/m^3",
            "status": "draft",
        }
    )
    with pytest.raises(ValueError):
        sn.formatted_unit(style="bogus")


def test_tags_and_links_normalization():
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "ion_temperature",
            "description": "Ion T",
            "unit": "eV",
            "status": "active",
            "tags": [" core ", "temperature", ""],
            "links": ["  https://example.com/ref  ", "", "https://example.com/ref"],
            "constraints": [" Ti >= 0 ", ""],
        }
    )
    assert sn.tags == ["core", "temperature"]
    assert sn.links == [
        "https://example.com/ref",
        "https://example.com/ref",
    ]  # duplication not removed (documented)
    assert sn.constraints == ["Ti >= 0"]


def test_deprecated_without_superseded_by_error():
    with pytest.raises(ValueError):
        create_standard_name(
            {
                "kind": "scalar",
                "name": "old_quantity",
                "description": "Deprecated item",
                "unit": "eV",
                "status": "deprecated",
            }
        )


def test_deprecated_with_superseded_by_ok():
    sn = create_standard_name(
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
