# Vocabulary Token Retrospective

Ongoing record of vocab gap triage runs.  Each section corresponds to a
pilot / release cycle.  Evidence counts (N) are the number of distinct
IMAS DD paths that required the token for standard-name composition as
recorded by imas-codex VocabGap nodes.

---

## EMW Pilot (rc27 candidates)

Source: imas-codex tier-a-pilot run `2026-04-24` on `electromagnetic_wave_diagnostics`.
Paths processed: 340, Names composed: 272, Vocab gaps identified: 32.

Evidence gate: N ≥ 3 distinct IMAS DD paths required to add a token.

### Added at rc27 (N≥3 evidence)

| Token | Segment | Vocab file | Evidence N | Example refs |
|-------|---------|------------|-----------|--------------|
| `diagnostic_latency` | base → physical_base | `physical_bases.yml` | 4 | `refractometer/latency`, `reflectometer_fluctuation/latency`, `reflectometer_profile/latency`, `ece/latency` |
| `sweep_duration` | base → physical_base | `physical_bases.yml` | 3 | `reflectometer_profile/channel/sweep_time`, `refractometer/channel/sweep_time`, `reflectometer_fluctuation/channel/sweep_time` |
| `x1_coordinate` | base → geometry_carrier | `geometry_carriers.yml` | 3 | `reflectometer_fluctuation/channel/antenna_detection_static/outline/x1`, `reflectometer_profile/channel/antenna_detection/outline/x1` |
| `x2_coordinate` | base → geometry_carrier | `geometry_carriers.yml` | 3 | `reflectometer_fluctuation/channel/antenna_detection_static/outline/x2`, `reflectometer_profile/channel/antenna_detection/outline/x2` |
| `x1_width` | base → physical_base | `physical_bases.yml` | 3 | `reflectometer_fluctuation/channel/antenna_detection_static/x1_width`, `reflectometer_profile/channel/antenna_detection/x1_width` |

### Deferred (N<3 evidence)

Re-evaluate after Tier B pilot adds more electromagnetic-wave diagnostics coverage.

| Token | Segment | Evidence N | Reason |
|-------|---------|-----------|--------|
| `variation_flag` | base | 2 | insufficient evidence at rc27; re-evaluate after Tier B |
| `probing_frequency` | base | 2 | insufficient evidence at rc27; re-evaluate after Tier B |
| `time_window_duration` | base | 2 | insufficient evidence at rc27; re-evaluate after Tier B |
| `x2_width` | base | 2 | insufficient evidence at rc27; re-evaluate after Tier B |
| `calibration_factor` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `wave_vector_component` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `normalized_toroidal_flux_coordinate` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B (token already in geometry_carriers.yml — possible parser issue) |
| `fringe_jump_correction_time` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `analysis_time_window` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `bandwidth` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `frequency_axis` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `carrier_frequency` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `phase_ellipse_rotation_angle` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `beam_spot_ellipse_rotation_angle` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `emission_position_correction_toroidal_angle` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `emission_position_correction_poloidal_angle` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `probing_signal_phase` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `arc_length` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `beam_spot_size` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `unit_vector_component` | base | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `suprathermal_electron_position_correction` | locus | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `beam_path` | locus | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `ece_beam_position` | locus | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `launched` | operators | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `correction_to` | operators | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `x1_unit_vector` | position | 1 | insufficient evidence at rc27; re-evaluate after Tier B |
| `x2_unit_vector` | position | 1 | insufficient evidence at rc27; re-evaluate after Tier B |

### Pilot context notes

- **Q1 (`x/y/z_cartesian` spatial qualifiers):** The pilot flagged 9 names with
  cartesian-system coordinate tokens.  The graph evidence mapped these to
  `x1_coordinate` (N=3), `x2_coordinate` (N=3), and `x1_width` (N=3) — all from
  reflectometer antenna-grid geometry fields.  All three met the gate and were
  added.  `x2_width` reached only N=2 and is deferred.
- **Q2 (`wave_power_flow` dimensionless power, 2 names):** Unit-rules audit
  issue, not a vocab gap.  No token addition warranted.
