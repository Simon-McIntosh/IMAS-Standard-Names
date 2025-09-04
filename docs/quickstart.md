# Quick Start

This guide covers both vector and scalar standard names. Vector examples come
first because they exercise the uniform component grammar. Skip to
"Adding a Base Scalar" for scalar-only quantities.

## Adding a New Vector with Uniform Components

Goal: Define a new vector (e.g. `magnetic_field`) plus components and magnitude
in under two minutes.

### 1. Pick / Define Frame
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

### 2. Create Domain Folder
```
standard_names/magnetic_field/
```

### 3. Vector File
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
magnitude: magnetic_field_magnitude
status: draft
description: Magnetic field vector in laboratory cylindrical coordinates.
```

### 4. Component Files (one per axis)
Example: `standard_names/magnetic_field/radial_component_of_magnetic_field.yml`
```yaml
name: radial_component_of_magnetic_field
kind: scalar
unit: T
axis: radial
parent_vector: magnetic_field
status: draft
description: Radial component of magnetic_field.
```
Repeat for toroidal/vertical axes.

### 5. Magnitude File
`standard_names/magnetic_field/magnetic_field_magnitude.yml`
```yaml
name: magnetic_field_magnitude
kind: derived_scalar
unit: T
parent_vector: magnetic_field
derivation:
  expression: sqrt(radial_component_of_magnetic_field^2 +\n                   toroidal_component_of_magnetic_field^2 +\n                   vertical_component_of_magnetic_field^2)
  dependencies:
    - radial_component_of_magnetic_field
    - toroidal_component_of_magnetic_field
    - vertical_component_of_magnetic_field
status: draft
```

### 6. (Optional) Derived Vector: Curl
`standard_names/magnetic_field/curl_of_magnetic_field.yml`
```yaml
name: curl_of_magnetic_field
kind: derived_vector
frame: cylindrical_r_tor_z
unit: T.m^-1
parent_operation:
  operator: curl
  operand_vector: magnetic_field
components:
  radial: radial_component_of_curl_of_magnetic_field
  toroidal: toroidal_component_of_curl_of_magnetic_field
  vertical: vertical_component_of_curl_of_magnetic_field
status: draft
```

Component example:
```yaml
name: radial_component_of_curl_of_magnetic_field
kind: derived_scalar
unit: T.m^-1
axis: radial
parent_vector: curl_of_magnetic_field
derivation:
  expression: d(B_vertical)/d(toroidal) - d(B_toroidal)/d(vertical)
  dependencies:
    - vertical_component_of_magnetic_field
    - toroidal_component_of_magnetic_field
status: draft
```

### 7. Validate
Run the (stub) validator:
```bash
python tools/validate_catalog.py
```
Resolve any reported issues.

### 8. Commit & Document
Add a short note in CHANGELOG if introducing a new vector domain.

Done.

## Adding a Base Scalar

### 1. Simple Physical Scalar
Choose a concise, lowercase, underscore-delimited name capturing the
quantity unambiguously (avoid framing or axis qualifiers unless intrinsic):

Example file: `standard_names/electron/electron_temperature.yml`
```yaml
name: electron_temperature
kind: scalar
unit: keV            # pick canonical unit; validators will standardize format
description: Electron temperature.
status: draft
```

Guidelines:
* Use singular nouns where the quantity is a field value (temperature not temperatures).
* Avoid embedding coordinate system (prefer metadata or separate coordinate vars).
* Do not prefix with measurement method; use a tag or metadata field instead (future schema extension).

### 2. Time Derivative of a Scalar
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

### 3. Gradient of a Scalar (Produces a Vector)
Gradient changes rank (scalar → vector). Follow vector quickstart using
`gradient_of_<scalar>` as the vector name (kind: derived_vector) and add
components: `<axis>_component_of_gradient_of_<scalar>`.

### 4. Derived Scalar from a Vector
If you need divergence of a velocity vector:
`divergence_of_plasma_velocity` (kind: derived_scalar) — ensure a parent vector exists.

### 5. Naming Anti‑Patterns for Scalars
Invalid | Reason | Correct
------- | ------ | -------
`electron_temperature_time_derivative` | Suffix pattern | `time_derivative_of_electron_temperature`
`gradient_of_electron_temperature_radial_component` | Gradient makes vector; component form wrong | `radial_component_of_gradient_of_electron_temperature`
`electron_temperature_magnitude` | Magnitude reserved for vectors | (omit)

### 6. Minimal Template (Base Scalar)
```yaml
name: <quantity>
kind: scalar
unit: <unit>
description: <one sentence>
status: draft
```

### 7. Minimal Template (Derived Scalar from Vector)
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

### Cheat Sheet (Copy‑Paste Snippets)

* Component template:
```yaml
name: <axis>_component_of_<vector_expression>
kind: scalar        # or derived_scalar
unit: <unit>
axis: <axis>
parent_vector: <vector or derived vector>
status: draft
```

* Derived vector template:
```yaml
name: <op>_of_<vector>
kind: derived_vector
frame: <frame>
unit: <unit>
parent_operation:
  operator: <op>
  operand_vector: <vector>
components:
  <axis>: <axis>_component_of_<op>_of_<vector>
  ...
status: draft
```
