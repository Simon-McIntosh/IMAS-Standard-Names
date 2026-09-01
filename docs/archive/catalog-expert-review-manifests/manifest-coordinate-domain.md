# Coordinate-Coverage & Domain-Move Manifest
**Followup f-coordinate-domain-gaps · §4.5 · rows 9/14/17**
Investigation worker (read-only). Live graph: `imas-codex sn status` = 3876 names,
2347 accepted. All evidence below queried against live Neo4j on 2026-07-15.
DD grounding: `mcp__imas-dd` (latest indexed = DD 4.x; camera/pulse_schedule
paths cited are lifecycle `alpha`, present in current DD).

---

## 0. Domain-reassignment MECHANISM (read this first — it gates workstream B)

`physics_domain` is a **scalar string property on the `StandardName` graph node**
(`sn.physics_domain`), plus a `source_domains` list. It is the canonical
`PhysicsDomain` StrEnum in **ISN** `imas_standard_names/grammar/tag_types.py`
(32 values; all target domains below already exist — **no ISN vocab-YAML change
needed**).

**There is NO first-class CLI to reassign a domain on an accepted name.**
- `sn edit` has axes `name` / `docs` / `both` only — no `--domain` axis.
- `physics_domain` is SET only inside the pipeline: seed (`build_dd.py`),
  merge/promote/consolidation (`graph_ops.py` lines 2126/2186/2744/5693/5711),
  and catalog import. Re-running `sn run` will **not** move an already-accepted
  name (its domain is frozen on the node).
- It is written to the **published catalog** by imas-codex `export.py`:
  ISNC groups names into per-domain files `standard_names/<domain>.yml` and
  writes `physics_domain:` on every entry. So a domain move is a **real,
  visible catalog change** (the name relocates to a different YAML file).
  (ISN's `yaml_store.py` `_STRIPPED_FIELDS={physics_domain,dd_paths}` strips it
  on *load* — a schema-migration artifact — but the grouping is authoritative.)

**Executor options (pick one; flag to lead):**
1. **Reviewed Cypher SET on the live graph** + re-export/publish. Exact form:
   ```cypher
   MATCH (sn:StandardName {id:$name})
   SET sn.physics_domain = $target,
       sn.source_domains  = [$target]
   ```
   (write op — outside my read-only scope). Then re-run the ISNC export/publish
   so `standard_names/<target>.yml` is regenerated. Low-risk, deterministic.
2. **Add a thin `sn reclassify <name> --domain <target> --reason ...`**
   subcommand mirroring `sn edit` (records origin/reason, SETs the property).
   Preferred if more than a handful of moves land, for provenance.

Recommend **option 1** for this batch (≈40 moves, one-off) with the moves below
applied as a single reviewed Cypher script; escalate to option 2 only if the
lead wants provenance trails.

---

## WORKSTREAM A — Coordinate completeness (rows 9, 14)

### A.1 Coverage matrix (cylindrical triplet R / Z / toroidal-φ), accepted names

Legend: ✓ accepted · ⊘ superseded/exhausted, NO accepted successor (gap) ·
✗ absent · n/a = axisymmetric object, no φ leaf in DD.

| Object | radial (R) | vertical (Z) | toroidal (φ / angle) | DD backing |
|---|---|---|---|---|
| magnetic_axis | ✓ | ✓ | n/a | equilibrium (axisymmetric) |
| geometric_axis | ✓ | ✓ | n/a | equilibrium |
| x_point / strike_point / current_center | ✓ | ✓ | n/a | equilibrium |
| **measurement_position** | ✓ | ✓ | ✓ | *complete exemplar* |
| **plasma_boundary_gap_reference_point** | ⊘ | ✓ | poloidal_angle ✓; φ n/a | `pulse_schedule/position_control/gap/{r,z,angle}` |
| **camera** | ✗ | ⊘ | ✗ | `camera_visible/channel/aperture/centre/{r?,z,phi}` |
| **diagnostic aperture** | ✓ (`radial_coordinate_of_aperture`) | ✓ | ✗ | `camera_visible/channel/aperture/centre/phi` EXISTS |
| **detector_pixel** | ✓ | ✓ | ✗ (has vertical_angle) | detector centre φ in DD |
| flux_loop / rogowski_coil | ✓ | ✓ | ✗ | magnetics (φ present in DD) |
| lower_hybrid_antenna(_row) | ✓ | ✓ | ✗ | lh_antennas |
| neutral_beam_injector | ✓ | ✓ | ✗ | nbi |

