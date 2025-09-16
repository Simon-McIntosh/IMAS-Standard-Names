from imas_standard_names.schema import create_standard_name


def test_alias_field_optional():
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "ion_pressure",
            "description": "Ion pressure",
            "unit": "Pa",
            "status": "active",
            "alias": "ion_pressure_alt",
        }
    )
    assert sn.alias == "ion_pressure_alt"


def test_alias_blank():
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "electron_pressure",
            "description": "Electron pressure",
            "unit": "Pa",
            "status": "active",
            "alias": "",
        }
    )
    assert sn.alias == ""


def test_links_trailing_whitespace_preserved_if_duplicate():
    # Current implementation does not deduplicate; we document that.
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "core_density",
            "description": "Core density",
            "unit": "1/m^3",
            "status": "draft",
            "links": ["https://example.com/a", "https://example.com/a"],
        }
    )
    assert sn.links == ["https://example.com/a", "https://example.com/a"]


def test_constraints_trimmed():
    sn = create_standard_name(
        {
            "kind": "scalar",
            "name": "upper_bound_test",
            "description": "Test",
            "unit": "eV",
            "status": "draft",
            "constraints": ["  T > 0  ", ""],
        }
    )
    assert sn.constraints == ["T > 0"]
