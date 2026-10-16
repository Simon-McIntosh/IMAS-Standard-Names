"""Template entries that require or exclude tokens, and carry a note.

A template pattern is a base plus the segment kinds a name must fill. A
conditioned entry narrows that pattern further: ``requires`` names, per
segment kind, the tokens a name must carry, and ``excludes`` names the segment
kinds a name must not fill. Each conditioned entry is written in a scratch
copy of the conventions directory so the shipped registry is untouched.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from imas_standard_names.grammar import vocab_loaders
from imas_standard_names.grammar.ir import OperatorKind
from imas_standard_names.grammar.parser import parse
from imas_standard_names.grammar.terms import (
    _ir_segments,
    select_conventions,
    template_sentences,
)
from imas_standard_names.grammar.vocab_loaders import (
    load_conventions,
    load_templates,
)

_CONVENTIONS_DIR = Path(vocab_loaders._CONVENTIONS_DIR)


def _scratch_templates(tmp_path: Path, text: str) -> Path:
    """A scratch conventions directory with ``templates.yml`` replaced."""
    scratch = tmp_path / "conventions"
    shutil.copytree(_CONVENTIONS_DIR, scratch)
    (scratch / "templates.yml").write_text(text, encoding="utf-8")
    return scratch


def _selected_bases(scratch: Path, name: str) -> list[str]:
    registry = load_conventions(scratch)
    return [t.base for t in select_conventions(name, registry=registry).templates]


# ---------------------------------------------------------------------------
# Required tokens
# ---------------------------------------------------------------------------


REQUIRES_NEUTRALS = """\
templates:
  - base: temperature
    segments:
      - subject
    requires:
      population: [cold, hot]
    description: Neutral temperature
    documentation: Temperature of a cold or hot neutral population
"""


def test_required_token_admits_only_names_carrying_the_token(tmp_path):
    scratch = _scratch_templates(tmp_path, REQUIRES_NEUTRALS)
    for name in ("cold_neutral_temperature", "hot_neutral_temperature"):
        assert _selected_bases(scratch, name) == ["temperature"], name
    # A name of the same pattern that carries no required-population token is
    # not admitted.
    for name in ("neutral_temperature", "electron_temperature"):
        assert _selected_bases(scratch, name) == [], name


def test_required_token_that_is_not_a_grammar_token_is_refused(tmp_path):
    scratch = _scratch_templates(
        tmp_path,
        """\
templates:
  - base: temperature
    segments:
      - subject
    requires:
      population: [lukewarm]
    description: Neutral temperature
    documentation: Temperature of a cold or hot neutral population
""",
    )
    with pytest.raises(ValueError, match="lukewarm"):
        load_templates(scratch)


# ---------------------------------------------------------------------------
# Excluded segment kinds
# ---------------------------------------------------------------------------


EXCLUDES_ZONE = """\
templates:
  - base: triangularity
    excludes:
      - zone
    description: Triangularity
    documentation: Triangularity of the plasma boundary
"""


def test_excluded_segment_kind_admits_only_names_without_it(tmp_path):
    scratch = _scratch_templates(tmp_path, EXCLUDES_ZONE)
    assert _selected_bases(scratch, "triangularity_of_plasma_boundary") == [
        "triangularity"
    ]
    for name in (
        "upper_triangularity_of_plasma_boundary",
        "lower_triangularity_of_plasma_boundary",
    ):
        assert _selected_bases(scratch, name) == [], name


def test_excluded_kind_that_is_not_a_segment_kind_is_refused(tmp_path):
    scratch = _scratch_templates(
        tmp_path,
        """\
templates:
  - base: triangularity
    excludes:
      - not_a_segment
    description: Triangularity
    documentation: Triangularity of the plasma boundary
""",
    )
    with pytest.raises(ValueError, match="not_a_segment"):
        load_templates(scratch)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


NOTE_ON_DENSITY = """\
templates:
  - base: density
    segments:
      - subject
    description: Number density of {subject}
    documentation: Number density of {subject}
    note: >-
      The unqualified density sums species; a population qualifier restricts it.
