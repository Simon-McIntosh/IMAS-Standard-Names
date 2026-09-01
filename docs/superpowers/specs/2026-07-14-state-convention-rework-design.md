# State-resolution convention rework — design

**Date:** 2026-07-14
**Status:** approved (design); implementation plan to follow
**Scope:** `imas-standard-names` grammar + `imas-standard-names-catalog` names + `imas-codex` pipeline/SPA composer

## Problem

The grammar encodes "state resolution" — a quantity resolved for a specific
charge/internal state of a species rather than the species aggregate — by
fusing a `state` token into compound **subject** tokens: `ion_state`,
`ion_charge_state`, `neutral_state` (`subjects.yml`). This is opaque and
defective:

1. **Not self-describing.** `ion_state_density` reads as "density of an ion
   state"; the bare word `state` never says *which* state, and it silently
   means different physics for different species. Review quorum scores these
   names low; `parallel_neutral_state_momentum_source` is the case that
   triggered this rework.
2. **Overloaded across species.** For ions `state` = charge (ionization) state;
   for neutrals it = internal (electronic/vibrational/rotational) state — a
   physically different axis.
3. **Redundant + actively corrupting.** `ion_state_*` and `ion_charge_state_*`
   are synonyms (both "a specific charge state"), and the two spellings are
   being abused as an ad-hoc scalar/vector disambiguation bit *in inconsistent
   directions*: `ion_state_diffusivity` (vector) vs `ion_charge_state_diffusivity`
   (scalar); `ion_state_particle_flux` (scalar) vs `ion_charge_state_particle_flux`
   (vector). Low review scores are the symptom; this is the disease.
4. **Violates the vocabulary rule** (`AGENTS.md`): "prefer atomic qualifiers
   over compound subjects; never fuse independent axes into one subject token."
5. **Blocks element composition.** Impurity transport (CXRS, STRAHL/SANCO,
   radiative divertor) needs per-element charge-state names. `argon_density` is
   already defined as the charge-state sum and promises state-resolved siblings.
   Fused subjects would require a new compound token *per element*
   (`argon_charge_state`, `tungsten_charge_state`, …) — the anti-pattern
   metastasizing combinatorially.

Inventory: **241** distinct `_state_` names in the current catalog checkout
(the graph reports a larger figure — reconcile against the live graph before
sizing the migration).

## Decision: a new `state` grammar segment

State resolution becomes a **first-class orthogonal segment** that refines the
subject — a fourth subject-refinement axis alongside `zone`, `orbit`,
`population`. Rejected alternatives:

- **`per_<state>` operator** (mirroring `per_toroidal_mode`): rejected on
  *layering*, not semantics. (The "per = normalization" objection fails —
  `per_toroidal_mode` is decomposition/"resolved per mode", same units, no
  `dimensionless` flag; "per = resolved-by" is established ISN usage.) But an
  operator transforms the *quantity* and cannot enforce "state requires a
  species subject" (`per_charge_state_growth_rate` would parse); it detaches the
  axis from the species in rendering and stacks badly
  (`per_toroidal_mode_per_charge_state_…`). The partial-pressure analogy argues
  the same way: "nitrogen partial pressure" is species-axis *selection*, which
  ISN handles as a subject — state is the identical selection ladder one rung
  deeper (species → population → state), i.e. subject-adjacent, not an operator.
- **Species-accurate atomic subject tokens** (`ion_charge_state`,
  `neutral_internal_state`): fixes self-description + dedup with a two-line diff
  but re-commits the compound-subject anti-pattern, blocks element composition,
  and saves nothing — the expensive migration (collision reconciliation, neutral
  audit, ~220 renames) is identical.

### Segment specification

| Aspect | Decision |
|---|---|
| Segment name | `state` |
| Vocabulary file | `imas_standard_names/grammar/vocabularies/states.yml` |
| Position | immediately after `subject` in `SEGMENT_ORDER` (between `subject` and `device`); `BASE_SEGMENT_INDICES` shifts (11,12)→(12,13); update the comment at `constants.py:225` and anything asserting those indices |
| Tokens | `charge_state`, `internal_state` — closed vocabulary, single-token (at most one state per name) |
| Model | mirror the token in `grammar/model_types.py` as a `StrEnum`; regenerate modules in the same commit (drift gate) |

### Canonical rendering rule

The state token sits **immediately after the subject**, before channel/base;
adjectival refinements (`zone`, `orbit`, `population`) stay prefix-of-subject:

```
<component>_<aggregation>_<orbit>_<population>_<subject>_<state>_<channel>_<base>_<of/at/due_to suffixes>
```

Rationale: state binds *tighter* than population — the DD nests
`ion[]/state[]/density` inside the species — so post-subject placement expresses
the binding depth and reads as the possessive chain "density of the ion's charge
state", matching the DD hierarchy. Prefix rendering (`charge_state_ion_density`)
reads worse, maximizes churn, and falsely parallels the adjectival axes.

### Validation gates

1. **State requires a species subject** — reject bare `charge_state_density`
   (same cross-segment-gate pattern as the flux-surface reduction gate).
2. **Species/state compatibility map**: `charge_state` → ion-like subjects
   (ion, impurity_ion, element/isotope species); `internal_state` → neutral-like
   subjects. Keep the map as a closed table; `ion + internal_state` is a legal
   *future* pairing (molecular ions) — allow it in the map but no catalog names
   need it yet.
