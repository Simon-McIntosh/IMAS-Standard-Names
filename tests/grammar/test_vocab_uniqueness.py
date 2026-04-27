"""Cross-segment vocabulary uniqueness lint (W40 task).

Ensures tokens are unique across vocabulary files, with one whitelisted
exception: physics_domains and tags intentionally share all domain tokens
(e.g. 'equilibrium', 'magnetics') because domain tags are used for both
classification and filtering.

Rationale:
  Token collisions across segments create ambiguity in grammar parsing and
  semantic interpretation. A token should map to exactly one vocabulary
  segment, except for the physics_domains ↔ tags whitelist.

  As of W40 graph harvest, one real collision exists:
    - 'current_drive' appears in both physical_bases.yml and physics_domains.yml

  This test will fail on that collision until resolved (see ISN issue).

Whitelist:
  physics_domains.yml ↔ tags.yml collisions are ALLOWED because:
    1. All physics domains are also valid tags for standard name metadata
    2. The grammar never confuses the two contexts (domain classification
       vs. tag filtering)
    3. Maintaining two separate lists would create sync drift

"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def load_vocab_tokens() -> dict[str, set[str]]:
    """Load all tokens from vocabulary YAML files.

    Returns:
        dict mapping vocab filename to set of tokens in that vocab.
    """
    vocab_dir = (
        Path(__file__).parents[2] / "imas_standard_names" / "grammar" / "vocabularies"
    )
    vocab_tokens = {}

    for yml_file in sorted(vocab_dir.glob("*.yml")):
        with open(yml_file) as f:
            data = yaml.safe_load(f)

        # Extract tokens based on vocab structure
        tokens = set()
        if isinstance(data, dict):
            # Most vocabs have a top-level key containing the items dict
            for top_key in data.keys():
                if isinstance(data[top_key], dict):
                    tokens.update(data[top_key].keys())

        vocab_tokens[yml_file.name] = tokens

    return vocab_tokens


def compute_collisions(vocab_tokens: dict[str, set[str]]) -> dict[str, set[str]]:
    """Compute cross-file token collisions.

    Returns:
        dict mapping token to set of vocab filenames where it appears.
        Only includes tokens that appear in 2+ files.
    """
    from collections import defaultdict

    token_sources = defaultdict(set)
    for vocab_name, tokens in vocab_tokens.items():
        for token in tokens:
            token_sources[token].add(vocab_name)

    return {tok: sources for tok, sources in token_sources.items() if len(sources) > 1}


def test_vocab_cross_segment_uniqueness():
    """Tokens must be unique across vocabulary files, except whitelisted pairs.

    WHITELIST: physics_domains.yml ↔ tags.yml (all physics domains are tags).

    This test will FAIL on the known 'current_drive' collision until resolved.
    """
    vocab_tokens = load_vocab_tokens()
    collisions = compute_collisions(vocab_tokens)

    # Whitelist: physics_domains ↔ tags collisions are allowed
    whitelist_pair = {"physics_domains.yml", "tags.yml"}
    non_whitelisted = {
        tok: sources for tok, sources in collisions.items() if sources != whitelist_pair
    }

    # Format error message
    if non_whitelisted:
        lines = [
            "Cross-segment token collisions detected (not whitelisted):",
            "",
        ]
        for token in sorted(non_whitelisted.keys()):
            sources = non_whitelisted[token]
            lines.append(f"  '{token}' in: {', '.join(sorted(sources))}")

        lines.append("")
        lines.append("Whitelist: physics_domains.yml ↔ tags.yml (intentional)")
        lines.append("All other collisions are errors and must be resolved.")

        pytest.fail("\n".join(lines))


def test_physics_domains_tags_whitelist_is_complete():
    """Verify the whitelist accounts for ALL physics_domains ↔ tags collisions.

    If this test fails, the whitelist in test_vocab_cross_segment_uniqueness
    may need adjustment.
    """
    vocab_tokens = load_vocab_tokens()
    collisions = compute_collisions(vocab_tokens)

    whitelist_pair = {"physics_domains.yml", "tags.yml"}
    whitelist_collisions = [
        tok for tok, src in collisions.items() if src == whitelist_pair
    ]

    # This test documents how many tokens are in the whitelist
    assert len(whitelist_collisions) >= 25, (
        f"Expected at least 25 physics_domains ↔ tags collisions, "
        f"found {len(whitelist_collisions)}"
    )


def test_no_empty_vocabularies():
    """All vocabulary files should contain at least one token.

    Empty vocab files may indicate missing data or incorrect YAML structure.
    Some stub vocabularies (e.g., binary_operators, subjects) are expected
    to be empty until populated in future work.
    """
    vocab_tokens = load_vocab_tokens()

    # Expected stub vocabularies (W40: not yet populated)
    expected_stubs = {
        "binary_operators.yml",
        "components.yml",
        "generic_physical_bases.yml",
        "processes.yml",
        "regions.yml",
        "subjects.yml",
    }

    empty = [name for name, tokens in vocab_tokens.items() if not tokens]
    unexpected_empty = set(empty) - expected_stubs

    if unexpected_empty:
        pytest.fail(
            f"Unexpectedly empty vocabulary files: {', '.join(sorted(unexpected_empty))}\n"
            f"Check YAML structure or populate with seed entries.\n"
            f"Known stubs: {', '.join(sorted(expected_stubs))}"
        )
