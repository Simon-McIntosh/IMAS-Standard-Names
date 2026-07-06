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
    # top-level keys are category names. scoping_qualifiers.yml is an
    # intentional SUBSET of qualifiers.yml (the phrase-scoping binding class),
    # not a segment vocabulary. Exclude both from the uniqueness scan.
    skip = {"qualifier_categories.yml", "scoping_qualifiers.yml"}

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
    # ELIMINATED (guard now active — do not re-add):
    # - qualifiers.yml ↔ locus_registry.yml: the mis-filed loci flux_surface, inlet,
    #   outlet were removed from qualifiers.yml — they are loci (at_inlet / over_…),
    #   and prefix-form names (coolant_outlet_temperature → coolant_temperature_at_outlet)
    #   migrate to the locus form. Intersection now empty.
    #
    # ELIMINATED (guard now active — do not re-add):
    # - qualifiers.yml ↔ physical_bases.yml AND qualifiers.yml ↔
    #   generic_physical_bases.yml: the only overlapping tokens were energy and
    #   momentum (the transport-channel words). They moved to channels.yml (the
    #   dedicated `channel` segment), so both intersections are now empty.
    #
    # ELIMINATED (guard now active — do not re-add):
    # - qualifiers.yml ↔ subjects.yml: 'particle' moved to channels.yml, 'state'
    #   to its subject-compound role — intersection now empty.
    # - qualifiers.yml ↔ regions.yml: region words live in zones.yml (prefix) /
    #   regions.yml (locus), not qualifiers — intersection now empty.
    #
    # INTENTIONAL dual-role (keep):
    # - qualifiers.yml ↔ physics_domains.yml: equilibrium, mhd, nbi are genuine
    #   modifier qualifiers (mhd_mode, nbi_power) that also name a physics domain
    #   (classification tag). Same benign dual use as the physics_domains↔tags
    #   whitelist — the grammar never confuses the qualifier vs domain context.
    #
    # ELIMINATED (guard now active — do not re-add):
    # - qualifiers.yml ↔ processes.yml: the only overlapping tokens were
    #   convection and heating, compound-base words (convection_velocity,
    #   heating_power). Those compounds are now atomic physical_bases, so the
    #   tokens left qualifiers.yml and this intersection is empty. qualifiers is
    #   now disjoint from every other segment vocabulary except the documented
    #   physics_domains dual-role and the normalizing_qualifiers metadata subset.
    allowed_overlap_pairs = {
        frozenset({"qualifiers.yml", "physics_domains.yml"}),
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
        # channels.yml is the transport-channel PREFIX segment (heat, particle,
        # energy, momentum — WHAT is transported). energy and momentum serve a
        # documented DUAL role: they are also physical_bases (kinetic_energy,
        # internal_energy, angular_momentum, standalone electron_energy) and
        # energy is additionally a generic_physical_base. The parser matches the
        # longest base first, so a standalone energy/momentum resolves as the
        # base while the *_flux / *_diffusivity / *_source compounds strip the
        # channel. Both forms coexist by design (see channels.yml header and the
        # canonical-qualifier-order plan).
        frozenset({"channels.yml", "physical_bases.yml"}),
        frozenset({"channels.yml", "generic_physical_bases.yml"}),
        # qualifiers.yml ↔ subjects.yml: the fusion reactant pairs
        # (deuterium_tritium, deuterium_deuterium, tritium_tritium) are a
        # DOCUMENTED dual-role — subject as the effective fuel species
        # (deuterium_tritium_density) and reaction-channel qualifier when a
        # product subject follows (deuterium_tritium_neutron_flux). The
        # token-level ratchet is enforced in test_vocabulary_gates.py
        # (_DOCUMENTED_ALSO_SUBJECT) — only these three pairs are permitted.
        frozenset({"qualifiers.yml", "subjects.yml"}),
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


def test_scoping_qualifiers_subset_of_qualifiers():
    """scoping_qualifiers.yml is a binding-class SUBSET of qualifiers.yml.

    A scoping token that is not a registered qualifier would never reach the
    qualifier segment (the parser only strips registered qualifiers), so the
    entry would be silently dead. Guard the subset relation.
    """
    from imas_standard_names.grammar.vocab_loaders import (
        load_qualifiers,
        load_scoping_qualifiers,
    )

    scoping = load_scoping_qualifiers()
    qualifiers = load_qualifiers()
    assert scoping, "scoping_qualifiers.yml must not be empty"
    stray = scoping - qualifiers
    assert not stray, (
        f"scoping_qualifiers.yml lists tokens not registered in "
        f"qualifiers.yml: {sorted(stray)}"
    )
