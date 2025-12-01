from imas_standard_names.generic_names import GenericNames
from imas_standard_names.grammar.constants import GENERIC_PHYSICAL_BASES


def test_generic_names_membership():
    """Test GenericNames uses grammar vocabulary for generic physical bases."""
    g = GenericNames()
    # Verify membership checks work against grammar vocabulary
    assert "area" in g
    assert "current" in g
    assert "plasma_current" not in g  # Qualified names are not generic
    # Verify names property returns grammar vocabulary
    assert g.names == GENERIC_PHYSICAL_BASES


def test_generic_names_check_raises_for_generic():
    """Test check() raises KeyError for generic names."""
    g = GenericNames()
    try:
        g.check("area")
        raise AssertionError("Expected KeyError for generic name 'area'")
    except KeyError as e:
        assert "area" in str(e)
        assert "generic name" in str(e).lower()
