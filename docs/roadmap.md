# Roadmap

Status: living document (updated 2025-09-04)

This roadmap translates current design decisions (uniform vector/component
grammar, frames, operators, validation) into phased deliverables. Each phase
has clear acceptance criteria and exit signals. Checklist items use GitHub
style `[ ]` / `[x]` for quick visual scanning.

## Vision

Establish a rigorously validated, machine-parseable catalog of fusion data
standard names (scalars + vectors + derived quantities) enabling:

- Deterministic semantic parsing of dataset variable names.
- Automated consistency validation (units, rank transitions, dependencies).
- Extensible transformation graph (operators) and coordinate frames.
- Sustainable governance workflow (issue → review → batch release).

## Guiding Principles

1. Uniformity over convenience (single component grammar).
2. Atomic scalars; vectors aggregate semantics only.
3. Left-to-right operator chains (parseable without recursion lookahead).
4. Explicit rank semantics enforced in tooling.
5. Incremental adoption: ship thin vertical slices early.

## Phase Overview

| Phase | Goal                           | Key Deliverables                                            | Status | Exit Criteria                          |
| ----- | ------------------------------ | ----------------------------------------------------------- | ------ | -------------------------------------- |
| 0     | Structure Seed                 | spec + quickstart + roadmap + validator stub                | [x]    | Docs merged; stub validator runs clean |
| 1     | Equilibrium Core Set           | `magnetic_field` + equilibrium geometry + diagnostics frame | [ ]    | Core attribute set & maps validated    |
| 2     | Operator Semantics             | Operator registry, rank-check validator extension           | [ ]    | Invalid chains rejected (tests)        |
| 3     | Frame Registry                 | `frames/` YAML schema + axis validation                     | [ ]    | Components rejected if axis undeclared |
| 4     | Derived Graph                  | Dependency closure + cycle detection in validator           | [ ]    | Cycles produce failing test            |
| 5     | CLI & CI Integration           | `validate_catalog` in pre-commit + CI gate                  | [ ]    | PR fails on violation                  |
| 6     | Documentation Hardening        | Naming cheat sheet, FAQ, examples gallery                   | [ ]    | Docs coverage: >90% key concepts       |
| 7     | Governance/Metadata            | Lifecycle states (draft, active, deprecated) + alias policy | [ ]    | Deprecation test & docs                |
| 8     | Tensor / Higher Rank (Stretch) | Draft tensor grammar & pilot entries                        | [ ]    | Prototype passes validator             |
| 9     | Transformation Introspection   | Programmatic operator expansion API                         | [ ]    | API returns chain metadata             |

## Detailed Milestones

### Phase 1 – Equilibrium Core Attribute Set

Objective: Capture the minimal but representative attribute surface required for
magnetics-based equilibrium reconstruction (no plasma velocity yet). This seeds
the catalog with vectors, geometry, coil & diagnostic scalars, and field/flux maps.

Checklist:

- [ ] Add `frames/cylindrical_r_tor_z.yml` (3 axes, right-handed).
- [ ] Add `standard_names/magnetic_field/` YAML set (components + magnitude + curl if practical).
- [ ] Add coil current & geometry scalars (see list below).
- [ ] Add magnetic diagnostics (probe + flux loop) position/value scalars.
- [ ] Add first wall and plasma boundary outline coordinate sets.
- [ ] Add magnetic axis position scalars.
- [ ] Add poloidal flux map + magnetic field component maps (grid semantics documented).
- [ ] Add basic boundary shape scalars (elongation, triangularity, area, volume).
- [ ] Unit normalization check (T, Wb, A, m, m^2, m^3, dimensionless shape factors).
- [ ] Document MCP extraction usage in spec/README (ensure done—see README update).
- [ ] Validator: tolerate map/grid arrays (no rank check yet) but enforce naming grammar.

Acceptance: Validator returns 0 with all Phase 1 names present; sample MCP extraction script generates at least 80% of listed attributes from IMAS DD metadata.

#### Phase 1 Target Attribute List (Concise)

| Category           | Attributes (proposed standard names / patterns)                                                                                                                                                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Magnetic Coils     | `pf_coil_<n>_current`, `pf_coil_<n>_center_radial_position`, `pf_coil_<n>_center_vertical_position`, `pf_coil_<n>_center_toroidal_angle` (optional), `pf_coil_<n>_effective_area` (optional)                                                                                         |
| Magnetic Probes    | `magnetic_probe_<id>_radial_position`, `magnetic_probe_<id>_vertical_position`, `magnetic_probe_<id>_toroidal_angle`, `magnetic_probe_<id>_normal_field`, `magnetic_probe_<id>_tangential_field`                                                                                     |
| Flux Loops         | `flux_loop_<id>_radial_position`, `flux_loop_<id>_vertical_position`, `flux_loop_<id>_toroidal_angle` (if needed), `flux_loop_<id>_poloidal_flux`                                                                                                                                    |
| Field / Flux Maps  | `radial_component_of_magnetic_field` (gridded), `vertical_component_of_magnetic_field`, `toroidal_component_of_magnetic_field`, `magnetic_field_magnitude`, `poloidal_flux`                                                                                                          |
| Axis & Geometry    | `magnetic_axis_radial_position`, `magnetic_axis_vertical_position`, `plasma_elongation`, `plasma_triangularity_upper`, `plasma_triangularity_lower`, `plasma_cross_section_area`, `plasma_volume`                                                                                    |
| Boundaries / Walls | `plasma_boundary_outline_radial_coordinates`, `plasma_boundary_outline_vertical_coordinates`, `first_wall_outline_radial_coordinates`, `first_wall_outline_vertical_coordinates`, `separatrix_outline_radial_coordinates` (if applicable), `separatrix_outline_vertical_coordinates` |

