# State-Resolution Convention Rework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fused `ion_state`/`ion_charge_state`/`neutral_state` compound subject tokens with a first-class `state` grammar segment (`charge_state`/`internal_state`), then migrate the ~241 affected catalog names.

**Architecture:** Add a single-token closed `state` segment positioned immediately after `subject` in the grammar's segment order. The grammar is authored in `specification.yml` (segments + `!include` vocab files) and code-generated into `model_types.py` + `constants.py`; `model.py` carries the pydantic `StandardName` field, IR field, and parse/compose wiring per segment. Grammar changes land and test independently (Phases A–D) before any catalog rename (Phase E), which runs through the codex pipeline edit path under operator supervision.

**Tech Stack:** Python 3.12, Pydantic, pytest, PyYAML, hatch (codegen build hook); imas-codex `sn` CLI + Neo4j for migration.

## Global Constraints

- The parser uses **greedy longest-prefix** matching; before/after any token change, every existing catalog name must still `parse_standard_name` → `compose_standard_name` round-trip identically. Live catalog: `/home/ITER/mcintos/Code/imas-standard-names-catalog/standard_names/*.yml` (read-only).
- **Vocabulary edits + regenerated modules (`model_types.py`, `constants.py`) MUST land in the same commit** — a drift gate (`tests/test_codegen_drift.py`) enforces this.
- `parse_standard_name` is the single validity oracle; canonical one-spelling-per-name is enforced (`NonCanonicalNameError`).
- Regenerate modules via the codegen entrypoint; never hand-edit `model_types.py`/`constants.py`.
- Neutral state token is **`internal_state`** (never `excited_state` — DD state includes the ground state). Ion token is **`charge_state`**. Closed vocabulary, single-token, no `metastable_state`.
- No AI co-authorship trailers on commits. Conventional-commit messages, explicit path staging, commit + push per coherent change on `main`.
- Production graph writes (Phase E) run only in a lead-supervised window via the `sn` CLI; dry-run preview before every batch.

---

## File Structure

