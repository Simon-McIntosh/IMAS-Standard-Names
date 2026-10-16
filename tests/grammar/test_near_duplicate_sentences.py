"""Separating sentences follow the parsed name's template conditions."""

from itertools import product

import pytest

from imas_standard_names.grammar.terms import select_conventions, template_sentences
from imas_standard_names.grammar.vocab_loaders import (
    load_aggregations,
    load_populations,
    load_zones,
)

NEUTRAL_SENTENCE = (
    "A cold or hot neutral temperature is that of the named component alone; "
    "without the component it covers the whole neutral population of the selected species."
)
TRIANGULARITY_SENTENCE = (
    "Triangularity without a qualifier is the mean of the upper and lower triangularities; "
    "upper and lower triangularity each use one extremum of the cross-section."
)
DENSITY_SENTENCE = (
    "Total density is the sum of the thermal and fast populations of the species; "
    "thermal excludes the suprathermal particles that fast names."
)
SENTENCES = (NEUTRAL_SENTENCE, TRIANGULARITY_SENTENCE, DENSITY_SENTENCE)

TEMPERATURE_NAMES = (
    "electron_temperature",
    "ion_temperature",
    "neutral_temperature",
    *(f"{population}_neutral_temperature" for population in load_populations()),
)
TRIANGULARITY_CASES = tuple(
    (zone, "_".join(part for part in (zone, "triangularity_of_" + locus) if part))
    for locus, zone in product(("plasma_boundary", "flux_surface"), ("", *load_zones()))
)
DENSITY_CASES = tuple(
    (
        aggregation,
        population,
        "_".join(
            part for part in (aggregation, population, "electron_density") if part
        ),
    )
    for aggregation, population in product(
        ("", *sorted(load_aggregations())),
        ("", *sorted(load_populations())),
    )
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        *(
            (
                name,
                {NEUTRAL_SENTENCE}
                if name
                in {
                    "neutral_temperature",
                    "cold_neutral_temperature",
                    "hot_neutral_temperature",
                }
                else set(),
            )
            for name in TEMPERATURE_NAMES
        ),
        *(
            (
                name,
                {TRIANGULARITY_SENTENCE} if zone in {"", "upper", "lower"} else set(),
            )
            for zone, name in TRIANGULARITY_CASES
        ),
        *(
            (
                name,
                {DENSITY_SENTENCE}
                if aggregation == "total" or population in {"thermal", "fast"}
                else set(),
            )
            for aggregation, population, name in DENSITY_CASES
        ),
    ],
)
def test_separating_sentences_render_once_only_on_described_names(name, expected):
    rendered = template_sentences(name)
    for sentence in SENTENCES:
        assert rendered.count(sentence) == (1 if sentence in expected else 0), name


def test_selected_openings_precede_their_notes():
    name = "total_thermal_electron_density"
    templates = select_conventions(name).templates
    assert len(templates) == 2
    assert [template.note for template in templates] == [
        DENSITY_SENTENCE,
        DENSITY_SENTENCE,
    ]
    assert template_sentences(name) == (
        templates[0].documentation,
        DENSITY_SENTENCE,
        templates[1].documentation,
    )
