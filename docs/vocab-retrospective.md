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
