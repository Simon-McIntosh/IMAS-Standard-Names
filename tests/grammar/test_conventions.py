"""The conventions registry, its token-validating loader and its accessor."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from imas_standard_names.grammar import vocab_loaders
from imas_standard_names.grammar.model import StandardName
from imas_standard_names.grammar.terms import select_conventions
from imas_standard_names.grammar.vocab_loaders import (
    TEMPLATE_SEGMENT_KINDS,
    load_concepts,
    load_conventions,
    load_notation,
    load_templates,
)

_CONVENTIONS_DIR = Path(vocab_loaders._CONVENTIONS_DIR)


def _scratch_conventions(tmp_path: Path, filename: str, text: str) -> Path:
    """A scratch copy of the shipped registry with one file replaced."""
    scratch = tmp_path / "conventions"
    shutil.copytree(_CONVENTIONS_DIR, scratch)
    (scratch / filename).write_text(text, encoding="utf-8")
    return scratch


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_shipped_registry_loads_all_three_files():
    registry = load_conventions()
    assert set(registry.concepts.concepts) == {
        "flux_surface_averaged",
        "plasma_boundary",
    }
    assert set(registry.notation.notation) == {"density"}
    assert [template.base for template in registry.templates.templates] == ["density"]


def test_density_notation_matches_the_seed():
    entry = load_notation().notation["density"]
    assert entry.symbol == "n_s"
    assert entry.forbidden_spellings == ["\\rho", "N_s"]
    assert "s" in entry.parameters


def test_template_segment_kinds_cover_the_flat_segments():
    assert set(StandardName.model_fields) <= TEMPLATE_SEGMENT_KINDS
    assert "subject" in TEMPLATE_SEGMENT_KINDS


# ---------------------------------------------------------------------------
# Loader refusals
# ---------------------------------------------------------------------------


def test_malformed_concepts_entry_is_refused_by_name(tmp_path):
    scratch = _scratch_conventions(
        tmp_path,
        "concepts.yml",
        """
concepts:
  flux_surface_averaged:
    phrase: flux-surface average
    restates_equation: false
""",
    )
    with pytest.raises(ValueError, match="flux_surface_averaged"):
        load_concepts(scratch)


def test_malformed_notation_entry_is_refused_by_name(tmp_path):
    scratch = _scratch_conventions(
        tmp_path,
        "notation.yml",
        """
notation:
  density:
    forbidden_spellings:
      - x
""",
    )
    with pytest.raises(ValueError, match="density"):
        load_notation(scratch)


def test_malformed_template_entry_is_refused(tmp_path):
    scratch = _scratch_conventions(
        tmp_path,
        "templates.yml",
        """
templates:
  - base: density
    segments:
      - subject
    description: Number density of {subject}
""",
    )
    with pytest.raises(ValueError, match="templates.yml"):
        load_templates(scratch)


def test_concept_key_that_is_not_a_token_is_refused_by_name(tmp_path):
    scratch = _scratch_conventions(
        tmp_path,
        "concepts.yml",
        """
concepts:
  not_a_real_token:
    phrase: not a real token
    equation: 'x = y'
    restates_equation: false
""",
    )
    with pytest.raises(ValueError, match="not_a_real_token"):
        load_concepts(scratch)


def test_forbidden_spelling_equal_to_a_registered_alias_is_refused(tmp_path):
    # atomic_number is a base token whose registered alias is nuclear_charge_number.
    scratch = _scratch_conventions(
        tmp_path,
        "notation.yml",
        """
notation:
  atomic_number:
    symbol: Z
    forbidden_spellings:
      - nuclear_charge_number
""",
    )
    with pytest.raises(ValueError, match="nuclear_charge_number"):
        load_notation(scratch)


def test_concept_restating_a_vocabulary_definition_is_refused(tmp_path):
    # plasma_boundary is a locus whose entry already carries the definition.
    scratch = _scratch_conventions(
        tmp_path,
        "concepts.yml",
        """
concepts:
  plasma_boundary:
    phrase: plasma boundary
    definition: A second definition of the plasma boundary.
    equation: '\\psi = \\psi_{\\mathrm{LCFS}}'
    restates_equation: false
""",
    )
    with pytest.raises(ValueError, match="plasma_boundary"):
        load_concepts(scratch)


# ---------------------------------------------------------------------------
# Accessor
# ---------------------------------------------------------------------------


def test_accessor_returns_exactly_the_applicable_entries():
    applied = select_conventions(
        "flux_surface_averaged_argon_density_at_plasma_boundary"
    )
    assert [concept.token for concept in applied.concepts] == [
        "flux_surface_averaged",
        "plasma_boundary",
    ]
    assert [entry.token for entry in applied.notation] == ["density"]
    assert [template.base for template in applied.templates] == ["density"]
    assert applied.templates[0].segments == ("subject",)


def test_accessor_fills_a_concept_definition_from_the_vocabulary():
    applied = select_conventions(
        "flux_surface_averaged_argon_density_at_plasma_boundary"
    )
    boundary = next(c for c in applied.concepts if c.token == "plasma_boundary")
    locus_definition = (
        vocab_loaders.load_locus_registry().loci["plasma_boundary"].definition
    )
    assert boundary.definition == locus_definition


def test_accessor_selects_from_the_parse_not_from_text():
    # A name with no operator or locus carries no concept, even though the
    # concept phrases are words a text search would find elsewhere.
    applied = select_conventions("electron_density")
    assert applied.concepts == ()
    assert [entry.token for entry in applied.notation] == ["density"]
    assert [template.base for template in applied.templates] == ["density"]
