# IMAS Standard Names Specification (Vector & Component Uniform Grammar)

Status: draft (initial skeleton)

This document defines the canonical naming grammar, roles, and validation
invariants for the emerging vector‑aware standard names catalog. Sections
marked (TBD) can evolve after initial vectors land.

---

## 1. Overview

We adopt an _absolute uniform_ component naming pattern and encourage using the
IMAS MCP server (configured in `.vscode/mcp.json`) to mine existing IMAS Data
Dictionary content when drafting new equilibrium or diagnostics-related names.

Component pattern:

```text
<axis>_component_of_<vector_expression>
```

where `<vector_expression>` may itself include a left‑to‑right chain of
operators (e.g. `time_derivative_of_curl_of_magnetic_field`). Every base or
derived vector has:

- A vector standard name (e.g. `magnetic_field`).
- A set of component scalar standard names (e.g. `radial_component_of_magnetic_field`).
- Optional derived scalar names (e.g. `magnetic_field_magnitude`, `divergence_of_magnetic_field`).
- Optional derived vectors (e.g. `curl_of_magnetic_field`).

Vectors group semantics; components remain atomic scalars.

---

## 2. Design Principles

| Principle                 | Rationale                                                          |
| ------------------------- | ------------------------------------------------------------------ |
| Uniformity                | Single component pattern eliminates ambiguity.                     |
| Atomicity                 | Scalars carry direct numeric semantics; vectors reference them.    |
| Deterministic Parsing     | Names are machine decomposed with simple regex + operator table.   |
| Rank Safety               | Operators have explicit input/output ranks (vector → scalar etc.). |
| Left‑to‑Right Composition | Outermost operation first: `time_derivative_of_curl_of_B`.         |
| No Silent Aliases         | One canonical form per concept (aliases permitted for migration).  |

---

## 3. Terminology & Kinds

| Kind             | Meaning                                                                    |
| ---------------- | -------------------------------------------------------------------------- |
| `scalar`         | Atomic physical scalar or base component.                                  |
| `derived_scalar` | Scalar produced by an operator chain (e.g. magnitude, divergence).         |
| `vector`         | Base multi‑component quantity (e.g. `magnetic_field`).                     |
| `derived_vector` | Vector produced by applying operators (e.g. `curl_of_magnetic_field`).     |
| `frame`          | Structural definition of axes (external file in `frames/`).                |
| `operator`       | Transformation with rank signature (defined in `operators/operators.yml`). |

---

## 4. Naming Grammar (EBNF)

Condensed from the detailed discussion; see `docs/naming-cheatsheet.md` (future).

```ebnf
<standard_name> ::= <vector_name>
                  | <component_name>
                  | <derived_scalar_name>
                  | <derived_vector_name>

<vector_name> ::= <base_quantity>
<base_quantity> ::= <word> ("_" <word> )*
<word> ::= [a-z][a-z0-9]*

<axis> ::= radial|toroidal|vertical|poloidal|parallel|perpendicular1|perpendicular2|x|y|z|<custom_axis>
<custom_axis> ::= <word>

<component_name> ::= <axis> "_component_of_" <vector_expression>

<vector_expression> ::= <vector_name>
                      | <operator_chain> "_of_" <vector_name>

<operator_chain> ::= <operator_invocation>
                   | <operator_invocation> "_of_" <operator_chain>

<operator_invocation> ::= curl|divergence|time_derivative|gradient|laplacian|normalized|magnitude
                        | derivative_with_respect_to_{coord}
                        | derivative  ; (generic; disfavoured unless qualified)

; Vector results exclude scalarizing terminals at the tail.
<derived_vector_name> ::= <vector_producing_chain> "_of_" <vector_name>
                        | <vector_producing_chain> "_of_" <derived_vector_name>
<vector_producing_chain> ::= (curl|time_derivative|gradient|laplacian|normalized|derivative_with_respect_to_{coord}|derivative)
                           | (curl|time_derivative|gradient|laplacian|normalized|derivative_with_respect_to_{coord}|derivative) "_of_" <vector_producing_chain>

<derived_scalar_name> ::= <scalarizing_chain> "_of_" <vector_name>
                        | <scalarizing_chain> "_of_" <derived_vector_name>
                        | <vector_name> "_magnitude"
                        | <vector_name> "_" <subset> "_magnitude"

<scalarizing_chain> ::= (divergence|magnitude|curl_magnitude|normalized_magnitude)
                      | (divergence|magnitude|curl_magnitude|normalized_magnitude) "_of_" <vector_producing_chain>

<subset> ::= poloidal|toroidal|radial|parallel|perpendicular1|perpendicular2|x|y|z|<word>
```

