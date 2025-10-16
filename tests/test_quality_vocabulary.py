"""
Test quality validation vocabulary composition.

This test documents the vocabulary sources for domain-specific quality checks.
"""

from imas_standard_names.grammar.model import parse_standard_name
from imas_standard_names.grammar.types import (
    Component,
    Object,
    Position,
    Process,
    Source,
    Subject,
)
from imas_standard_names.operators import PRIMITIVE_OPERATORS
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.validation.quality import QualityChecker


def test_vocabulary_composition():
    """Test that quality checker builds vocabulary from three sources."""
    qc = QualityChecker()
    vocab = qc._build_physics_vocabulary()

    # Source 1: Grammar enums (Component, Subject, Object, Source, Position, Process)
    grammar_vocab = set()
    for enum_class in [Component, Subject, Object, Source, Position, Process]:
        grammar_vocab.update(member.value for member in enum_class)

    # Source 2: Catalog base names (extracted by parsing standard names)
    catalog = StandardNameCatalog()
    catalog_bases = {parse_standard_name(entry.name).base for entry in catalog.list()}

    # Source 3: Primitive operators (from operators.py)
    operators = PRIMITIVE_OPERATORS

    # Verify all sources are represented
    assert grammar_vocab.issubset(vocab), "Grammar vocabulary should be in total vocab"
    assert catalog_bases.issubset(vocab), "Catalog bases should be in total vocab"
    assert operators.issubset(vocab), "Operators should be in total vocab"

    # Verify no unexpected overlap (would indicate redundancy)
    grammar_catalog_overlap = grammar_vocab & catalog_bases
    grammar_operator_overlap = grammar_vocab & operators
    catalog_operator_overlap = catalog_bases & operators

    # Some overlap is expected (e.g., "magnetic_axis" might be both a position and a base)
    # but operators should be distinct
    assert len(grammar_operator_overlap) == 0, (
        "Grammar and operators should not overlap"
    )
    assert len(catalog_operator_overlap) == 0, (
        "Catalog and operators should not overlap"
    )

    # Document composition
    total_expected = len(grammar_vocab | catalog_bases | operators)
    assert len(vocab) == total_expected, (
        f"Expected {total_expected} unique terms, got {len(vocab)}"
    )

    # Log composition for documentation
    print("\n=== Quality Vocabulary Composition ===")
    print(f"Grammar terms: {len(grammar_vocab)}")
    print(f"Catalog bases: {len(catalog_bases)}")
    print(f"Operators: {len(operators)}")
    print(f"Total unique: {len(vocab)}")
    print(f"Grammar-catalog overlap: {len(grammar_catalog_overlap)}")


def test_vocabulary_sources_traceable():
    """Test that all vocabulary terms are traceable to a source."""
    qc = QualityChecker()
    vocab = qc._build_physics_vocabulary()

    # Every term should come from one of three sources
    grammar_vocab = set()
    for enum_class in [Component, Subject, Object, Source, Position, Process]:
        grammar_vocab.update(member.value for member in enum_class)

    catalog = StandardNameCatalog()
    catalog_bases = {parse_standard_name(entry.name).base for entry in catalog.list()}

    operators = PRIMITIVE_OPERATORS

    for term in vocab:
        assert term in grammar_vocab or term in catalog_bases or term in operators, (
            f"Term '{term}' not traceable to any source"
        )


def test_no_hardcoded_vocabulary():
    """Test that vocabulary is dynamically loaded, not hardcoded."""
    import inspect

    source = inspect.getsource(QualityChecker._build_physics_vocabulary)

    # Should not contain hardcoded lists of physics terms
    assert "['temperature'" not in source, "Should not have hardcoded term lists"
    assert '["temperature"' not in source, "Should not have hardcoded term lists"
    assert "{'temperature'" not in source, "Should not have hardcoded term sets"

    # Should contain dynamic loading from sources
    assert "for enum_class in" in source, "Should iterate over grammar enums"
    assert "catalog.list()" in source, "Should load from catalog"
    assert "PRIMITIVE_OPERATORS" in source, "Should use operators from operators.py"
