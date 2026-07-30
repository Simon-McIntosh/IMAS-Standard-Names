"""Keep parseable documentation examples aligned with the public grammar."""

import re
from pathlib import Path

import yaml

from imas_standard_names.grammar.model import (
    compose_standard_name,
    parse_standard_name,
)

ROOT = Path(__file__).resolve().parents[2]
STYLE_GUIDE = ROOT / "docs" / "development" / "style-guide.md"
EQUILIBRIUM_EXAMPLES = (
    ROOT
    / "imas_standard_names"
    / "resources"
    / "standard_name_examples"
    / "equilibrium.yml"
)
PARSE_EXAMPLE_BLOCK = re.compile(
    r"<!-- isn-parse-examples:start -->\s*```text\s*(.*?)\s*```\s*"
    r"<!-- isn-parse-examples:end -->",
    re.DOTALL,
)


def _assert_round_trip(name: str) -> None:
    parsed = parse_standard_name(name)
    assert compose_standard_name(parsed) == name


def test_marked_style_guide_examples_round_trip() -> None:
    """Every explicitly marked positive example is canonical."""
    text = STYLE_GUIDE.read_text()
    blocks = PARSE_EXAMPLE_BLOCK.findall(text)

    assert blocks
    for block in blocks:
        for name in block.splitlines():
            _assert_round_trip(name.strip())


def test_scalar_equilibrium_examples_round_trip() -> None:
    """Quantitative resource entries use canonical standard names."""
    entries = yaml.safe_load(EQUILIBRIUM_EXAMPLES.read_text())
    scalar_names = [entry["name"] for entry in entries if entry["kind"] == "scalar"]

    assert scalar_names
    for name in scalar_names:
        _assert_round_trip(name)