3. **Review rubric criterion**: a name may carry the state segment only if its
   source DD path *actually resolves that axis* (guards against the neutral
   mis-founding below).

### Atomic vocabulary surgery (non-negotiable, same release)

Delete `ion_state`, `ion_charge_state`, `neutral_state`, and the (catalog-unused
— verify in graph) bare `state` from `subjects.yml` **in the same release** that
adds the segment. Greedy longest-prefix subject matching would otherwise capture
`ion_charge_state` whole at the subject slot, giving one spelling two parses and
breaking canonicality. No coexistence window.

## Physics mapping (DD → ISN)

- **Ions:** `charge_state`. DD ion `state` carries `z_min`/`z_max` ("Ion Charge
  State Bundles") plus electron-configuration/vibrational fields — so a DD ion
  state is not *purely* charge, but charge is the dominant axis. `charge_state`
  names it correctly; **document** that an entry may be a bundled z-range.
- **Neutrals:** `internal_state` (NOT `excited_state` — the DD state includes the
  *ground* state; "excited" would be false for a ground-state atom).
  `internal_state` covers ground/excited/metastable/vibrational — the internal
  degrees of freedom.
- **No `metastable_state` token** — metastable is a *value* on the internal-state
  axis, not an axis.
- **DD `neutral/state/neutral_type`** (cold/thermal/fast/NBI) maps to ISN
  `population`, not to `state`. Rule: DD neutral state ↦ ISN (population,
  internal_state); DD ion state ↦ ISN charge_state (possibly bundled).

## Before → after

| Before | After | Note |
|---|---|---|
| `ion_state_density` | `ion_charge_state_density` | insert one token |
| `ion_charge_state_temperature` | *spelling unchanged*, re-parses subject+state | IR-only change; synonym `ion_state_temperature` collides → deprecate onto it |
| `ion_state_particle_flux` (scalar) vs `ion_charge_state_particle_flux` (vector) | per-pair reconciliation | kinds diverge; carry scalar/vector via component/projection, not the synonym |
| `parallel_neutral_state_momentum_source` | `parallel_neutral_internal_state_momentum_source` OR `parallel_<population>_neutral_momentum_source` (no state) | depends on neutral audit |
| `fast_ion_state_pressure` | `fast_ion_charge_state_pressure` | population + subject + state stack |
| `total_ion_state_density` | `total_ion_charge_state_density` | aggregation outside, state inside |
| `per_toroidal_mode_fast_ion_state_power` | `per_toroidal_mode_fast_ion_charge_state_power` | operator wraps; state glued to subject |
| `radial_derivative_of_total_ion_state_density` | `radial_derivative_of_total_ion_charge_state_density` | |
| `ion_state_lower_bound_charge` | `ion_charge_state_lower_bound_charge` | bundle z_min; consider `…minimum_charge_number` |
| — | `argon_charge_state_density` | **new capability**, free under this design |

## Migration phases (implementation-plan input)

1. **Reconcile the inventory** against the live graph (241 catalog vs the larger
   graph figure); enumerate the exact working set.
2. **Grammar first (ISN):** add the `state` segment (`states.yml` +
   `model_types.py` + `SEGMENT_ORDER` + index shift), the two validation gates,
   the atomic subject-token deletion, SPA composer support; regenerate modules;
   full ISN suite + full-catalog round-trip must stay green. This is the design's
   testable core and lands independently of the catalog renames.
3. **Collision pairs first:** the ~15 `ion_state_X` / `ion_charge_state_X` pairs
   with diverging kinds — semantic reconciliation (component/projection carries
   scalar-vs-vector), *before* any mechanical rename (rename-onto-existing-id is
   prohibited).
4. **Neutral audit:** for each `neutral_state_*` name, check whether its source
   DD path genuinely resolves an internal state. Expect the family to **shrink** —
   mis-founded transport-coefficient names become population-resolved with *no*
   state token; keep `internal_state` for the true minority (Balmer, metastable
   He). Do not mechanically 1:1 rename.
5. **Bulk renames** via the pipeline edit path (P2-parity gates, P1 deprecation
   stubs for the accepted subset only). The rename-cascade tooling skips
   directional projections (parallel/poloidal/toroidal) — handle those per-name.
6. **IR-only changes:** the 21 already-`ion_charge_state_*` names change IR
   (subject+state) without changing id — confirm catalog reconcile/exports
   handle IR-only changes.
7. **Round-trip gate:** all working-set names round-trip through
   `parse_standard_name`; SPA compose/seed harness green.

## Risks / guards

- The migration cost center is **semantic reconciliation** (collision pairs +
  neutral audit), not grammar machinery. Budget accordingly.
- Don't let the new segment invite state-resolving names whose data will never
  be state-resolved (the neutral transport-coefficient family is the warning
  case) — the review-rubric DD-path criterion (gate 3) enforces this.
- Deprecation stubs are needed only for the *accepted* subset; most catalog
  entries are draft.

## Open items (resolved for this design)

- Neutral token: **`internal_state`** (lead-confirmed).
- Segment vs operator vs subject-tokens: **segment** (this document).
- Rendering: **post-subject** (this document).