### A.2 Proposed MISSING names (all must enter via `sn run`/`sn edit` — NOT hand-authored in ISN)

**Confident, source-backed (DD leaf verified present):**

| Proposed name | DD path evidence | Suggested domain | Notes |
|---|---|---|---|
| `toroidal_angle_of_aperture` | `camera_visible/channel/aperture/centre/phi` (FLT_0D, rad) | radiation_measurement_diagnostics | R,Z already accepted; φ is the only missing triplet leg |
| `toroidal_angle_of_diagnostic_aperture` | aperture `centre/phi` (cross-diag cluster) | radiation_measurement_diagnostics | matches existing `{radial,vertical,x,y}_coordinate_of_diagnostic_aperture` |
| `toroidal_angle_of_detector_pixel` | detector centre φ | radiation_measurement_diagnostics | R,Z accepted; φ absent |
| `radial_coordinate_of_plasma_boundary_gap_reference_point` | `pulse_schedule/position_control/gap/r` (FLT_0D, m) | see A.3 (domain unification) | **currently ⊘ superseded, no accepted successor** — RE-PROPOSE; Z + poloidal_angle already accepted |

**Camera position triplet (needs a scoping decision — see A.4):**
Camera geometry in DD is modelled **per aperture / optical_element / detector
`centre` (r,z,phi)**, not a single "camera centre". Accepted names collapse the
object to `_of_camera` for direction/image-up unit vectors, but the **position
(R,Z,φ) is entirely absent** (`vertical_coordinate_of_camera` is superseded with
no successor; `z_unit_vector_of_camera` was correctly refined into the
`z_direction`/`z_image_up` pair). Recommend the executor run
`sn run` **scoped to `camera_ir` + `camera_visible` geometry subtrees** and let
the pipeline surface the correct object stem (aperture/optical_element centre)
rather than hand-forcing `radial_coordinate_of_camera`. Candidate names the
pipeline should be steered toward:
`{radial_coordinate,vertical_coordinate,toroidal_angle}_of_camera_optical_element`
(or `_of_camera` if the family keeps collapsing to the camera object).

### A.3 Locus / frame → StandardTerm candidates
The **reference frame** of two angle quantities is only *implicit* and should be
exposed as a `StandardTerm` (a `Locus`/frame definition), not left buried in prose:
- **plasma boundary gap reference point** — `poloidal_angle_at_..._gap_reference_point`
  is defined "relative to the poloidal horizontal axis" (DD `gap/angle` doc). The
  reference-point + horizontal-axis frame is a reusable locus → StandardTerm.
- **line of sight** — `toroidal_angle_of_line_of_sight` presupposes a viewing-chord
  frame shared across ~14 diagnostics; the chord/first-point locus is only
  indirectly visible → StandardTerm.

### A.4 Genuine human decisions (workstream A)
1. **Camera position object granularity** — collapse to `_of_camera`, or model per
   `aperture`/`optical_element`? *My default:* follow the existing collapsed
   `_of_camera` convention (consistent with the accepted direction-vector family),
   proposed via pipeline scoped to camera IDS.
2. **How far to push the toroidal-φ backfill** — φ leaves exist in DD for
   flux_loop, rogowski_coil, antennas, NBI too. *My default:* propose φ only for
   the **diagnostic optical family** (aperture, detector_pixel, camera) where the
   expert flagged the gap; treat magnetics/antenna φ as a separate, lower-priority
   pass (many are effectively axisymmetric-installed and low physics value).

---

## WORKSTREAM B — Domain taxonomy (row 17)

Principle applied (LOCKED): **semantic-subject**. Plasma quantities follow the
physical phenomenon; the diagnostic METHOD (Langmuir probe, mass spec, camera)
is a SECONDARY facet and does NOT override. Intrinsic hardware/component
quantities follow the component's functional subsystem.

### B.1 `computational_workflow` (3 names) — ALL mis-filed (confident move out)
`computational_workflow` = "auxiliary/atomic/geometry/computational tools". A
gyrocenter frequency is a **physical quantity**, so the move OUT is confident;
only the TARGET is a physics call.

