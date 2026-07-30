"""Keep parseable documentation examples aligned with the public grammar."""

import re
from pathlib import Path

import yaml

from imas_standard_names.grammar.context import get_grammar_context
from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)

ROOT = Path(__file__).resolve().parents[2]
AUTHORING_DOCS = (
    ROOT / "docs" / "development" / "style-guide.md",
    ROOT / "docs" / "development" / "specification.md",
    ROOT / "docs" / "development" / "quickstart.md",
    ROOT / "docs" / "grammar-reference.md",
)
EQUILIBRIUM_EXAMPLES = (
    ROOT
    / "imas_standard_names"
    / "resources"
    / "standard_name_examples"
    / "equilibrium.yml"
)
AUTHORING_EXAMPLE_START = "<!-- isn-authoring-examples:start -->"
AUTHORING_EXAMPLE_END = "<!-- isn-authoring-examples:end -->"
AUTHORING_EXAMPLE_BLOCK = re.compile(
    rf"{re.escape(AUTHORING_EXAMPLE_START)}(.*?){re.escape(AUTHORING_EXAMPLE_END)}",
    re.DOTALL,
)
FENCED_BLOCK = re.compile(
    r"```(?P<language>text|yaml)\s*(?P<body>.*?)\s*```", re.DOTALL
)
BACKTICK_NAME = re.compile(r"`([a-z][a-z0-9_]*)`")


def _compatibility_only_fields() -> set[str]:
    """Derive non-authoring parse fields from the public grammar guidance."""
    anti_patterns = get_grammar_context()["anti_patterns"]
    compatibility_rule = next(
        item
        for item in anti_patterns
        if "parse compatibility only" in item["correction"]
    )
    compatibility = parse_standard_name(
        compatibility_rule["example_wrong"]
    ).model_dump()
    preferred = parse_standard_name(compatibility_rule["example_right"]).model_dump()

    fields = {
        field
        for field, value in compatibility.items()
        if value is not None and preferred[field] is None
    }
    assert fields
    return fields


def _assert_preferred_authoring(name: str, compatibility_fields: set[str]) -> None:
    parsed = parse_standard_name(name)
    assert compose_standard_name(parsed) == name
    parsed_fields = parsed.model_dump()
    assert not {
        field for field in compatibility_fields if parsed_fields[field] is not None
    }, f"{name!r} uses a compatibility-only grammar segment"


def _names_from_block(block: str) -> list[str]:
    fenced = FENCED_BLOCK.fullmatch(block.strip())
    if not fenced:
        return BACKTICK_NAME.findall(block)
    if fenced["language"] == "yaml":
        return [yaml.safe_load(fenced["body"])["name"]]
    return [line.split()[0] for line in fenced["body"].splitlines() if line.strip()]


def test_marked_authoring_examples_are_present_and_preferred() -> None:
    """Every scoped guide carries nonempty, preferred authoring examples."""
    compatibility_fields = _compatibility_only_fields()
    for path in AUTHORING_DOCS:
        text = path.read_text()
        start_count = text.count(AUTHORING_EXAMPLE_START)
        end_count = text.count(AUTHORING_EXAMPLE_END)
        blocks = AUTHORING_EXAMPLE_BLOCK.findall(text)

        assert start_count > 0, f"{path} has no authoring-example markers"
        assert start_count == end_count == len(blocks), (
            f"{path} has unpaired authoring-example markers"
        )
        for block in blocks:
            names = _names_from_block(block)
            assert names, f"{path} contains an empty authoring-example block"
            for name in names:
                _assert_preferred_authoring(name, compatibility_fields)


def test_scalar_equilibrium_examples_round_trip() -> None:
    """Quantitative resource entries use canonical standard names."""
    entries = yaml.safe_load(EQUILIBRIUM_EXAMPLES.read_text())
    scalar_names = [entry["name"] for entry in entries if entry["kind"] == "scalar"]

    assert scalar_names
    for name in scalar_names:
        parsed = parse_standard_name(name)
        assert compose_standard_name(parsed) == name
