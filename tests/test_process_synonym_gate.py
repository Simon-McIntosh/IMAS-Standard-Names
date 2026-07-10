"""Curation gate for the processes vocabulary.

The processes vocabulary follows a canonical-token policy: each physical
mechanism has exactly ONE process token. Reworded synonyms of an existing
mechanism were merged to their canonical token. This gate blocks a rotation
harvest (or a manual edit) from silently reintroducing a merged synonym: if
any retired synonym reappears as a ``Process`` token, these tests fail.

The retired-synonym -> canonical map below is the authoritative record of the
merge. When a synonym is legitimately promoted to a distinct mechanism in the
future, remove it from this map in the same change that adds it to
``processes.yml`` (and document why it is physically distinct).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from imas_standard_names.grammar.model_types import Process

_PROCESSES_YML = (
    Path(__file__).resolve().parents[1]
    / "imas_standard_names"
    / "grammar"
    / "vocabularies"
    / "processes.yml"
)

# Retired synonym -> canonical process token. Each key was a reworded synonym
# of the value and has been merged into it.
RETIRED_PROCESS_SYNONYMS: dict[str, str] = {
    "thermalization_of_fast_particles": "thermalization",
    "fast_particle_thermalization": "thermalization",
    "coulomb_collisions": "collisions",
    "radiation_emission": "radiation",
    "recombination_emission": "radiation",
    "disruption_event": "disruption",
    "viscous": "viscosity",
}


def _process_tokens() -> set[str]:
    """The live process vocabulary, read straight from processes.yml.

    Reading the raw YAML (rather than the generated enum) catches a
    reintroduced synonym the moment it lands in the vocabulary file, before
    any code regeneration.
    """
    data = yaml.safe_load(_PROCESSES_YML.read_text(encoding="utf-8"))
    return {token for token in data if isinstance(token, str)}


class TestProcessSynonymGate:
    def test_canonical_tokens_present(self):
        """Every canonical target of a merge must exist in the vocabulary."""
        tokens = _process_tokens()
        missing = {
            canonical
            for canonical in RETIRED_PROCESS_SYNONYMS.values()
            if canonical not in tokens
        }
        assert not missing, f"canonical process tokens missing from vocabulary: {missing}"

    @pytest.mark.parametrize("synonym", sorted(RETIRED_PROCESS_SYNONYMS))
    def test_retired_synonym_absent_from_vocabulary(self, synonym):
        """A merged synonym must not reappear in processes.yml."""
        canonical = RETIRED_PROCESS_SYNONYMS[synonym]
        assert synonym not in _process_tokens(), (
            f"retired process synonym '{synonym}' reappeared in the vocabulary; "
            f"it was merged into '{canonical}'. Do not reintroduce it — use the "
            f"canonical token (see processes.yml canonical-token policy)."
        )

    @pytest.mark.parametrize("synonym", sorted(RETIRED_PROCESS_SYNONYMS))
    def test_retired_synonym_not_an_enum_member(self, synonym):
        """The generated Process enum must not carry a merged synonym."""
        assert synonym not in {member.value for member in Process}, (
            f"retired process synonym '{synonym}' is a Process enum member; "
            f"regenerate grammar types after removing it from processes.yml."
        )
