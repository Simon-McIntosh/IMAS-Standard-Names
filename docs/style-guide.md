# Standard Names Style Guide

Status: draft (initial) – complements the formal grammar in `specification.md`.

Purpose: Provide concise, actionable rules for authors proposing new standard
names (scalars, vectors, geometry, diagnostics) and writing supporting YAML
metadata.

Use the IMAS MCP server (configured in `.vscode/mcp.json` under id `imas`) to
harvest existing IMAS Data Dictionary information before drafting new names. Align proposals with real data.

---

## 1. Core Principles (Recap)

1. Uniform component pattern: `<axis>_component_of_<vector_expression>`.
2. Left-to-right operator chains: `time_derivative_of_curl_of_magnetic_field`.
3. Scalars are atomic; vectors aggregate semantics only.
4. One canonical spelling (aliases only for deprecation migration).
5. Deterministic parsing > brevity.

---

## 2. Lexical Rules

| Rule          | Requirement                                                                                                                            |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Characters    | Lowercase a–z, digits 0–9, underscores.                                                                                                |
| Start         | Must begin with a letter.                                                                                                              |
| No            | Double underscores (`__`), trailing underscore, camelCase, hyphens.                                                                    |
| Pluralization | Use singular unless the concept is inherently plural (`coefficients` rarely justified – prefer specific noun like `spectral_density`). |
| Abbreviations | Avoid unless universally canonical (e.g. `pf` for poloidal field coil if documented). Prefer full words first time in domain.          |
| Numbers       | Use plain digits without zero padding unless ordering benefits.                                                                        |

Reserved tokens (internal meaning – do not repurpose): `component`, `of`, `time_derivative`, `curl`, `divergence`, `gradient`, `laplacian`, `normalized`, `magnitude`, `derivative_with_respect_to`.

---

## 3. Scalar Naming

| Category           | Guidance                                                         | Example                                   |
| ------------------ | ---------------------------------------------------------------- | ----------------------------------------- |
| Base physical      | Direct phenomenon noun(s)                                        | `electron_temperature`                    |
| Time derivative    | Prefix chain                                                     | `time_derivative_of_electron_temperature` |
| Gradient (vector)  | Use derived vector rules (produces vector + components)          | `gradient_of_electron_temperature`        |
| Scalar from vector | Use scalarizing operator OR canonical magnitude prefix           | `divergence_of_magnetic_field`            |
| Magnitude (scalar) | ALWAYS `magnitude_of_<vector_expression>` (canonical; no suffix) | `magnitude_of_magnetic_field`             |
| No frame terms     | Omit coordinate hints (unless intrinsic landmark like axis)      | (avoid) `electron_temperature_radial`     |

Canonical Magnitude Policy: The legacy suffix form `<vector>_magnitude` is deprecated. New entries MUST adopt `magnitude_of_<vector_expression>`; tooling will flag suffix usage (DRP001).

Anti-patterns: `electron_temperature_time_derivative` (suffix derivative), `magnetic_field_magnitude` (legacy magnitude suffix), `gradient_of_electron_temperature_radial_component` (rank misuse).

---

## 4. Vector Naming

| Aspect              | Rule                                            | Example                              |
| ------------------- | ----------------------------------------------- | ------------------------------------ |
| Base vector         | Single descriptive phrase                       | `magnetic_field`                     |
| Derived vector      | `<operator>_of_<vector_expression>`             | `curl_of_magnetic_field`             |
| Components          | `<axis>_component_of_<vector_expression>`       | `radial_component_of_magnetic_field` |
| Magnitude scalar    | Scalar name: `magnitude_of_<vector_expression>` | `magnitude_of_magnetic_field`        |
| No container suffix | Never append `_vector`                          | (avoid) `magnetic_field_vector`      |
| Axis list           | Must exist in frame YAML                        | `cylindrical_r_tor_z`                |

