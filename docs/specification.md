# IMAS Standard Names Specification

Status: draft (initial skeleton)

This document defines the canonical naming grammar, roles, and validation
invariants for the emerging vector‑aware standard names catalog. Sections
marked (TBD) can evolve after initial vectors land.

---

## 1. Overview

This specification treats **scalars as the primary, atomic carriers of physical
meaning**. Almost every quantity (temperature, density, current, flux, axis
position, shape parameter, diagnostic reading) is a scalar standard name. Vector
standard names are a lightweight organizational layer that _group existing
scalar components_; they never replace or diminish scalar semantics.

You should first look for (or propose) scalar names. Introduce a vector name
only when you need to express a coherent multi‑component physical field (e.g.
`magnetic_field`) whose components already follow a consistent axis frame.

Use the IMAS MCP server (configured in `.vscode/mcp.json`) to mine existing IMAS
Data Dictionary content before proposing new scalar or vector names so the
catalog reflects deployed diagnostics and equilibrium reconstructions.

Section 2 establishes scalar naming rules. Section 3 then layers the uniform
vector/component system on top of those, including transformation (operator)
chains.

---

## 2. Scalar Standard Names

Scalar names represent a single physical quantity or its derived transformation
without embedding coordinate system, measurement method, or storage shape. Core
rules:

| Aspect          | Guidance                                                               | Example                                                       |
| --------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| Form            | Lowercase words separated by underscores                               | `electron_temperature`                                        |
| Clarity         | Prefer explicit words over opaque abbreviations                        | `ion_density`                                                 |
| No frame tokens | Omit axis names unless intrinsic                                       | `plasma_volume`                                               |
| Derivatives     | Prefix operator chain                                                  | `time_derivative_of_electron_temperature`                     |
| From vector     | Use scalarizing operator or canonical magnitude prefix `magnitude_of_` | `divergence_of_magnetic_field`, `magnitude_of_magnetic_field` |

Common scalar patterns:

- Physical state: `electron_temperature`, `ion_density`, `plasma_volume`.
- Diagnostic reading (generic physical quantity).
- Geometry / landmark: `magnetic_axis_radial_position`, `magnetic_axis_vertical_position`.
- Shape parameter: `plasma_elongation`, `plasma_triangularity_upper`.
- Flux / field map scalar: `poloidal_flux` (grid axes defined separately).

Scalar anti‑patterns:

| Invalid                                             | Issue                                     | Correct                                                |
| --------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------ |
| `electron_temperature_time_derivative`              | Suffix derivative form                    | `time_derivative_of_electron_temperature`              |
| `magnetic_field_magnitude`                          | Deprecated suffix magnitude form          | `magnitude_of_magnetic_field`                          |
| `gradient_of_electron_temperature_radial_component` | Gradient raises rank                      | `radial_component_of_gradient_of_electron_temperature` |
| `magnetic_probe_23_normal_field`                    | Embeds instrument index (device-specific) | `magnetic_probe_normal_field` (generic)                |

Gradients, curls, divergence, and similar operators may _raise_ or _lower_ rank.
When they yield scalars (e.g. divergence) they simply produce another scalar
name. When they yield vectors (e.g. gradient of a scalar), the resulting vector
and its components use the vector layer (next section) but the scalar inputs
remain the foundation.

For extended scalar guidance (templates, validation hooks) see Section 12 and
the `style-guide.md`.

See also `provenance.md` for the unified derivation / operator / reduction schema.

---

## 3. Vector & Component System (Layer on Scalars)

Vectors provide structured grouping of related scalar components plus optional
derived vectors and scalars. Every vector is defined strictly by its scalar
components; vectors do not introduce independent physical values.

Uniform component pattern:

```text
<axis>_component_of_<vector_expression>
```

`<vector_expression>` may include a left‑to‑right operator chain, e.g.
`time_derivative_of_curl_of_magnetic_field`.

Each (base or derived) vector entry supplies:

- Vector standard name (e.g. `magnetic_field`).
- Mapping axis → component scalar names (`radial_component_of_magnetic_field`, ...).
- Optional magnitude scalar (`magnitude_of_magnetic_field`).
- Optional derived vectors (`curl_of_magnetic_field`).

Vectors group semantics; components remain atomic scalars.

---

## 4. Design Principles

| Principle                 | Rationale                                                          |
| ------------------------- | ------------------------------------------------------------------ |
| Uniformity                | Single component pattern eliminates ambiguity.                     |
| Atomicity                 | Scalars carry direct numeric semantics; vectors reference them.    |
| Deterministic Parsing     | Names are machine decomposed with simple regex + operator table.   |
| Rank Safety               | Operators have explicit input/output ranks (vector → scalar etc.). |
| Left‑to‑Right Composition | Outermost operation first: `time_derivative_of_curl_of_B`.         |
| One Canonical Form        | Exactly one name per concept (no alternate alias field).           |

