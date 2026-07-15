# Naming / Duplicate Manifest — Review Rows 7–13

Read-only investigation. Live Neo4j graph (3876 StandardNames, `sn status` OK,
2026-07-15). DD evidence via imas-dd MCP (`fetch_dd_paths`). Grammar evidence
from `imas_standard_names/grammar/` in ISN. No graph mutations performed.

Relationship semantics used:
- **DD source** = `(StandardName)<-[:PRODUCED_NAME]-(StandardNameSource {id:'dd:<path>'})`
- **Authoritative DD map** = `(IMASNode)-[:HAS_STANDARD_NAME]->(StandardName)` (the
  edge the catalog export follows; a `source_path` *property* can be stale relative
  to this edge — see Row 12).
- **Grammar parent** = `(child)-[:HAS_PARENT]->(parent)` (shared-segment lineage).

CLI reference (confirmed from `sn edit --help` / `sn supersede --help`):
- Rename:  `imas-codex sn edit OLD --rename NEW --reason "..." [--scope self|family|subtree] --dry-run`
- Doc-only:`imas-codex sn edit NAME --docs "…full replacement…" --reason "..." --axis docs --dry-run`
- Fold into existing accepted name: `imas-codex sn supersede OLD --into TARGET --dry-run`
  (`--into` target MUST be `name_stage='accepted'`; tombstones OLD, threads REFINED_FROM.)

---

## Row 7 — ICRH power: launched vs coupled vs absorbed → **DOC-ONLY**

| name | name_stage | docs_stage | DD source | scope |
|---|---|---|---|---|
| `total_power_due_to_ion_cyclotron_heating` | accepted | accepted | `dd:summary/heating_current_drive/power_ic/value` | system total |
| `power_due_to_ion_cyclotron_heating` (parent) | accepted | accepted | `dd:summary/heating_current_drive/ic/power/value` | per-launcher |
| `total_power_of_ion_cyclotron_heating_antenna` | accepted | accepted | `dd:ic_antennas/power_launched` | **launched** (distinct) |

**DD facts (imas-dd):**
- `summary/.../power_ic/value` = *"Total Ion Cyclotron (IC) heating power (Pic) **coupled to the plasma** …"*
- `summary/.../ic/power/value` = *"Ion Cyclotron … heating power **coupled to the plasma** from a specific launcher."*
- `ic_antennas/power_launched` = the antenna **launched** power (already a cleanly distinct name).

**Finding:** The name is NOT launched-antenna power — that is the separate
`total_power_of_ion_cyclotron_heating_antenna` (dd `ic_antennas/power_launched`).
DD calls the `power_ic` quantity **"coupled to the plasma"**. The current SN
documentation asserts it is **"absorbed by the plasma"** and *"excludes launched
power that is not absorbed"*. Coupled (crosses the antenna→plasma boundary =
launched − reflected − near-field loss) is weaker than absorbed (damped in the
plasma); for multi-pass/parasitic scenarios they differ. Under strict-normative
docs the exclusion clause is slightly wrong.

**Recommendation:** DOC-ONLY correction — replace "absorbed by the plasma" with
"coupled to the plasma" (DD wording) in both `total_power_due_to_ion_cyclotron_heating`
and its parent `power_due_to_ion_cyclotron_heating`. **No rename** (name is sound;
antenna/launched vs heating/coupled pair is already well-distinguished).

```
imas-codex sn edit total_power_due_to_ion_cyclotron_heating \
  --docs "<full doc, 'coupled to the plasma' replacing 'absorbed'>" \
  --reason "DD summary/heating_current_drive/power_ic/value defines Pic as power COUPLED to the plasma, not absorbed; align exclusion clause." \
  --axis docs --dry-run
# repeat for power_due_to_ion_cyclotron_heating (ic/power/value, same wording)
```

**Confidence:** High on disposition (doc-only, not launched-power).
**Human decision:** LOW-STAKES — is "coupled" vs "absorbed" worth a doc edit, or
is coupled≈absorbed acceptable? Recommended default: make the edit (matches DD).