Allowed canonical axes (Phase 1): `radial`, `toroidal`, `vertical` (others reserved until frame registry expands).

---

## 5. Operator Chain Construction

1. Compose strictly left-to-right: outermost operation first.
2. Stop after scalarizing operator if output is scalar.
3. Disallow vector operator after scalarizing operator (e.g. `curl_of_divergence_of_*`).
4. Use `derivative_with_respect_to_<coord>` for explicit coordinate derivatives (future validator will confirm coordinate variable existence).

Examples:
Good | Reason
---- | ------
`time_derivative_of_curl_of_magnetic_field` | Vector→vector→vector chain
`divergence_of_time_derivative_of_magnetic_field` | Chain ends in scalar
Bad | Issue
--- | -----
`curl_of_divergence_of_magnetic_field` | Curl after scalar
`magnitude_of_magnetic_field_magnitude` | Double magnitude

---

## 6. Equilibrium Reconstruction (Phase 1) Style

| Element               | Style Rule                                                                                                   | Example                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------- | -------------------------------------------- |
| Coil current          | `pf_coil_<id>_current` (ampere)                                                                              | `pf_coil_1_current`                       |
| Coil position         | Add coordinate token: `_radial_position`, `_vertical_position`, `_toroidal_angle`                            | `pf_coil_1_radial_position`               |
| Probe field component | Use physical orientation nouns: `_normal_field`, `_tangential_field` (no instrument number in standard name) | `magnetic_probe_normal_field`             |
| Probe position        | Same coordinate suffix set as coils (avoid embedding numeric ids)                                            | `magnetic_probe_vertical_position`        |
| Flux loop flux        | `_poloidal_flux`                                                                                             | `flux_loop_5_poloidal_flux`               |
| Axis position         | `magnetic_axis_radial_position`, `magnetic_axis_vertical_position`                                           | (both)                                    |
| Boundary outlines     | `<structure>_outline_<radial                                                                                 | vertical>\_coordinates`                   | `plasma_boundary_outline_radial_coordinates` |
| Wall outlines         | Same pattern with `first_wall`                                                                               | `first_wall_outline_vertical_coordinates` |
| Maps                  | Use quantity base name (unqualified) – grid metadata external                                                | `poloidal_flux`                           |

Notes:

- Indices `<id>` should be numeric unless a facility-specific code name adds value (document if used).
- Outline arrays will later be wrapped by geometry containers; keep names stable.

---

## 7. Geometry & Coordinate Arrays

Until geometry container metadata is formalized, coordinate arrays follow:
`<object>_outline_<axis>_coordinates` with plural noun `coordinates`.
Axis tokens MUST be consistent across both radial & vertical arrays for the same outline.

Future container fields (preview): `geometry_type`, `node_coordinates`, `part_node_count` (do not embed those in names).

---

## 8. Units Formatting

| Aspect             | Rule                                                                 | Example            |
| ------------------ | -------------------------------------------------------------------- | ------------------ |
| Base units         | SI symbols                                                           | `T`, `A`, `m`      |
| Compound           | Use `.` for multiplication, `^` for powers or implicit `-1` exponent | `T.m^-1`           |
| Per units          | Negative exponent (avoid slash chaining)                             | `s^-1` (not `1/s`) |
| Dimensionless      | Leave blank or use `1` (consistent)                                  | `1`                |
| Magnitude inherits | Same as vector components                                            | `T`                |

Later unit validation will parse via Pint; keep forms Pint-friendly.

---

## 9. Descriptions

Keep concise ( ≤ 120 chars ). Begin with capital, no trailing period if fragment; include period if full sentence.
Include:

1. Core physical meaning.
2. If derived, the operator chain succinctly ("Curl of magnetic_field.").
3. For components: axis first ("Radial component of magnetic_field.").

Avoid repetition of the name itself beyond meaningful grammar.

---

## 10. YAML Field Guidelines

