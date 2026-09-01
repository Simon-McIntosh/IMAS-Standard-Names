"""Every concrete example the grammar context advertises must parse.

``get_grammar_context()`` is the single ISN -> codex contract point: LLM
pipelines learn composition patterns from these examples, so an example
that fails to parse actively trains downstream generators to emit
invalid names.
"""

from imas_standard_names.grammar.context import get_grammar_context
from imas_standard_names.grammar.model import parse_standard_name


def _collect_examples(context: dict) -> list[tuple[str, str]]:
    """Collect (slot, name) pairs for every advertised-valid example."""
    examples: list[tuple[str, str]] = []
    for entry in context["anti_patterns"]:
        examples.append(("anti_patterns.example_right", entry["example_right"]))
    for entry in context["common_patterns"]:
        examples.append((f"common_patterns.{entry['pattern']}", entry["example"]))
    for base, requirements in context["base_requirements"].items():
        if isinstance(requirements, dict) and "example" in requirements:
            examples.append((f"base_requirements.{base}", requirements["example"]))
    return examples


def test_context_exposes_examples():
    examples = _collect_examples(get_grammar_context())
    assert len(examples) >= 10


def test_advertised_examples_parse():
    failures = []
    for slot, name in _collect_examples(get_grammar_context()):
        try:
            parse_standard_name(name)
        except Exception as exc:
            failures.append(f"{slot}: {name!r} -> {type(exc).__name__}: {exc}")
    assert not failures, "advertised examples must parse:\n" + "\n".join(failures)


def test_retired_component_long_form_stays_retired():
    """The long projection spelling must not silently come back."""
    templates = get_grammar_context()["grammar"]["canonical_templates"]
    assert templates["projection_component"] == "<axis>_<base>"
    try:
        parse_standard_name("radial_component_of_magnetic_field")
    except Exception:
        return
    raise AssertionError(
        "retired long form parsed; update canonical_templates and anti_patterns"
    )
