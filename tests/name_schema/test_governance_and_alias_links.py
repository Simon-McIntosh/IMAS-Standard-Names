from imas_standard_names.models import create_standard_name_entry


def test_links_trailing_whitespace_preserved_if_duplicate():
    # Current implementation does not deduplicate; we document that.
    sn = create_standard_name_entry(
        {
            "kind": "scalar",
            "name": "core_density",
            "description": "Core density",
            "unit": "m^-3",
            "status": "draft",
            "links": ["https://example.com/a", "https://example.com/a"],
        }
    )
    assert sn.links == ["https://example.com/a", "https://example.com/a"]


def test_constraints_trimmed():
    sn = create_standard_name_entry(
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