| Field              | Requirement                                            | Example                                      |
| ------------------ | ------------------------------------------------------ | -------------------------------------------- | ---------- | ------------------------------- | ----- |
| `name`             | Matches grammar exactly                                | `radial_component_of_magnetic_field`         |
| `kind`             | One of scalar, derived_scalar, vector, derived_vector  | `vector`                                     |
| `frame`            | Required for vectors / derived vectors                 | `cylindrical_r_tor_z`                        |
| `components`       | Mapping axis→component for vectors                     | `radial: radial_component_of_magnetic_field` |
| `magnitude`        | Scalar magnitude name (optional but recommended)       | `magnetic_field_magnitude`                   |
| `parent_vector`    | Component backlink                                     | `magnetic_field`                             |
| `parent_operation` | For derived vectors/scalars (operator, operand_vector) | operator: curl                               |
| `derivation`       | Expression + dependencies for computed scalars         | expression: sqrt(...)                        |
| `dependencies`     | Complete list of required scalar names                 | list of component names                      |
| `unit`             | SI-consistent                                          | `T`                                          |
| `status`           | draft                                                  | active                                       | deprecated | superseded (future enforcement) | draft |

---

## 11. Submission Checklist

Before submitting an issue / PR:

- Name conforms to grammar (run validator).
- Vector has ≥2 components and magnitude defined (if sensible).
- Component files exist for each axis and backlink correctly.
- Derivation dependencies complete and free of cycles (manual check until Phase 4).
- Units consistent with physical dimension.
- Description concise and informative.
- No reserved tokens misused.
- Phase alignment: If equilibrium attribute, matches Phase 1 patterns.

---

## 12. Anti-Pattern Matrix

| Bad                                                 | Problem                                        | Correct                                                |
| --------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------ |
| `magnetic_field_radial_component`                   | Reversed component order                       | `radial_component_of_magnetic_field`                   |
| `curl_of_divergence_of_magnetic_field`              | Curl after scalar                              | (remove curl) or pick different chain                  |
| `magnetic_field_magnitude`                          | Legacy magnitude suffix (deprecated)           | `magnitude_of_magnetic_field`                          |
| `electron_temperature_time_derivative`              | Suffix derivative                              | `time_derivative_of_electron_temperature`              |
| `gradient_of_electron_temperature_radial_component` | Gradient rank misuse                           | `radial_component_of_gradient_of_electron_temperature` |
| `pf_coil_current_1`                                 | Misplaced index                                | `pf_coil_1_current`                                    |
| `first_wall_vertical_coordinates`                   | Missing outline token                          | `first_wall_outline_vertical_coordinates`              |
| `magnetic_probe_23_normal_field`                    | Hard-coded instrument index (violates DIAG001) | `magnetic_probe_normal_field`                          |

---

## 13. Reserved / Planned Extensions

| Area                | Future Plan                                              |
| ------------------- | -------------------------------------------------------- |
| Geometry containers | Introduce metadata-only variable linking outlines.       |
| Tensor quantities   | `kind: tensor` with index metadata & symmetry.           |
| Lifecycle           | Enforce status transitions + alias deprecation warnings. |
| Operator registry   | Machine-readable rank & composition legality.            |
| Grid axes           | Standard names / attributes for 2D/3D analytical grids.  |

---

## 14. Quick Reference (Copy Block)

```
Vector pattern: <vector>
Component: <axis>_component_of_<vector_expression>
Derived vector: <operator>_of_<vector_expression>
Magnitude (canonical): magnitude_of_<vector_expression>
Time derivative: time_derivative_of_<target>
Axis tokens (Phase 1): radial, toroidal, vertical
Outline coordinates: <object>_outline_<axis>_coordinates
Coil current: pf_coil_<id>_current
Probe field: magnetic_probe_<normal|tangential>_field (do not encode instrument index)
Flux loop flux: flux_loop_<id>_poloidal_flux
Magnetic axis: magnetic_axis_<radial|vertical>_position
```

---

End of style guide.