- **Q3 (`fluctuation_power_spectrum` density-unit, 1 name):** Pattern exception,
  not a vocab gap.  No token addition warranted.
- **Q4 (`line_integrated` cumulative prefix, 1 name):** `operators` segment,
  N=1 — deferred (not captured directly in the gap nodes above; the
  `launched` and `correction_to` operator gaps were flagged instead).

---

## Rotation Waves W7 + W9A (rc28 candidates)

Source: imas-codex rotation waves 7 and 9A across domains:
`gyrokinetics`, `plasma_wall_interactions`, `particle_measurement_diagnostics`.
Waves accumulated 33 unique VocabGap tokens; 7 pre-existed in ISN; 2 explicitly
rejected by preposition policy; 5 qualified at N≥3.

Evidence gate: N ≥ 3 distinct IMAS DD paths required to add a token.
Evidence method: direct DD path count via `imas-codex` graph queries on
`IMASNode` paths matching each candidate token.

### Added (N≥3 evidence)

| Token | Segment | Vocab file | Evidence N | Example DD paths |
|-------|---------|------------|-----------|-----------------|
| `x2_width` | physical_base | `physical_bases.yml` | 43 | `bolometer/camera/channel/aperture/x2_width`, `bolometer/channel/detector/x2_width`, `camera_ir/fibre_bundle/geometry/x2_width`, `camera_visible/channel/aperture/x2_width`, `camera_x_rays/aperture/x2_width` |
| `gyroaveraged` | subject | `subjects.yml` | 15 | `gyrokinetics/wavevector/eigenmode/fluxes_moments/moments_norm_gyrocenter/density_gyroav`, `/heat_flux_parallel_gyroav`, `/j_parallel_gyroav`, `/pressure_parallel_gyroav`, `/pressure_perpendicular_gyroav` |
| `vessel_outline_point` | position | `locus_registry.yml` | 6 | `wall/description_2d/vessel/unit/annular/outline_inner/r`, `/outline_inner/z`, `/outline_outer/r`, `/outline_outer/z`, `/element/outline/r`, `/element/outline/z` |
| `focs_outline_point` | position | `locus_registry.yml` | 3 | `focs/outline/r`, `focs/outline/z`, `focs/outline/phi` |
| `limiter_outline_point` | position | `locus_registry.yml` | 3 | `wall/description_2d/limiter/unit/outline`, `/outline/r`, `/outline/z` |

### Already in ISN (no action required)

These tokens appeared in VocabGap nodes from old rotations before they were
added to ISN; they are confirmed present in `locus_registry.yml`:

`outboard_midplane`, `inner_divertor_target`, `outer_divertor_target`,
`divertor_target`, `constraint_position`, `current_center`,
`last_closed_flux_surface`

### Explicitly rejected

| Token | Reason |
|-------|--------|
| `from_wall` | Preposition-form token banned by compose grammar (`_from_/_to_` ban in `compose_system_lean.md`) |
| `from_plasma` | Same preposition-form ban |

### Deferred (N<3 evidence at this time)

| Token | Segment | N | Notes |
|-------|---------|---|-------|
| `diagnostic_component_center` | position | 0 | No specific DD paths found; re-evaluate after PWI coverage |
| `detector_aperture` | position | 0 | `diagnostic_aperture` entity already covers; may be redundant |
| `mobile_unit_outline_point` | position | 0 | Specific to mobile wall units; insufficient DD coverage |
| `shearing_rate` | base | 2 | `gyrokinetics/species_all/shearing_rate_norm` + `gyrokinetics_local` — only 2 paths |
| `spun_fiber` | position | 0 | FOCS spun-fiber properties are physical quantities, not position tokens |
| `annular` | coordinate_axes | 0 | 123 DD paths exist but segment assignment unclear; not a coordinate axis |
| `vertical_coordinate_of` | coordinate_axes | 0 | Not found in VocabGap graph; needs re-evaluation |
| `cartesian_x` | component | 0 | Not found in VocabGap graph; insufficient evidence |

### Note on `x1_width`

`x1_width` was already added at rc27 (EMW pilot). `x2_width` is the symmetric
counterpart (43 DD paths vs 3 for `x1_width`) and logically belongs alongside it.