| Name | current → target | rule / evidence |
|---|---|---|
| `gyrocenter_frequency` | computational_workflow → **fast_particles** *(default; human-call)* | subject=gyrocenter, unit=rad/s; source IDS = `distributions` (fast-ion distribution functions) |
| `poloidal_gyrocenter_frequency` | computational_workflow → **fast_particles** | src=`distributions` |
| `toroidal_gyrocenter_frequency` | computational_workflow → **fast_particles** | src=`distributions` |

**Consistency note:** `gyrocenter_density`, `gyrocenter_current_density` are
currently **domain=NULL** (accepted). Whatever target is chosen for the 3
frequencies should also be applied to these 2 for a coherent `gyrocenter`
family. → see B.5 human-call #1.

### B.2 `mechanical_measurement_diagnostics` (52 accepted; expert said ~61) — heavily mis-filed
Only the **`operational_instrumentation`-sourced** entries are genuinely
mechanical. Everything else drifted in. Domain shrinks from 52 → ~11.

**STAY (genuinely mechanical, `operational_instrumentation`) — 11, confident:**
`displacement_of_passive_structure`, `temperature_at_sensor_attachment_point`,
`x/y/z_coordinate_of_sensor_attachment_point`,
`x/y/z_first_measurement_direction_unit_vector_of_strain_gauge`,
`x/y/z_second_measurement_direction_unit_vector_of_strain_gauge`.

**CONFIDENT MOVES:**

| Name(s) | current → target | rule (evidence) |
|---|---|---|
| `toroidal_angular_width_of_camera`, `vertical_angular_width_of_camera` | → **radiation_measurement_diagnostics** | intrinsic camera-diagnostic geometry; src=`camera_ir` |
| `voltage_of_mass_spectrometer`, `voltage_of_mass_spectrometer_channel`, `ion_current_of_mass_spectrometer_channel`, `current_of_mass_spectrometer_channel`, `pressure_of_mass_spectrometer_channel`, `neutral_pressure_of_mass_spectrometer_channel` | → **particle_measurement_diagnostics** | intrinsic mass-spec hardware quantities; src=`spectrometer_mass` (→particle in categorizer) |
| `coolant_temperature_at_inlet`, `coolant_temperature_at_outlet`, `temperature_at_inlet`, `temperature_at_outlet`, `thermal_energy_of_plant_component_port`, `thermal_power_of_plant_component_port`, `energy_of_plant_component_port`, `power_of_plant_component_port` | → **plant_systems** | cooling-loop / calorimetry / plant-port quantities; src=`calorimetry`/`balance_of_plant`/`breeding_blanket` |
| `area_of_langmuir_probe`, `effective_area_of_langmuir_probe`, `wetted_area_of_langmuir_probe` | → **particle_measurement_diagnostics** | intrinsic probe **hardware geometry** (fixed diagnostic parameter); src=`langmuir_probes` |
| `electron_temperature_at_midplane`, `electron_average_temperature_at_midplane`, `electron_temperature_at_wall`, `ion_temperature_at_midplane`, `ion_field_line_average_temperature_over_scrape_off_layer`, `electrostatic_potential_at_midplane`, `electrostatic_potential_at_wall`, `temperature_at_midplane` | → **edge_plasma_physics** | **plasma quantities** at midplane/wall/SOL; Langmuir-probe method is secondary (LOCKED principle). Locations (midplane, SOL, wall) are edge-physics |
| `temperature_at_wall` | → **plasma_wall_interactions** | wall material temperature; src=`wall` |

**NEEDS HUMAN CALL (probe-intrinsic vs edge-plasma phenomenon):**

| Name(s) | current | my default | tension |
|---|---|---|---|
| `ion_current_density`, `ion_saturated_current_density`, `fluctuating_ion_current_density`, `fluctuating_ion_saturated_current_density`, `parallel_ion_current_density`, `parallel_fluctuating_ion_current_density`, `saturated_current_density` | mechanical | **edge_plasma_physics** | edge sheath current density is a plasma phenomenon, but "saturation" is probe-sheath-specific → could argue particle_measurement_diagnostics |
| `ion_saturated_current`, `saturated_current`, `floating_electrostatic_potential` | mechanical | **particle_measurement_diagnostics** | probe I-V-curve characteristics (hardware-defined) vs plasma sheath potential |
| `heat_flux`, `parallel_heat_flux` | mechanical | **edge_plasma_physics** (or divertor_physics) | generic edge/divertor heat flux; `parallel_heat_flux` src=`langmuir_probes`; `heat_flux` has no src (composed) |
| `neutral_pressure` | mechanical | **stay mechanical** (or particle_measurement_diagnostics) | src=`barometry`, which the categorizer maps to mechanical; but neutral-gas pressure is arguably a gas/particle diagnostic → also revisit the `barometry→mechanical` map globally |