Notes:

- Coordinate arrays (e.g. `*_outline_radial_coordinates`) will migrate to geometry container conventions in later phases; Phase 1 treats them as canonical array variables.
- Map variables (field/flux) supply grid axes separately (not enumerated here) — grid axis naming policy slated for later phase.
- Coil / probe / loop `<id>` realisation strategy: numeric indices (zero-padded optional) or facility-specific labels; enforce lowercase.

Out of Scope for Phase 1:

- Plasma velocity (moved to future physical dynamics phase).
- Normalized or derived higher-order operators beyond curl/divergence.
- Tensor stresses or pressure anisotropy.

MCP Extraction Guidance (summary; full text placed early in specification/README): Use the configured `imas` MCP server (see `.vscode/mcp.json`) to query the IMAS Data Dictionary for existing coil, probe, loop, and equilibrium data to seed YAML drafts automatically.

### Phase 2 – Operator Semantics

Checklist:

- [ ] `operators/operators.yml` with rank in/out + scalarizing flag.
- [ ] Extend validator: parse operator chains, compute rank transitions.
- [ ] Add tests for allowed vs disallowed chains.
- [ ] Reject invalid: `curl_of_divergence_of_*`.

Acceptance: Invalid chain test fails pre-change, passes post-change.

### Phase 3 – Frame Registry

Checklist:

- [ ] Frame YAML schema (frame id, axes[], handedness, dimension).
- [ ] Validator loads frames before vector validation.
- [ ] Components referencing undefined axis produce error.
- [ ] Add alternative frame (e.g. `cartesian_xyz`).

Acceptance: Intentional bad axis triggers a single, clear validator error.

### Phase 4 – Derived Graph Validation

Checklist:

- [ ] Build dependency graph from `derivation.dependencies`.
- [ ] Detect cycles; output condensed cycle path.
- [ ] Ensure magnitude lists every base component exactly once.
- [ ] Add unit propagation sanity hooks (optional warning phase).

Acceptance: Introduced artificial cycle fails test; removing it passes.

### Phase 5 – CLI & CI Integration

Checklist:

- [ ] Add `scripts.py` entry `validate_catalog` calling validator.
- [ ] Pre-commit hook invoking validator.
- [ ] CI job blocking merge on validation failure.
- [ ] Short README section: “Validation & CI”.

Acceptance: Broken component pattern in PR fails CI automatically.

### Phase 6 – Documentation Hardening

Checklist:

- [ ] `docs/naming-cheatsheet.md` with high-density examples.
- [ ] `docs/faq.md` addressing common edge cases.
- [ ] Embedded diagrams (operator chain → rank transitions).
- [ ] Cross-links: quickstart ↔ spec ↔ roadmap.

Acceptance: Manual doc audit—no TODO markers left in core pages.

### Phase 7 – Governance & Lifecycle

Checklist:

- [ ] Add `lifecycle` field (draft|active|deprecated|superseded).
- [ ] Alias mechanism (`aliases:` list) with validator uniqueness check.
- [ ] Deprecation test: deprecated references warn; superseded requires replacement pointer.
- [ ] Documentation: deprecation migration path.

Acceptance: Sample deprecated entry triggers expected warning classification.

### Phase 8 – Tensor / Higher Rank (Stretch)

Checklist:

- [ ] Draft grammar additions (`kind: tensor`).
- [ ] Pilot tensor (e.g. `stress_tensor`) + components.
- [ ] Validator ensures index ordering & symmetry metadata (if provided).

Acceptance: Prototype passes; invalid permutation flagged.

### Phase 9 – Transformation Introspection

Checklist:

- [ ] Provide API to expand derived name → operator chain structure.
- [ ] Expose via Python function (e.g. `resolve_chain(name)`).
- [ ] Unit tests for chain resolution edge cases.

Acceptance: `resolve_chain("time_derivative_of_curl_of_magnetic_field")` returns ordered list of operator dicts.

## Backlog (Unscoped)

- Normalized variants with explicit denominator references.
- Unit dimensional analysis for composite derivations.
- Multi-language doc generation (internationalization).
- JSON schema export for external tooling.
- Web UI preview of vector/component graphs.

## Technical Debt / Cleanup Targets

| Item                                | Rationale                   | Planned Phase |
| ----------------------------------- | --------------------------- | ------------- |
| Markdown lint tolerances            | Reduce distraction noise    | 6             |
| Spec wording normalization          | Consistency across examples | 6             |
| Validator performance (batch parse) | Scale to 10k names          | 5             |

## Risks & Mitigations

| Risk                                | Impact                      | Mitigation                                               |
| ----------------------------------- | --------------------------- | -------------------------------------------------------- |
| Scope creep (tensor early)          | Delays vector stabilization | Keep tensor in stretch phase 8                           |
| Inconsistent operator chain parsing | Invalid catalogs in wild    | Central operator registry + tests (Phase 2)              |
| Axis naming drift across domains    | Ambiguous components        | Frame-enforced axis registry (Phase 3)                   |
| Unvalidated derivation expressions  | Silent math errors          | Dependency + cycle checks first; expression parser later |

## Success Metrics

| Metric                           | Target (after Phase 6)                     |
| -------------------------------- | ------------------------------------------ |
| Validator runtime                | < 2s for 2k entries on laptop              |
| CI failure clarity               | Single-line per violation (no stack flood) |
| Doc task completion (user study) | < 5 min to add new vector w/ curl          |
| Issue to merge (median)          | < 7 days post-Phase 7                      |

## Current Focus

Entering Phase 1: implement frames and first two vectors; extend validator accordingly.

---

End of roadmap.
