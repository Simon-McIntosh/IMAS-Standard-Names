# Quick Start

This guide starts with scalars (atomic building blocks) and then covers
vectors (structured aggregations) that use the uniform component grammar.
If you are defining simple physical scalars, Section 1 may be sufficient.

---

## 1. Adding a Base Scalar (Atomic Quantity)

### 1.1 Simple Physical Scalar

Choose a concise, lowercase, underscore-delimited name capturing the quantity
unambiguously (avoid frame or axis qualifiers unless intrinsic):

Example file: `standard_names/electron/electron_temperature.yml`

```yaml
name: electron_temperature
kind: scalar
unit: keV # pick canonical unit; validators will check format
description: Electron temperature.
status: draft
```

Guidelines:

- Use singular nouns where the quantity is a field value (temperature not temperatures).
- Avoid embedding coordinate system (prefer metadata or separate coordinate vars).
- Do not prefix with measurement method; use a tag or metadata field instead (future schema extension).

### 1.2 Time Derivative of a Scalar

For scalar → scalar with time derivative, prepend `time_derivative_of_`.

`standard_names/electron/time_derivative_of_electron_temperature.yml`

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
description: Temporal derivative of electron_temperature.
status: draft
```

### 1.3 Gradient of a Scalar (Produces a Vector)

Gradient changes rank (scalar → vector). Skip to the vector section below using
`gradient_of_<scalar>` as the vector name (kind: derived*vector) and add
components: `<axis>\_component_of_gradient_of*<scalar>`.

### 1.4 Derived Scalar from a Vector

If you need divergence of a velocity vector:
`divergence_of_plasma_velocity` (kind: derived_scalar) — ensure a parent vector exists.

### 1.5 Naming Anti‑Patterns for Scalars

| Invalid                                             | Reason                                      | Correct                                                |
| --------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------ |
| `electron_temperature_time_derivative`              | Suffix pattern                              | `time_derivative_of_electron_temperature`              |
| `gradient_of_electron_temperature_radial_component` | Gradient makes vector; component form wrong | `radial_component_of_gradient_of_electron_temperature` |
| `electron_temperature_magnitude`                    | Magnitude reserved for vectors              | (omit)                                                 |

### 1.6 Minimal Template (Base Scalar)

```yaml
name: <quantity>
kind: scalar
unit: <unit>
description: <one sentence>
status: draft
```

### 1.7 Minimal Template (Derived Scalar from Vector)

```yaml
name: divergence_of_<vector>
kind: derived_scalar
unit: <unit>
parent_operation:
  operator: divergence
  operand_vector: <vector>
dependencies:
  - <vector_component_1>
  - <vector_component_2>
  - <vector_component_3>
status: draft
```

Run the validator after adding any new scalar.

### 1.8 Scalar Cheat Sheet

```text
Base scalar: <noun_phrase>
Time derivative: time_derivative_of_<scalar>
Vector gradient (see vectors): gradient_of_<scalar>
Scalar from vector divergence: divergence_of_<vector>
Scalar from vector magnitude (vector → scalar): magnitude_of_<vector_expression>  # canonical (suffix form deprecated)
```

---

## 2. Adding a New Vector with Uniform Components

Goal: Define a new vector (e.g. `magnetic_field`) plus components and its magnitude in under two minutes.

### 2.1 Pick / Define Frame

Add or reuse a frame YAML in `frames/` (example: `cylindrical_r_tor_z.yml`).

Minimal frame example:

```yaml
frame: cylindrical_r_tor_z
dimension: 3
axes:
  - name: radial
  - name: toroidal
  - name: vertical
handedness: right
status: draft
```

### 2.2 Create Domain Folder

```
standard_names/magnetic_field/
```

### 2.3 Vector File

`standard_names/magnetic_field/magnetic_field.yml`

```yaml
name: magnetic_field
kind: vector
frame: cylindrical_r_tor_z
unit: T
components:
  radial: radial_component_of_magnetic_field
  toroidal: toroidal_component_of_magnetic_field
  vertical: vertical_component_of_magnetic_field
magnitude: magnitude_of_magnetic_field
status: draft
description: Magnetic field vector in laboratory cylindrical coordinates.
```

### 2.4 Component Files (one per axis)

Example: `standard_names/magnetic_field/radial_component_of_magnetic_field.yml`

```yaml
name: radial_component_of_magnetic_field
kind: scalar
unit: T
status: draft
description: Radial component of magnetic_field.
```

Repeat for toroidal / vertical axes. Component membership is inferred purely from the
uniform name pattern and the vector's `components` mapping.

### 2.5 Magnitude File

`standard_names/magnetic_field/magnitude_of_magnetic_field.yml`

```yaml
name: magnitude_of_magnetic_field
kind: derived_scalar
unit: T
provenance:
  mode: reduction
  reduction: magnitude
  domain: none
  base: magnetic_field
status: draft
```

### 2.6 (Optional) Derived Vector: Curl

`standard_names/magnetic_field/curl_of_magnetic_field.yml`

```yaml
name: curl_of_magnetic_field
kind: derived_vector
frame: cylindrical_r_tor_z
unit: T.m^-1
provenance:
  mode: operator
  operators: [curl]
  base: magnetic_field
  operator_id: curl
components:
  radial: radial_component_of_curl_of_magnetic_field
  toroidal: toroidal_component_of_curl_of_magnetic_field
  vertical: vertical_component_of_curl_of_magnetic_field
status: draft
```

Component example (derived scalar component):

```yaml
name: radial_component_of_curl_of_magnetic_field
kind: derived_scalar
unit: T.m^-1
provenance:
  mode: operator
  operators: [curl]
  base: radial_component_of_magnetic_field
  operator_id: curl
status: draft
description: Radial component of curl_of_magnetic_field.
```

### 2.7 Validate

Run the catalog validator (structural + semantic):

```bash
validate_catalog resources/standard_names
```

If you don't have the console script (editable install not active), you can also invoke:

```bash
python -m imas_standard_names.validation.cli validate_catalog resources/standard_names
```

Resolve any reported issues shown. Exit code 0 means all checks passed; non-zero indicates problems (see messages for details).

### 2.8 Commit & Document

Add a short note in CHANGELOG if introducing a new vector domain.

Done.

---

## 3. Vector Cheat Sheet (Copy‑Paste Snippets)

- Component template:

```yaml
name: <axis>_component_of_<vector_expression>
kind: scalar # or derived_scalar
unit: <unit>
status: draft
description: <Axis> component of <vector_expression>.
```

- Derived vector template:

```yaml
name: <op>_of_<vector>
kind: derived_vector
frame: <frame>
unit: <unit>
provenance:
  mode: operator
  operators: [<op>]
  base: <vector>
  operator_id: <op>
components:
  <axis>: <axis>_component_of_<op>_of_<vector>
  ...
status: draft
```

---

End of quick start.