---

## 5. Terminology & Kinds

| Kind       | Meaning                                                                    |
| ---------- | -------------------------------------------------------------------------- |
| `scalar`   | Physical scalar quantity, including components and derived scalars.        |
| `vector`   | Multi‑component quantity (e.g. `magnetic_field`).                          |
| `operator` | Transformation with rank signature (defined in `operators/operators.yml`). |

Scalars may have optional provenance (operator, reduction, or expression) describing
their derivation. Vectors are specified using the `vector_axes` metadata attribute at
runtime to indicate axis labels (e.g., "radial toroidal vertical").

---

## 6. Naming Grammar (EBNF)

!!! info "Auto-Generated Vocabularies"
The vocabularies below are automatically generated from `grammar.yml` at build time.
For the complete grammar reference, see [Grammar Reference](grammar-reference.md).

**Current Vocabularies:**

### Components

{{ grammar_vocabulary_table('components') }}

### Subjects

{{ grammar_vocabulary_table('subjects') }}

### Positions

{{ grammar_vocabulary_table('positions') }}

### Processes

{{ grammar_vocabulary_table('processes') }}

---

Condensed from the detailed discussion; see `docs/naming-cheatsheet.md` (future).

```ebnf
<standard_name> ::= <vector_name>
                  | <component_name>
                  | <scalar_name>

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

<scalar_name> ::= <base_quantity>
                | <operator_chain> "_of_" <scalar_name>
                | <operator_chain> "_of_" <vector_expression>
                | "magnitude_of_" <vector_expression>
```

Authoritative grammar and code generation:

- The canonical grammar, segment order, and vocabularies are defined in `imas_standard_names/resources/grammar.yml`.
- The Python enums and segment metadata in `imas_standard_names/grammar/types.py` are auto-generated from this YAML during build/install (via Hatch). You can regenerate manually with `python -m imas_standard_names.grammar_codegen.generate` or the `build-grammar` script configured in `pyproject.toml`.

Enforce semantic rank rules (Section 7); grammar alone is insufficient.

---

## 7. Operator Rank Semantics

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

## 8. Validation Invariants

| Code name (for tooling) | Rule                                                               |
| ----------------------- | ------------------------------------------------------------------ |
| VEC001                  | A vector file must list >=2 distinct axes.                         |
| VEC002                  | All component names referenced exist.                              |
| VEC003                  | Each component follows uniform pattern `<axis>_component_of_...`.  |
| OPR001                  | Operator chain obeys rank transitions.                             |
| OPR002                  | Scalarizing operator cannot precede a vector‑producing operator.   |
| MAG001                  | `<vector>_magnitude` depends on every base component once.         |
| SUB001                  | `<subset>_magnitude` subset ⊆ frame axes.                          |
| AXS001                  | Axis tokens must appear in frame file.                             |
| DRP001                  | No legacy suffix pattern detected.                                 |
| DIAG001                 | No hard-coded instrument indices inside diagnostic quantity names. |

---

## 9. Authoring Workflow (Summary)

1. Define / reuse frame (see `frames/`).
2. Create vector file with axes + magnitude field (recommended).
3. Create one component file per axis (uniform pattern).
4. Add derived vectors (curl etc.) + their component sets.
5. Add derived scalars (divergence, magnitude if not already).
6. Run validator: `validate_catalog resources/standard_names` (or `python -m imas_standard_names.validation.cli validate_catalog resources/standard_names`).
7. Commit on green.

Extended quick start: see `quickstart.md`.

---

## 10. Anti‑Patterns

| Invalid                                   | Reason                        | Correct                                      |
| ----------------------------------------- | ----------------------------- | -------------------------------------------- |
| `magnetic_field_radial_component`         | Legacy suffix style           | `radial_component_of_magnetic_field`         |
| `curl_of_magnetic_field_radial_component` | Ambiguous (curl of scalar)    | `radial_component_of_curl_of_magnetic_field` |
| `gradient_of_magnetic_field`              | Gradient needs scalar operand | (none) or `gradient_of_electron_temperature` |
| `magnitude_of_magnetic_field_magnitude`   | Double magnitude (invalid)    | `magnitude_of_magnetic_field`                |

---

## 11. Future Extensions (TBD)

- Tensor ranks (`kind: tensor` with index list).
- Frame transformations.
- Normalized variants with explicit dependency tracking.

---

## 12. Appendix: Quick Regex Hints

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

## 13. Extended Scalar Author Guidance

See also the dedicated Style Guide (`style-guide.md`) for a broader set of
rules, anti-patterns, submission checklist, and equilibrium attribute
conventions.

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
| `magnetic_field_magnitude`                          | Deprecated legacy magnitude suffix          | `magnitude_of_magnetic_field`                          |
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