Enforce semantic rank rules (Section 6); grammar alone is insufficient.

---

## 5. Operator Rank Semantics

| Operator                           | Input Rank    | Output Rank | Components? | Notes                                |
| ---------------------------------- | ------------- | ----------- | ----------- | ------------------------------------ |
| curl                               | vector        | vector      | yes         | 3D frames only.                      |
| divergence                         | vector        | scalar      | no          | No components.                       |
| time_derivative                    | scalar/vector | same        | yes         | Chainable.                           |
| gradient                           | scalar        | vector      | yes         | If input not scalar → invalid.       |
| laplacian                          | scalar        | scalar      | no          | On vector → vector (component‑wise). |
| normalized                         | vector        | vector      | yes         | Requires nonzero magnitude.          |
| magnitude                          | vector        | scalar      | no          | Appears at tail.                     |
| derivative*with_respect_to*{coord} | any           | same        | yes         | {coord} from dataset.                |

Disallowed chains: e.g. `curl_of_divergence_of_...` (scalar → curl invalid).

---

## 6. Validation Invariants

| Code name (for tooling) | Rule                                                                 |
| ----------------------- | -------------------------------------------------------------------- |
| VEC001                  | A vector file must list >=2 distinct axes.                           |
| VEC002                  | All component names referenced exist & backlink via `parent_vector`. |
| VEC003                  | Each component follows uniform pattern `<axis>_component_of_...`.    |
| OPR001                  | Operator chain obeys rank transitions.                               |
| OPR002                  | Scalarizing operator cannot precede a vector‑producing operator.     |
| MAG001                  | `<vector>_magnitude` depends on every base component once.           |
| SUB001                  | `<subset>_magnitude` subset ⊆ frame axes.                            |
| AXS001                  | Axis tokens must appear in frame file.                               |
| DRP001                  | No legacy suffix pattern detected.                                   |

---

## 7. Authoring Workflow (Summary)

1. Define / reuse frame (see `frames/`).
2. Create vector file with axes + magnitude field (recommended).
3. Create one component file per axis (uniform pattern).
4. Add derived vectors (curl etc.) + their component sets.
5. Add derived scalars (divergence, magnitude if not already).
6. Run validator: `python tools/validate_catalog.py`.
7. Commit on green.

Extended quick start: see `quickstart.md`.

---

## 8. Anti‑Patterns

| Invalid                                   | Reason                        | Correct                                      |
| ----------------------------------------- | ----------------------------- | -------------------------------------------- |
| `magnetic_field_radial_component`         | Legacy suffix style           | `radial_component_of_magnetic_field`         |
| `curl_of_magnetic_field_radial_component` | Ambiguous (curl of scalar)    | `radial_component_of_curl_of_magnetic_field` |
| `gradient_of_magnetic_field`              | Gradient needs scalar operand | (none) or `gradient_of_electron_temperature` |
| `magnitude_of_magnetic_field_magnitude`   | Double magnitude              | `magnetic_field_magnitude`                   |

---

## 9. Future Extensions (TBD)

- Tensor ranks (`kind: tensor` with index list).
- Frame transformations & alias vectors.
- Normalized variants with explicit dependency tracking.

---

## 10. Appendix: Quick Regex Hints