"""


def test_note_renders_after_the_opening_on_selecting_names_only(tmp_path):
    scratch = _scratch_templates(tmp_path, NOTE_ON_DENSITY)
    registry = load_conventions(scratch)
    note = "The unqualified density sums species; a population qualifier restricts it."
    applied = select_conventions("electron_density", registry=registry)
    assert len(applied.templates) == 1
    template = applied.templates[0]
    assert template.note == note
    rendered = template_sentences("electron_density", registry=registry)
    assert rendered == (template.documentation, note)
    # A name the entry does not select renders no note, on the same base.
    assert note not in template_sentences("electron_temperature", registry=registry)


def test_note_appears_once_when_a_name_selects_two_openings(tmp_path):
    scratch = _scratch_templates(
        tmp_path,
        """\
templates:
  - base: density
    segments:
      - subject
    description: Number density of {subject}
    documentation: Number density of {subject}
  - base: density
    segments:
      - aggregation
    description: '{aggregation} density of {subject}'
    documentation: '{aggregation} density of {subject}'
    note: Total density sums the species contributions.
""",
    )
    registry = load_conventions(scratch)
    rendered = template_sentences("total_electron_density", registry=registry)
    assert sum("Total density sums" in text for text in rendered) == 1
    assert all(
        "Total density sums" not in text
        for text in template_sentences("electron_density", registry=registry)
    )


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


UNQUALIFIED_TRIANGULARITY = """\
templates:
  - base: triangularity
    description: Triangularity
    documentation: Triangularity of the plasma boundary
  - base: triangularity
    excludes:
      - zone
    description: Unqualified triangularity
    documentation: Triangularity without a zone qualifier
    note: The unqualified triangularity is not the upper or lower form.
"""


def test_conditioned_entry_supersedes_its_unconditioned_sibling(tmp_path):
    """When a conditioned entry and an unconditioned sibling both match, the
    conditioned entry is selected and the unconditioned sibling is dropped."""
    scratch = _scratch_templates(tmp_path, UNQUALIFIED_TRIANGULARITY)
    registry = load_conventions(scratch)
    applied = select_conventions("triangularity_of_plasma_boundary", registry=registry)
    assert [t.documentation for t in applied.templates] == [
        "Triangularity without a zone qualifier"
    ]
    assert applied.templates[0].note
    # The conditioned entry excludes a zone, so a zoned name falls back to the
    # unconditioned sibling.
    zoned = select_conventions(
        "upper_triangularity_of_plasma_boundary", registry=registry
    )
    assert [t.documentation for t in zoned.templates] == [
        "Triangularity of the plasma boundary"
    ]
    assert all(t.note == "" for t in zoned.templates)


# ---------------------------------------------------------------------------
# Unconditioned templates follow the subset selection
# ---------------------------------------------------------------------------

# Names selected by unconditioned templates.
_UNCONDITIONED_TEMPLATE_NAMES = (
    "flux_surface_averaged_argon_density_at_plasma_boundary",
    "electron_density",
    "ratio_of_line_averaged_electron_density_to_greenwald_density",
    "difference_of_total_pressure_and_electron_pressure",
    "product_of_density_and_temperature",
)


def _subset_only_selection(name: str) -> list[tuple[str, tuple[str, ...]]]:
    """Select templates by base and segment-kind subset, without conditions."""
    ir = parse(name, strict=True).ir
    segments = _ir_segments(ir)
    bases = {op.op for op in ir.operators if op.kind is OperatorKind.BINARY}
    if ir.base.token != "placeholder":
        bases.add(ir.base.token)
    return [
        (entry.base, tuple(entry.segments))
        for entry in load_templates().templates
        if not entry.requires
        and not entry.excludes
        and entry.base in bases
        and set(entry.segments) <= segments
    ]


def test_unconditioned_templates_follow_subset_selection():
    shipped = load_templates()
    assert any(entry.requires or entry.excludes for entry in shipped.templates)
    for name in _UNCONDITIONED_TEMPLATE_NAMES:
        applied = select_conventions(name)
        assert [(t.base, t.segments) for t in applied.templates] == (
            _subset_only_selection(name)
        ), name