### B.3 lower-hybrid antenna pressure — confident move
| Name | current → target | rule |
|---|---|---|
| `pressure_of_lower_hybrid_antenna` | **plant_systems → auxiliary_heating** | src=`lh_antennas` (auxiliary_heating). Sibling names `pressure_of_ion_cyclotron_heating_antenna` and `gas_pressure_of_ion_cyclotron_heating_antenna` are already in auxiliary_heating — this one is the inconsistent outlier. LH antenna is an auxiliary-heating launcher; its intrinsic gas pressure follows that subsystem. |

### B.4 `plasma_control` (2 names) — 1 correct, 1 needs-call
| Name | verdict |
|---|---|
| `poloidal_angle_at_plasma_boundary_gap_reference_point` | correct (`pulse_schedule`→plasma_control) — but see B.5 #2 (gap-reference domain unification) |
| `toroidal_angle_of_line_of_sight` | **needs-human**: src spans ~14 diagnostics + pulse_schedule; it's a diagnostic viewing-chord geometry, NOT a control quantity. *My default:* **general** (universal geometry across many IDS) |

### B.5 Genuine human decisions (workstream B) — with recommended defaults
1. **gyrocenter family target** (5 names: 3 frequencies + `gyrocenter_density`,
   `gyrocenter_current_density`): `fast_particles` vs `gyrokinetics` vs `transport`.
   *Default:* **fast_particles** (source IDS = `distributions`; orbit-averaged
   fast-particle quantities). Apply the SAME domain to all 5 for coherence.
2. **gap reference point domain unification**: the triplet is currently split —
   R (superseded, was plasma_control), Z (equilibrium), poloidal_angle
   (plasma_control), gap value (equilibrium). *Default:* unify all four to
   **equilibrium** (semantic subject = plasma-boundary geometry; the control USE
   is secondary; the same object also appears under `equilibrium/.../boundary/gap`).
   Alternative if the lead views it as a control artifact: unify to plasma_control.
3. **Langmuir current-density / saturation cluster** (B.2 needs-human rows):
   probe-intrinsic vs edge-plasma. *Default:* current-DENSITIES and heat-flux →
   edge_plasma_physics; the raw probe I-V quantities (saturated_current,
   floating_electrostatic_potential) → particle_measurement_diagnostics.
4. **`barometry → mechanical_measurement_diagnostics`** categorizer mapping
   (`imas_codex/definitions/physics/ids_domains.json`): revisit globally — neutral
   pressure gauges are arguably a gas/particle diagnostic. *Default:* leave as-is
   this pass (low value; only `neutral_pressure` affected).
5. **`toroidal_angle_of_line_of_sight`** target (B.4). *Default:* general.

---

## Summary counts
- **Coordinate proposals (missing names, via pipeline):** 4 confident source-backed
  (`toroidal_angle_of_{aperture,diagnostic_aperture,detector_pixel}` +
  re-propose `radial_coordinate_of_plasma_boundary_gap_reference_point`) + the
  camera position triplet (needs A.4 scoping decision). 2 StandardTerm frame
  definitions (gap-reference frame, line-of-sight frame).
- **Domain moves:** ~30 confident (out of computational_workflow=3;
  mechanical→{radiation 2, particle 9, plant_systems 8, edge 8, PWI 1}; LH
  antenna 1) + ~11 needs-human (Langmuir current/flux cluster, neutral_pressure,
  line_of_sight) + 5 genuine human decisions (B.5) each with a recommended default.
- **`mechanical_measurement_diagnostics` shrinks 52 → ~11** (only the
  `operational_instrumentation` strain-gauge/displacement/sensor-mount set is
  genuinely mechanical).
- **Mechanism blocker:** no `sn edit --domain`; apply via reviewed Cypher SET +
  ISNC re-export (option 1), or add a `sn reclassify` command (option 2).
