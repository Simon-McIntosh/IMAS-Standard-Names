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

    # qualifier_categories.yml is a token→category MAP, not a token-defining
    # vocabulary: it intentionally re-lists qualifiers.yml tokens and its
    # top-level keys are category names. Exclude it from the uniqueness scan.
    skip = {"qualifier_categories.yml"}

    for yml_file in sorted(vocab_dir.glob("*.yml")):
        if yml_file.name in skip:
            continue
        with open(yml_file) as f:
            data = yaml.safe_load(f)

        # Extract tokens based on vocab structure
        tokens = set()
        if isinstance(data, list):
            # Flat list format (e.g., qualifiers.yml, processes.yml)
            tokens.update(str(item) for item in data if item)
        elif isinstance(data, dict):
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
    """Tokens must be unique across vocabulary files, with allowed exceptions.

    Qualifiers intentionally overlap with subjects (parser unions them)
    and some tokens legitimately serve dual roles across segments.
    """
    vocab_tokens = load_vocab_tokens()
    collisions = compute_collisions(vocab_tokens)

    # Allowed cross-segment overlaps (documented dual-role tokens).
    #
    # RATCHET: this allowlist shrinks toward empty as the canonical-qualifier-order
    # grammar redesign resolves mis-files. A token belongs to exactly one segment
    # role; every entry here is either intentional (documented) or a tracked
    # §3-review target to be eliminated. Do NOT add entries to silence a new
    # mis-file — fix the vocab instead.
    #
    # ELIMINATED (guard now active — do not re-add):
    # - qualifiers.yml ↔ operators.yml: the 8 double-registered operator tokens
    #   (normalized, perturbed, volume_averaged, …) were removed from qualifiers.yml;
    #   this intersection is now empty and the guard prevents its re-introduction.
    #
    # Intentional (keep):
    # - components.yml ↔ coordinate_axes.yml: shared directional vocab by design
    # - generic_physical_bases.yml ↔ physical_bases.yml: subset relationship
    # - zones.yml ↔ regions.yml / locus_registry.yml: zone PREFIX vs locus POSTFIX
    #
    # §3-review targets (still allowed, to be ratcheted out as each is resolved):
    # - qualifiers.yml ↔ {physical_bases, subjects, processes, physics_domains,
    #   locus_registry, generic_physical_bases}.yml
    allowed_overlap_pairs = {
        frozenset({"qualifiers.yml", "subjects.yml"}),
        frozenset({"qualifiers.yml", "processes.yml"}),
        frozenset({"qualifiers.yml", "regions.yml"}),
        frozenset({"qualifiers.yml", "locus_registry.yml"}),
        frozenset({"qualifiers.yml", "physics_domains.yml"}),
        frozenset({"qualifiers.yml", "physical_bases.yml"}),
        frozenset({"qualifiers.yml", "generic_physical_bases.yml"}),
        frozenset({"components.yml", "coordinate_axes.yml"}),
        frozenset({"generic_physical_bases.yml", "physical_bases.yml"}),
        frozenset({"processes.yml", "subjects.yml"}),
        frozenset({"locus_registry.yml", "regions.yml"}),
        frozenset({"locus_registry.yml", "subjects.yml"}),
        frozenset({"locus_registry.yml", "processes.yml"}),
        frozenset({"physics_domains.yml", "processes.yml"}),
        # normalizing_qualifiers.yml is a metadata subset — tokens there
        # intentionally appear in other segment vocabs (subjects, qualifiers)
        frozenset({"normalizing_qualifiers.yml", "subjects.yml"}),
        frozenset({"normalizing_qualifiers.yml", "qualifiers.yml"}),
        # zones.yml is the ordered plasma-region / geometric sub-selector PREFIX
        # segment. Its tokens legitimately serve dual roles:
        #  - zones.yml ↔ regions.yml / locus_registry.yml: the same region word
        #    is both a prefix zone (scrape_off_layer_density) and a postfix
        #    locus (over_scrape_off_layer / at_pedestal). Both forms coexist by
        #    design (see zones.yml header and the canonical-qualifier-order plan).
        frozenset({"zones.yml", "regions.yml"}),
        frozenset({"zones.yml", "locus_registry.yml"}),
    }

    # Filter out allowed overlaps
    real_collisions = {}
    for token, sources in collisions.items():
        # Check if ALL pairs in this collision set are allowed
        pairs = [frozenset({a, b}) for a in sources for b in sources if a < b]
        if not all(p in allowed_overlap_pairs for p in pairs):
            real_collisions[token] = sources

    # Format error message
    if real_collisions:
        lines = [
            "Cross-segment token collisions detected:",
            "",
        ]
        for token in sorted(real_collisions.keys()):
            sources = real_collisions[token]
            lines.append(f"  '{token}' in: {', '.join(sorted(sources))}")

        lines.append("")
        lines.append("All collisions are errors and must be resolved.")

        pytest.fail("\n".join(lines))


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