**imas-standard-names (grammar):**
- Create: `imas_standard_names/grammar/vocabularies/states.yml` — the two state tokens + comments (the segment's vocabulary).
- Modify: `imas_standard_names/grammar/specification.yml` — declare the `state` segment after `subject`.
- Modify: `imas_standard_names/grammar/vocabularies/subjects.yml` — delete `ion_state`, `ion_charge_state`, `neutral_state`, bare `state`.
- Regenerated: `imas_standard_names/grammar/model_types.py`, `imas_standard_names/grammar/constants.py` (State enum, SEGMENT_ORDER, SEGMENT_TOKEN_MAP, SEGMENT_RULES, BASE_SEGMENT_INDICES).
- Modify: `imas_standard_names/grammar/model.py` — `StandardName.state` field, IR field, single-token parse branch + compose emission (mirror `population`/`orbit`).
- Modify: `imas_standard_names/grammar/ir.py` — IR carries the state token (if IR is separate from model).
- Modify: `imas_standard_names/validation/semantic.py` — state-requires-subject + species/state compatibility gate.
- Test: `tests/grammar/test_state_segment.py`, `tests/grammar/test_state_compatibility_gate.py`, `tests/test_validation_checks.py` (extend).

**imas-codex (composer + migration):**
- Modify: the SPA/MCP grammar composer payload path (`imas_codex/standard_names/grammar_query.py` / `tools`) — surface the `state` segment.
- Migration scripts staged under `/home/ITER/mcintos/.local/share/imas-codex/state-migration/` (not committed).

---

## Phase A — Grammar segment

### Task A1: Add the `states.yml` vocabulary file

**Files:**
- Create: `imas_standard_names/grammar/vocabularies/states.yml`

**Interfaces:**
- Produces: a YAML list of two tokens `charge_state`, `internal_state`, loaded by the codegen `!include` in `specification.yml` (Task A2) as the `states` vocabulary.

- [ ] **Step 1: Write the vocabulary file**

```yaml
# State-resolution vocabulary
#
# The `state` segment resolves a quantity for a specific state of a species,
# rather than the species aggregate. It refines the subject (the DD nests
# ion[]/state[]/... and neutral[]/state[]/... inside the species) and is a
# single-token closed segment rendered immediately AFTER the subject:
#   <population>_<subject>_<state>_<channel>_<base>
#
# Tokens name the resolved axis (self-describing):
#   - charge_state:   ionization (charge) state of an ion; may be a bundled
#                     z-range (DD z_min/z_max "Ion Charge State Bundles").
#                     Valid on ion-like subjects only.
#   - internal_state: internal degrees of freedom of a neutral (electronic,
#                     vibrational, rotational) — covers ground, excited,
#                     metastable. NOT "excited_state" (ground is a state too).
#                     Valid on neutral-like subjects only.
#
# Metastable/excited are VALUES on the internal-state axis, not tokens here.
- charge_state
- internal_state
```

- [ ] **Step 2: Verify it loads as YAML**

Run: `cd /home/ITER/mcintos/Code/imas-standard-names && uv run python -c "import yaml; print(yaml.safe_load(open('imas_standard_names/grammar/vocabularies/states.yml')))"`
Expected: `['charge_state', 'internal_state']`

- [ ] **Step 3: Commit** (with Task A2 — the vocab file alone doesn't wire in; combine the commit at A3 after regen so the drift gate stays green.)

### Task A2: Declare the `state` segment in `specification.yml`

**Files:**
- Modify: `imas_standard_names/grammar/specification.yml` (segment list, after the `subject` segment, before `device`/`objects`)

**Interfaces:**
- Consumes: the `states` vocabulary (Task A1).
- Produces: a `state` segment declaration the codegen reads to emit the `State` enum + SEGMENT_ORDER/RULES entries.

- [ ] **Step 1: Add the segment declaration** immediately after the `- id: subject` block. Match the existing block shape (id / optional / vocabulary / description); mirror the `population` block since `state` is also single-token:

```yaml
  - id: state
    optional: true
    vocabulary: states
    description: >
      State resolution: a quantity resolved for a specific state of the
      species rather than the species aggregate. Single-token closed segment,
      an orthogonal subject-refinement axis (like population), but rendered
      IMMEDIATELY AFTER the subject because it binds tighter — the DD nests
      ion[]/state[]/... and neutral[]/state[]/... inside the species:
      <population>_<subject>_<state>_<channel>_<base>
      (e.g. fast_ion_charge_state_pressure, neutral_internal_state_density).
      charge_state is valid on ion-like subjects, internal_state on
      neutral-like subjects (see the compatibility gate).
```

- [ ] **Step 2: Confirm the spec parses**

Run: `uv run python -c "from imas_standard_names.grammar_codegen.spec import GrammarSpec; s=GrammarSpec.load(); print([seg.identifier for seg in s.segments])"`
Expected: the printed list includes `state` positioned between `subject` and `device`.

### Task A3: Regenerate modules and confirm the `State` enum + segment order

**Files:**
- Regenerated: `imas_standard_names/grammar/model_types.py`, `imas_standard_names/grammar/constants.py`

**Interfaces:**
- Produces: `State` StrEnum (`CHARGE_STATE="charge_state"`, `INTERNAL_STATE="internal_state"`); `SEGMENT_ORDER` with `"state"` after `"subject"`; `SEGMENT_TOKEN_MAP["state"]`; a `SegmentRule(identifier="state", optional=True, …)`; `BASE_SEGMENT_INDICES` shifted (11,12)→(12,13).

- [ ] **Step 1: Run the codegen**

Run: `uv run python -m imas_standard_names.grammar_codegen.generate`
Expected: "Updated grammar/model_types.py" / "Updated grammar/constants.py" (or "already up to date" if a prior run generated them).

- [ ] **Step 2: Verify the generated artifacts**

Run:
```bash
uv run python -c "
from imas_standard_names.grammar.model_types import State
from imas_standard_names.grammar.constants import SEGMENT_ORDER, SEGMENT_TOKEN_MAP, BASE_SEGMENT_INDICES
print('State:', [m.value for m in State])
print('order:', SEGMENT_ORDER[SEGMENT_ORDER.index('subject'):SEGMENT_ORDER.index('subject')+3])
print('tokens:', SEGMENT_TOKEN_MAP['state'])
print('base_idx:', BASE_SEGMENT_INDICES)
"
```
Expected: `State: ['charge_state', 'internal_state']`; `order: ('subject', 'state', 'device')`; `tokens: ('charge_state', 'internal_state')`; `base_idx` shifted by 1 (physical_base still points at the physical_base slot).

- [ ] **Step 3: Commit vocab + spec + regenerated modules together** (drift gate requirement)

```bash
git add imas_standard_names/grammar/vocabularies/states.yml imas_standard_names/grammar/specification.yml imas_standard_names/grammar/model_types.py imas_standard_names/grammar/constants.py
git commit -m "feat(grammar): add state segment (charge_state/internal_state) after subject"
git log -1 --format=%B | grep -Eqi "^co-authored-by:" && echo AMEND || true
git pull --no-rebase origin main && git push origin main
```

### Task A4: Wire the `state` field into the StandardName model + IR

**Files:**
- Modify: `imas_standard_names/grammar/model.py` (`StandardName` model field ~line 991-993; `_model_to_ir`/`_ir_to_model_dict`; IR dataclass fields)
- Modify: `imas_standard_names/grammar/ir.py` (if the IR type is defined there)
- Test: `tests/grammar/test_state_segment.py`

**Interfaces:**
- Consumes: `State` enum (Task A3).
- Produces: `StandardName.state: State | None = None`; IR carries `state`; parse populates it; compose emits it after the subject.

- [ ] **Step 1: Write the failing test**

```python
# tests/grammar/test_state_segment.py
import pytest
from imas_standard_names.grammar.model import parse_standard_name, compose_standard_name

ROUND_TRIP = [
    "ion_charge_state_density",
    "neutral_internal_state_density",
    "fast_ion_charge_state_pressure",
    "total_ion_charge_state_density",
    "parallel_neutral_internal_state_momentum_flux",
]

@pytest.mark.parametrize("name", ROUND_TRIP)
def test_state_names_round_trip(name):
    parsed = parse_standard_name(name)
    assert compose_standard_name(parsed) == name

def test_state_segment_populated():
    p = parse_standard_name("ion_charge_state_density")
    assert p.subject.value == "ion"
    assert p.state.value == "charge_state"
    assert p.physical_base == "density"

def test_state_renders_after_subject():
    # population + subject + state order
    p = parse_standard_name("fast_ion_charge_state_pressure")
    assert p.population.value == "fast"
    assert p.subject.value == "ion"
    assert p.state.value == "charge_state"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/grammar/test_state_segment.py -x -q`
Expected: FAIL (no `state` attribute / names don't parse).

- [ ] **Step 3: Add the model field**

In `model.py`, in the `StandardName` model (near `subject: Subject | None = None`, ~line 993), add:

```python
    state: State | None = None
```

Add `State` to the `model_types` import at the top of `model.py`.

- [ ] **Step 4: Wire parse + compose + IR**

Mirror the single-token `population`/`orbit` handling:
- In the parse loop (~model.py:470-532) add a `state` single-token branch: after the subject is matched, attempt to match a `state` token at the next slot; assign `state = matched` (reuse the same "admits at most one token" guard pattern as population, model.py:512). The token match uses `SEGMENT_TOKEN_MAP["state"]`.
- In the IR dataclass (ir.py or the IR region of model.py) add a `state` field alongside `population`/`subject`.
- In `_model_to_ir` / `_ir_to_model_dict` map the `state` field through.
- In the compose path (`compose_standard_name` / `_compose_ir`, ~model.py:886-924) emit the state token immediately after the subject and before the channel/base, in the prefix-assembly sequence.

(Follow the exact pattern the `subject`/`population` tokens already use in each of these four spots — do not invent a new mechanism.)

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/grammar/test_state_segment.py -q`
Expected: PASS (all 5 round-trips + 3 assertions).

- [ ] **Step 6: Run the full grammar suite (no regression)**

Run: `uv run pytest tests/grammar/ -q -p no:cacheprovider`
Expected: PASS (0 failed). Note: the NEW names above do not yet exist in the catalog; the compound `ion_state`/`neutral_state` names STILL round-trip at this point because the fused subject tokens are not deleted until Task C1 — that is expected and desired (no coexistence break yet).

- [ ] **Step 7: Commit**

```bash
git add imas_standard_names/grammar/model.py imas_standard_names/grammar/ir.py tests/grammar/test_state_segment.py
git commit -m "feat(grammar): parse/compose the state segment on the StandardName model"
git pull --no-rebase origin main && git push origin main
```

## Phase B — Validation gates

### Task B1: state-requires-subject gate

**Files:**
- Modify: `imas_standard_names/grammar/model.py` (parse-time gate, mirror the flux-surface reduction gate `_check_flux_surface_reduction_gate` wiring in `parse_standard_name`/`compose_standard_name`)
- Test: `tests/grammar/test_state_compatibility_gate.py`

**Interfaces:**
- Produces: `_check_state_requires_subject(ir)` raising `ValueError` when a state token is present without a species subject.

- [ ] **Step 1: Write the failing test**

```python
# tests/grammar/test_state_compatibility_gate.py
import pytest
from imas_standard_names.grammar.model import parse_standard_name, compose_standard_name

def test_state_without_subject_rejected():
    with pytest.raises(ValueError, match="state.*requires.*subject"):
        # charge_state as a bare base-adjacent token with no species subject
        compose_standard_name({"state": "charge_state", "physical_base": "density"})

def test_state_with_subject_ok():
    p = parse_standard_name("ion_charge_state_density")
    assert compose_standard_name(p) == "ion_charge_state_density"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/grammar/test_state_compatibility_gate.py::test_state_without_subject_rejected -q`
Expected: FAIL (no error raised).

- [ ] **Step 3: Implement the gate**

In `model.py`, add:

```python
def _check_state_requires_subject(ir) -> None:
    """A state token resolves a species sub-population; it is meaningless
    without a species subject."""
    if getattr(ir, "state", None) is not None and getattr(ir, "subject", None) is None:
        raise ValueError(
            f"state '{ir.state}' requires a species subject — state resolves "
            "a specific state OF a species (e.g. ion_charge_state_density); "
            "a bare state token has no referent"
        )
```

Call it in both `parse_standard_name` and `compose_standard_name` alongside `_check_flux_surface_reduction_gate` / `_check_extremum_infix_gate`.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/grammar/test_state_compatibility_gate.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add imas_standard_names/grammar/model.py tests/grammar/test_state_compatibility_gate.py
git commit -m "feat(grammar): gate state segment to require a species subject"
git pull --no-rebase origin main && git push origin main
```

### Task B2: species/state compatibility map

**Files:**
- Modify: `imas_standard_names/grammar/model.py` (extend the gate) OR `imas_standard_names/validation/semantic.py` (semantic check) — put it in the parse gate so invalid combinations never parse.
- Test: `tests/grammar/test_state_compatibility_gate.py` (extend)

**Interfaces:**
- Produces: a compatibility table `charge_state → {ion, impurity_ion, <element/isotope species>}`, `internal_state → {neutral, <neutral species>}`; `ion + internal_state` allowed (future molecular ions); rejects e.g. `electron_charge_state` and `ion_internal_state` unless in the map.

- [ ] **Step 1: Write the failing test**

```python
def test_charge_state_on_neutral_rejected():
    with pytest.raises(ValueError, match="charge_state.*ion"):
        compose_standard_name({"subject": "neutral", "state": "charge_state", "physical_base": "density"})

def test_internal_state_on_neutral_ok():
    p = parse_standard_name("neutral_internal_state_density")
    assert compose_standard_name(p) == "neutral_internal_state_density"

def test_charge_state_on_ion_ok():
    p = parse_standard_name("ion_charge_state_density")
    assert p.state.value == "charge_state"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/grammar/test_state_compatibility_gate.py::test_charge_state_on_neutral_rejected -q`
Expected: FAIL.

- [ ] **Step 3: Implement the compatibility map**

Extend the gate in `model.py`:

```python
_ION_LIKE_SUBJECTS = frozenset({"ion", "impurity_ion"})  # + element/isotope species — see note
_NEUTRAL_LIKE_SUBJECTS = frozenset({"neutral"})
_STATE_COMPAT = {
    "charge_state": _ION_LIKE_SUBJECTS,          # ions carry charge states
    "internal_state": _NEUTRAL_LIKE_SUBJECTS | _ION_LIKE_SUBJECTS,  # neutrals; ions allowed (molecular ions, future)
}

def _check_state_subject_compat(ir) -> None:
    st = getattr(ir, "state", None)
    subj = getattr(ir, "subject", None)
    if st is None:
        return
    allowed = _STATE_COMPAT.get(str(st), frozenset())
    # element/isotope species subjects (argon, tungsten, deuterium, ...) count
    # as ion-like for charge_state; treat any species subject in the element
    # vocabulary as ion-like. Determine element membership from the subjects
    # vocabulary grouping (see subjects.yml element section).
    if str(subj) not in allowed and not _is_element_species(str(subj)):
        raise ValueError(
            f"state '{st}' is not valid on subject '{subj}': charge_state "
            "applies to ions/elements, internal_state to neutrals"
        )
```

Implement `_is_element_species` by reading the element/isotope group from the subjects vocabulary (the `# === Fusion fuel + isotopes ===` / element section of `subjects.yml`) so `argon_charge_state_density` etc. validate. Fold the state-requires-subject check (B1) and this compat check into one `_check_state_gate(ir)` called from parse + compose.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/grammar/test_state_compatibility_gate.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add imas_standard_names/grammar/model.py tests/grammar/test_state_compatibility_gate.py
git commit -m "feat(grammar): species/state compatibility gate (charge_state=ion, internal_state=neutral)"
git pull --no-rebase origin main && git push origin main
```

## Phase C — Atomic subject-token surgery

### Task C1: Delete the fused subject tokens + regenerate (same commit)

**Files:**
- Modify: `imas_standard_names/grammar/vocabularies/subjects.yml` (delete `ion_state`, `ion_charge_state`, `neutral_state`, bare `state` — lines ~84-87)
- Regenerated: `model_types.py`, `constants.py`
- Test: `tests/grammar/test_state_segment.py` (extend)

**Interfaces:**
- Produces: `Subject` enum without the four fused tokens; the greedy parser now routes `ion_charge_state_*` to subject=ion + state=charge_state (one canonical parse).

- [ ] **Step 1: Verify the bare `state` subject is catalog-unused** (safety precondition)

Run:
```bash
cd /home/ITER/mcintos/Code/imas-codex && uv run --no-sync python -c "
from imas_codex.graph import GraphClient
gc=GraphClient()
r=gc.query(\"MATCH (n:StandardName) WHERE n.name_stage IN ['accepted','reviewed','drafted'] AND (n.id='state' OR n.id STARTS WITH 'state_') RETURN count(n) AS n\")
print('bare-state names:', r)
"
```
Expected: `0` (if not zero, STOP — those need migration first).

- [ ] **Step 2: Write the failing test** (new-form parse must win; old fused subject must be gone)

```python
def test_fused_subject_tokens_removed():
    from imas_standard_names.grammar.model_types import Subject
    vals = {m.value for m in Subject}
    assert "ion_state" not in vals
    assert "ion_charge_state" not in vals
    assert "neutral_state" not in vals
    assert "state" not in vals

def test_ion_charge_state_parses_via_segment():
    p = parse_standard_name("ion_charge_state_density")
    assert p.subject.value == "ion" and p.state.value == "charge_state"
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/grammar/test_state_segment.py::test_fused_subject_tokens_removed -q`
Expected: FAIL (tokens still present).

- [ ] **Step 4: Delete the four tokens from `subjects.yml`**

Remove the lines:
```yaml
- ion_state
- ion_charge_state
- neutral_state
- state
```
(and any now-stale comment referencing them as atomic ionisation-state qualifiers).

- [ ] **Step 5: Regenerate + run the drift gate**

Run:
```bash
uv run python -m imas_standard_names.grammar_codegen.generate
uv run pytest tests/test_codegen_drift.py tests/grammar/test_state_segment.py -q
```
Expected: PASS.

- [ ] **Step 6: Full-catalog round-trip guard — EXPECTED to show the migration set**

Run: the round-trip sweep over the live catalog (repository loader). The `ion_state_*`/`neutral_state_*` **old** names now FAIL to parse (the fused token is gone, the new segment form differs). Capture the exact failing set — this IS the Phase E working set. Confirm the count matches the reconciled inventory (Task E1) and that NO unrelated name regressed.

```bash
uv run python - <<'PY'
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.grammar.model import parse_standard_name, compose_standard_name
# NOTE: point at the full ISNC catalog, not the bundled test resources
import glob, yaml
names=set()
for f in glob.glob('/home/ITER/mcintos/Code/imas-standard-names-catalog/standard_names/*.yml'):
    d=yaml.safe_load(open(f))
    for e in (d or []):
        if isinstance(e, dict) and 'name' in e: names.add(e['name'])
fails=[n for n in names if _fails(n)]  # define _fails: try parse+round-trip, except -> True
print(len(fails), 'names need migration'); [print(' ', n) for n in sorted(fails)[:50]]
PY
```
Expected: only `*_state_*` old-form names fail; count ≈ the reconciled inventory. **Do not commit C1 until Phase E is ready** — deleting the tokens breaks the published catalog's round-trip until the names are migrated. Sequence: land A/B/D, prepare E's migration scripts, then land C1 + execute E in the same supervised window.

- [ ] **Step 7: Commit** (only when Phase E is staged and the supervised window is open)

```bash
git add imas_standard_names/grammar/vocabularies/subjects.yml imas_standard_names/grammar/model_types.py imas_standard_names/grammar/constants.py tests/grammar/test_state_segment.py
git commit -m "feat(grammar): remove fused state subject tokens; state segment is canonical"
git pull --no-rebase origin main && git push origin main
```

## Phase D — Codex SPA / MCP composer support

### Task D1: Surface the `state` segment in the grammar composer payload

**Files:**
- Modify: the codex grammar-context consumer that builds the SPA/MCP composer payload (`imas_codex/standard_names/grammar_query.py` and/or `imas_codex/standard_names/tools`) — it derives from ISN `get_grammar_context()`, which already exposes segments; confirm `state` flows through with its vocabulary + position.
- Test: the codex composer/grammar test module that asserts the segment set.

**Interfaces:**
- Consumes: ISN `get_grammar_context()` (now includes `state`).
- Produces: the SPA Grammar composer offers `state` as a pickable segment after `subject` with `{charge_state, internal_state}`.

- [ ] **Step 1: Bump the codex ISN pin** to the commit that lands Phase A–C, extras-preserving:

```bash
cd /home/ITER/mcintos/Code/imas-codex
sed -i 's|IMAS-Standard-Names.git@[0-9a-f]\+|IMAS-Standard-Names.git@<NEW_SHA>|g' pyproject.toml
uv sync --extra cpu --extra test --dev
```

- [ ] **Step 2: Write/extend the failing test** asserting the composer payload includes `state` with the two tokens. (Mirror the existing composer-payload test; if none asserts the segment list, add one that calls the payload builder and checks `"state"` ∈ segments and `{"charge_state","internal_state"} ⊆ tokens`.)

- [ ] **Step 3: Run to verify it fails** (pre-derivation), then confirm the derivation path already forwards new segments (the payload is derived from `get_grammar_context()` per the P5 MCP-derivation change). If it forwards automatically, the test passes after the pin bump; if a hand-maintained list exists, add `state` to it.

- [ ] **Step 4: Run the composer/grammar test module**

Run: `uv run --no-sync pytest tests/standard_names/ -k "grammar or composer" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock <composer file> <test file>
git commit -m "feat(standard-names): surface the state segment in the grammar composer"
git pull --no-rebase origin main && git push origin main
```

## Phase E — Catalog migration (supervised, production graph)

> Runs in a lead-supervised window via the `sn` CLI. Dry-run preview before every batch. Batch by family. Accepted-name renames leave P1 deprecation stubs; the pipeline re-validates each edit through the P2 gates. The rename cascade skips directional projections (parallel/poloidal/toroidal) — handle those per-name.

### Task E1: Reconcile the inventory

- [ ] **Step 1:** Enumerate the live-graph working set (all stages) and cross-check the 241 catalog figure:

```bash
cd /home/ITER/mcintos/Code/imas-codex && uv run --no-sync python - <<'PY'
from imas_codex.graph import GraphClient
gc=GraphClient()
r=gc.query("MATCH (n:StandardName) WHERE n.id CONTAINS '_state' AND n.name_stage IN ['accepted','reviewed','drafted'] RETURN n.id AS id, n.name_stage AS s, n.kind AS k ORDER BY n.id")
print(len(r),'names'); [print(x['s'], x['k'], x['id']) for x in r]
PY
```
- [ ] **Step 2:** Classify each into: ion (charge_state), neutral (internal_state candidate), collision-pair member, element-species. Save the classification table to the migration dir.

### Task E2: Resolve the collision pairs FIRST

- [ ] For each of the ~15 `ion_state_X` / `ion_charge_state_X` pairs (kinds diverge — scalar/vector abuse), decide the correct kind + projection semantics and reconcile to a SINGLE `ion_charge_state_X` name carrying scalar-vs-vector via the component/projection machinery, not the synonym. Deprecate the loser via `sn supersede <old> --into <accepted>` (the tombstone verb) or the rename cascade. Dry-run each; log before/after.

### Task E3: Neutral internal-state audit

- [ ] For each `neutral_state_*` name, inspect its source DD path. If the DD state is an energy-type classification (cold/thermal/fast/NBI), the honest target is population-resolved with NO state token (e.g. `parallel_cold_neutral_momentum_source`); reserve `internal_state` for names whose DD path genuinely resolves an internal quantum state. Produce the per-name verdict table (rename-to-internal_state vs rename-to-population vs retire). Expect the family to shrink.

### Task E4: Bulk renames by family

- [ ] Land Task C1 (token deletion) now (opens the window), then execute the ion `charge_state` renames, the neutral verdicts from E3, and the element-species additions — batched by family, dry-run first, through the `sn edit --rename` cascade (P2 gates + P1 stubs). Handle directional projections per-name. Run `sn run --only review --names-only` to clear drafted successors.

### Task E5: Verify + close

- [ ] Full-catalog round-trip green (all migrated names parse+round-trip). `validate_catalog` clean. Deprecation stubs present for accepted renames. Update the plan doc + resolve the driving followup.

---

## Self-Review

**Spec coverage:** segment (A1-A4) ✓; rendering post-subject (A2/A4) ✓; charge_state/internal_state vocab (A1) ✓; state-requires-subject gate (B1) ✓; compatibility map (B2) ✓; atomic surgery (C1) ✓; SPA composer (D1) ✓; inventory reconcile (E1) ✓; collision pairs (E2) ✓; neutral audit (E3) ✓; bulk renames + stubs (E4) ✓; round-trip verify (E5) ✓; element composition (B2 `_is_element_species`) ✓.

**Placeholder scan:** Phase E tasks are procedural (data-dependent per-name judgment) by necessity — they carry exact queries/commands but not per-name code, which is correct for a supervised migration; the grammar tasks A–D carry full code. `<NEW_SHA>` in D1 is a deliberate fill-at-execution (the SHA of the landed A–C commits).

**Type consistency:** `State` enum, `StandardName.state`, `_check_state_gate` used consistently across A4/B1/B2; parse/compose both call the gate; `SEGMENT_TOKEN_MAP["state"]` matches the vocabulary file stem `states`.

**Sequencing risk (explicit):** C1 breaks the published catalog's round-trip until E runs — the plan sequences A/B/D first, stages E's scripts, then lands C1 + executes E in one supervised window (noted in C1 Step 6/7 and E4).
