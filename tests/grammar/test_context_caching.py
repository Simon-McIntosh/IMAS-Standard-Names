"""get_grammar_context builds its expensive aggregate once per process.

The payload includes a full catalog scan (usage statistics); external
pipelines construct grammar-validated models in tight loops, so a rebuild
per call is prohibitive. The aggregate is cached and calls receive deep
copies, keeping caller-side mutation away from the shared cache.
"""

import time

from imas_standard_names.grammar.context import get_grammar_context


def test_second_call_is_cheap():
    get_grammar_context()  # warm (may pay the catalog scan)
    start = time.perf_counter()
    get_grammar_context()
    assert time.perf_counter() - start < 1.0


def test_calls_return_equal_but_independent_payloads():
    first = get_grammar_context()
    second = get_grammar_context()
    assert first == second
    assert first is not second

    first["naming_guidance"] = "mutated"
    first["applicability"]["include"].append("mutated")
    fresh = get_grammar_context()
    assert fresh["naming_guidance"] != "mutated"
    assert "mutated" not in fresh["applicability"]["include"]