Below are illustrative (not normative) patterns. Escape and extend as needed.

- Component:
  - `^(radial|toroidal|vertical|poloidal|parallel|perpendicular1|perpendicular2|x|y|z)_component_of_[a-z0-9_]+(_of_[a-z0-9_]+)*$`
- Vector:
  - `^[a-z][a-z0-9_]*$`
- Derived Vector:
  - `^(curl|time_derivative|laplacian|normalized|derivative_with_respect_to_[a-z0-9_]+|derivative)_of_[a-z0-9_]+(_of_[a-z0-9_]+)*$`
- Magnitude:
  - `^[a-z0-9_]+_magnitude$`
- Scalarizing Op:
  - `^(divergence|magnitude|curl_magnitude|normalized_magnitude)_of_.*$`

Always combine regex checks with semantic rank validation.

---

End of initial specification skeleton.

## 11. Scalar Standard Names (Author Guidance)

While much of this specification emphasizes vectors (to pin down the
uniform component grammar), the majority of entries will remain plain
scalars. This section provides explicit scalar guidelines.

### 11.1 Base Scalars

Pattern: `<descriptive_terms>` (lowercase, underscores). Avoid:

- Frame or coordinate hints (put those in metadata or dataset coordinates).
- Acquisition method (prefer a future `method` tag or link).
- Redundant words like `value`, `data`, `measurement`.

Examples:

- `electron_temperature`
- `ion_density`
- `total_radiated_power`

### 11.2 Derived Scalars from Scalars

Apply operator prefix chain: `time_derivative_of_`, `laplacian_of_`, etc.
Example: `time_derivative_of_electron_temperature`.

### 11.3 Derived Scalars from Vectors

Scalarizing operators over vectors: `divergence_of_<vector_expression>`,
`magnitude_of_<vector_expression>` (canonical form `<vector_expression>_magnitude`).
We prefer the suffix form `_magnitude` ONLY for the final tail; no `magnitude_of_` prefix variant is added.

### 11.4 Gradients

`gradient_of_<scalar>` is a vector (kind: derived*vector). Do not create a
scalar `gradient_of*\*` entry; instead generate its components.

### 11.5 Time Derivatives

Always prefix: `time_derivative_of_<name>`; chainable with other operators:
`time_derivative_of_divergence_of_plasma_velocity`.

### 11.6 Anti‑Patterns (Scalars)

| Invalid                                             | Reason                                      | Correct                                                |
| --------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------ |
| `electron_temperature_time_derivative`              | Suffix style conflicts with uniform grammar | `time_derivative_of_electron_temperature`              |
| `magnitude_of_magnetic_field`                       | Non-canonical magnitude form                | `magnetic_field_magnitude`                             |
| `gradient_of_electron_temperature_radial_component` | Gradient raises rank (vector)               | `radial_component_of_gradient_of_electron_temperature` |

### 11.7 Minimal YAML Templates

Base scalar:

```yaml
name: electron_temperature
kind: scalar
unit: keV
description: Electron temperature.
status: draft
```

Derived scalar (time derivative):

```yaml
name: time_derivative_of_electron_temperature
kind: derived_scalar
unit: keV.s^-1
derivation:
    operator_chain:
        - operator: time_derivative
            operand: electron_temperature
dependencies:
    - electron_temperature
status: draft
```

Derived scalar (divergence of vector):

```yaml
name: divergence_of_plasma_velocity
kind: derived_scalar
unit: s^-1
parent_operation:
  operator: divergence
  operand_vector: plasma_velocity
dependencies:
  - radial_component_of_plasma_velocity
  - toroidal_component_of_plasma_velocity
  - vertical_component_of_plasma_velocity
status: draft
```

### 11.8 Validation Hooks (Scalars)

Future validator extensions will ensure:

- Derived scalar dependency closure.
- No misuse of `gradient_of_` as scalar.
- Consistent unit transformations where operator implies dimensions.

---