---

## Row 8 — coherent-wave power channels omit the wave mechanism → **FAMILY RENAME (human decision)**

The wave-absorption power family under DD `waves/coherent_wave/global_quantities`
is **internally inconsistent**: four core channels omit "wave", while their own
siblings in the same DD subtree carry it.

| name | name_stage | DD source | carries "wave"? |
|---|---|---|---|
| `thermal_electron_power` | accepted | `dd:waves/coherent_wave/global_quantities/electrons/power_thermal` | **NO** |
| `fast_electron_power` | accepted | `…/electrons/power_fast` | **NO** |
| `thermal_ion_power` | accepted | `…/ion/power_thermal` | **NO** |
| `fast_ion_power` | accepted | `…/ion/power_fast` | **NO** |
| `fast_ion_charge_state_absorbed_wave_power` | accepted | `…/ion/state/power_fast` | YES |
| `ion_charge_state_absorbed_wave_power` | accepted | `…/ion/state/power_fast` | YES |
| `per_toroidal_mode_wave_absorbed_power` | reviewed | `…/power_n_phi` | YES |
| `per_toroidal_mode_thermal_electron_power` | accepted | `…/electrons/power_thermal_n_phi` | NO |

`thermal_electron_power` / `fast_electron_power` are grammar children of
`electron_power` (a **derived, deliberately broad** parent covering *all* electron
power channels — wave, collisional, radiative). The children are actually
**coherent-wave-only** (DD `power_thermal` = *"Total RF wave power thermally
absorbed by the electron population"*), so their broad names overclaim scope.

**Recommendation:** Rename the four bare channels (and their `per_toroidal_mode_*`
variants) to carry absorbed-wave semantics, matching the existing
`…_absorbed_wave_power` siblings, e.g.:
- `thermal_electron_power` → `thermal_electron_absorbed_wave_power`
- `fast_electron_power` → `fast_electron_absorbed_wave_power`
- `thermal_ion_power` → `thermal_ion_absorbed_wave_power`
- `fast_ion_power` → `fast_ion_absorbed_wave_power`

```
imas-codex sn edit thermal_electron_power \
  --rename thermal_electron_absorbed_wave_power --scope self \
  --reason "DD waves/coherent_wave/.../electrons/power_thermal is RF wave power absorbed by thermal electrons; align with sibling *_absorbed_wave_power names; parent electron_power is broader (all channels)." \
  --dry-run
# analogous for fast_electron_power, thermal_ion_power, fast_ion_power (+ per_toroidal_mode_* variants)
```

**Confidence:** High that the current names overclaim (DD is wave-specific);
Medium on the exact token/ordering.
**HUMAN DECISION (flag):**
(A) rename the 4+ channels to `<pop>_absorbed_wave_power` (my default — restores
family consistency), **vs** (B) keep broad names and instead generalise the docs +
narrow via qualifiers. Note (A) touches accepted names and changes grammar
shared-segment lineage (new names no longer share `electron_power` segment — they
would reparent under an `absorbed_wave_power` family), so the executor must confirm
composer round-trip and reparenting for each.

---

## Row 9 — bare `power_density` vs `electron_power_density` → **NOT A DUPLICATE (keep both)**

| name | name_stage | physical_base | DD source | parent |
|---|---|---|---|---|
| `power_density` | accepted | power_density | `derived:power_density` (NO DD path) | — (family parent) |
| `electron_power_density` | accepted | power_density | 7 real DD paths (core/edge/plasma_sources electrons+neutral energy) | `power_density` |

`electron_power_density` DD sources: `core_sources`, `plasma_sources`,
`edge_sources` `…/electrons/energy` (+ neutral energy) — real, electron-specific.
`power_density` is `derived:` — a **source-less grammar family parent** and is
already `electron_power_density`'s `HAS_PARENT`.

**Recommendation:** KEEP BOTH. `power_density` is a genuine derived family parent
with distinct (null-DD) provenance; `electron_power_density` is its DD-backed
electron specialisation. No merge, no rename.
**Confidence:** High. **Human decision:** none.

---

## Row 10 — `thermal_electron_stored_energy` vs the "energy" family → **RENAME the minority**

`thermal_electron_stored_energy` is the **sole** member of the whole energy family
using `physical_base='stored_energy'` and the word "stored":

- `physical_base='energy'` (majority): `plasma_energy`, `thermal_plasma_energy`,
  `total_plasma_energy`, `electron_energy`, `ion_energy`, `thermal_ion_energy`,
  `total_thermal_ion_energy`, `fast_electron_energy`, `fast_particle_energy`,
  `diamagnetic_energy`, … (all volume-integrated stored energies, none say "stored")
- `physical_base='stored_energy'` (minority): **only** `thermal_electron_stored_energy`
  (`dd:summary/global_quantities/energy_electrons_thermal/value` = "Thermal electron
  plasma energy content").

Directly parallel: `thermal_plasma_energy` (`…/energy_thermal/value` = "Total
thermal plasma energy content Wth") drops "stored"; the electron analogue keeps it.
`thermal_electron_energy` does **not** currently exist (free target).

**Recommendation:** Adopt the majority "energy" convention (matches DD "energy
content"). Migrate the single minority:
- `thermal_electron_stored_energy` → `thermal_electron_energy` (and set base=energy).
  Optionally reparent under `electron_energy` (grammar family), mirroring
  `thermal_ion_energy` under ion energy.

```
imas-codex sn edit thermal_electron_stored_energy \
  --rename thermal_electron_energy --scope self \
  --reason "Family-wide energy convention: all volume-integrated stored energies use base 'energy' w/o 'stored' (thermal_plasma_energy, thermal_ion_energy); migrate lone minority. DD energy_electrons_thermal = 'thermal electron energy content'." \
  --dry-run
```

**Confidence:** High that the minority migrates.
**HUMAN DECISION (flag):** the family rule DIRECTION — keep "energy" (drop "stored",
majority + DD wording; my default) vs re-introduce "stored" family-wide. Default =
"energy". (Dropping "stored" loses an explicit confinement-inventory cue, but the
whole family already dropped it.)

---

## Row 11 — `volume_of_first_wall` means enclosed volume → **DOC/CONVENTION (keep name)**

| name | DD source | DD meaning |
|---|---|---|
| `volume_of_first_wall` | `dd:wall/first_wall_enclosed_volume` | "Total geometric volume **enclosed** by the first wall boundary" |
| `area_of_first_wall` | `dd:wall/first_wall_surface_area` | "Total **wetted area** of the first wall" (the wall's own surface) |
| `volume_of_flux_surface` (precedent) | equilibrium volume | volume **enclosed** by the flux surface |

**Grammar evidence:** `volume` is a *generic* base in `generic_physical_bases.yml`
(needs qualification). The grammar has **no `enclosed_by` relation** — locus
relations are `[of, at, over, along]` (`locus_registry.yml`). The doc comment cites
`volume_enclosed_by_flux_surface` as illustrative, but **no accepted name uses
"enclosed"** and the real, accepted convention is `volume_of_<surface>` — and
`volume_of_flux_surface` (accepted) **already means the enclosed volume** (a flux
surface has no material volume). So `volume_of_first_wall` is **consistent with
established precedent**.

The genuine wrinkle: `area_of_first_wall` = the wall's *own* surface area, whereas
`volume_of_first_wall` = the *enclosed* volume — the `_of_` connective is overloaded
across the two siblings. But this matches DD path semantics and the
`volume_of_flux_surface` precedent.

**Recommendation:** KEEP `volume_of_first_wall` + record a **geometric-base
convention**: `volume_of_<bounding-surface>` denotes the volume enclosed by that
surface (already stated in the name's docs: "Total volume enclosed by the first
wall contour"). This is effectively already satisfied — at most a one-line
convention note. **No rename** (renaming would require inventing an `enclosed_by`
relation and would also force `volume_of_flux_surface` to change).

**Confidence:** High. **HUMAN DECISION (flag, low weight):**
(A) keep `volume_of_first_wall` + document the `volume_of_<surface>=enclosed`
convention (my default — zero churn, matches `volume_of_flux_surface`), **vs**
(B) extend the grammar with an `enclosed_by` relation and rename both
`volume_of_first_wall` and `volume_of_flux_surface` (larger grammar change).

---

## Row 12 — deposited-power duplicates → **MERGE `total_electron_deposited_power` → `electron_deposited_power`**

Grammar lineage: `deposited_power` → `electron_deposited_power` → `total_electron_deposited_power`.

**Authoritative DD ownership (`HAS_STANDARD_NAME`):**
| name | name_stage | authoritatively OWNS | note |
|---|---|---|---|
| `deposited_power` (parent) | accepted | (none returned) | derived/generic distribution-source power (`dd:distributions/distribution/global_quantities/source/power`); kinetic, any distribution |
| `electron_deposited_power` (mid) | accepted | **(none — ORPHANED)** | `source_path` property still says `plasma_sources/.../electrons/power`, but that IMASNode now maps to `total_electron_deposited_power` |
| `total_electron_deposited_power` (leaf) | accepted | `core_sources/source/global_quantities/electrons/power`, `plasma_sources/source/global_quantities/electrons/power` | holds ALL the real electron-source DD backing |

**DD facts:** both `plasma_sources` and `core_sources` `…/source/global_quantities/
electrons/power` are **per-source-term** (source is an AoS) electron power ("Total
power coupled specifically to the electron population"). There is **no DD node for
a sum-over-sources**, so the `total_` prefix has no DD basis and misdescribes a
per-source quantity. The middle name `electron_deposited_power` is orphaned (lost
its authoritative edge to the leaf).

**Recommendation:** Collapse the redundant middle/leaf pair into ONE canonical
per-source electron-deposited-power name. Prefer the cleaner `electron_deposited_power`
(drop the misleading "total_"):

```
imas-codex sn supersede total_electron_deposited_power --into electron_deposited_power --dry-run
```

Then VERIFY (executor, mandatory — "zero orphaned references required"): the two
DD IMASNodes (`core_sources/.../electrons/power`, `plasma_sources/.../electrons/power`)
resolve to `electron_deposited_power` after the fold. If `supersede` does not move
the `HAS_STANDARD_NAME` edges, the executor must re-point them (or run the fold in
the opposite direction — see decision).

- KEEP `deposited_power` (distinct scope: generic kinetic distribution-source power,
  `distributions` IDS) as family parent.
- KEEP `electron_power` (derived broad parent: *all* electron power channels; distinct
  from the deposited-source channel). Not a duplicate.

**Confidence:** High that total_/electron_ are duplicates and one must go.
**HUMAN DECISION (flag):** survivor name — `electron_deposited_power` (my default;
drops misleading "total_", but is currently orphaned so DD edges must be moved onto
it) **vs** keep `total_electron_deposited_power` (already owns the DD edges, less
edge-surgery, but retains the inaccurate "total_"). Default = `electron_deposited_power`
with edge reassignment verified.

---

## Row 13 — plasma-energy (family) + plasma-current (duplicate)

### 13a. Plasma energy — **WELL-FORMED, NO MERGE**

| name | name_stage | DD source | scope |
|---|---|---|---|
| `plasma_energy` (parent) | accepted | `derived:plasma_energy` (no DD) | generic stored internal energy |
| `thermal_plasma_energy` | accepted | `dd:summary/global_quantities/energy_thermal/value` (Wth) | thermal only |
| `total_plasma_energy` | accepted | `dd:summary/global_quantities/energy_total/value` (Wmhd) | thermal + fast |
| `diamagnetic_energy` (separate) | accepted | (diamagnetic measurement) | distinct measurement method |

Parent + two children with **distinct DD sources and distinct physical scope**
(thermal-only vs total incl. fast). Not duplicates — "total"/"thermal" mark genuine
aggregation differences. The reviewer's "4th" name is most likely `diamagnetic_energy`
(a distinct *diamagnetically-measured* stored energy), which should also be kept.

**Recommendation:** NO ACTION (confirm well-formed). **Confidence:** High.
**Human decision:** none.

### 13b. Plasma current — **MERGE `toroidal_plasma_current` → `plasma_current`**

| name | name_stage | docs_stage | authoritatively OWNS (`ip` paths) |
|---|---|---|---|
| `plasma_current` (parent) | accepted | pending | `magnetics/ip`, `core_profiles/…/ip`, `equilibrium/…/global_quantities/ip`, `plasma_profiles/…/ip` |
| `toroidal_plasma_current` (child) | accepted | accepted | `summary/…/ip/value`, `equilibrium/…/constraints/ip/measured`, `equilibrium/…/constraints/ip/reconstructed`, `plasma_initiation/…/ip` |

Both are the **net toroidal plasma current I_p**, identical definition
(`I_p = ∬ j_φ dA` over the poloidal cross-section) in **both** documentations. All
8 DD paths are `ip` — the *same* physical quantity, arbitrarily partitioned across
two names. Plasma current **is** toroidal by definition, so "toroidal" adds **no
distinct frame or aggregation** (locked-decision test → redundant).

**Recommendation:** Fold the redundant child into the canonical parent:

```
imas-codex sn supersede toroidal_plasma_current --into plasma_current --dry-run
```

Then VERIFY the 4 `ip` paths owned by `toroidal_plasma_current` re-point to
`plasma_current` (zero orphans). Consider promoting `plasma_current` docs_stage
pending→accepted afterwards (its docs are complete).

**Confidence:** High (identical physics + all-`ip` sources).
**HUMAN DECISION (flag):** confirm the fold direction (`plasma_current` survives —
my default, it is the parent/standard I_p and the DD `ip` primary) and that no
consumer relies on a separate `toroidal_plasma_current` id. Default = fold into
`plasma_current`.

---

## Summary of dispositions

| Row | Canonical | Disposition | Op |
|---|---|---|---|
| 7 | `total_power_due_to_ion_cyclotron_heating` (+ parent) | doc-only: "absorbed"→"coupled" | `sn edit --docs` |
| 8 | `<pop>_absorbed_wave_power` ×4+ | family rename (wave semantics) | `sn edit --rename` |
| 9 | keep both `power_density`, `electron_power_density` | none | — |
| 10 | `thermal_electron_energy` | rename minority (drop "stored") | `sn edit --rename` |
| 11 | keep `volume_of_first_wall` | doc/convention only | `sn edit --docs` (opt.) |
| 12 | `electron_deposited_power` | merge `total_electron_deposited_power` in | `sn supersede` |
| 13a | plasma_energy family | none (well-formed) | — |
| 13b | `plasma_current` | merge `toroidal_plasma_current` in | `sn supersede` |

## Genuine human decisions (→ AskUserQuestion)
1. **Row 8** — rename 4+ wave channels to `*_absorbed_wave_power` (default YES) vs generalise docs. Touches accepted names + grammar reparenting.
2. **Row 10** — family rule: "energy" (drop "stored", default) vs "stored energy".
3. **Row 12** — survivor name `electron_deposited_power` (default, needs DD-edge move) vs `total_electron_deposited_power` (owns edges, keeps misleading "total_").
4. **Row 13b** — confirm fold `toroidal_plasma_current` → `plasma_current` (default YES).
5. **Row 11** (low weight) — keep `volume_of_first_wall`+convention (default) vs add `enclosed_by` grammar relation.
6. **Row 7** (low weight) — make the coupled/absorbed doc edit (default) vs leave.

## Execution caveats for `sn supersede` merges (rows 12, 13b)
`sn supersede` tombstones OLD + threads REFINED_FROM, but it is **unverified here**
whether it moves the OLD name's `HAS_STANDARD_NAME` (DD-path) edges onto `--into`.
Both merges require post-fold verification that every `ip` / electron-power DD path
resolves to the survivor with **zero orphaned references** (row-12/13b acceptance
criteria). Run each `--dry-run` first and inspect the reported cascade.
