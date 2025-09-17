# Provenance Schema Reference

This document describes the unified `provenance` block used across derived
standard names. It replaces earlier ad hoc `derivation` / `parent_operation`
fields and provides a single structured container for expressing how a
quantity was produced.

## Modes

| mode       | Description                               | Typical Kind          |
| ---------- | ----------------------------------------- | --------------------- |
| operator   | One or more chained operators on a base   | derived_scalar/vector |
| reduction  | Scalar reduction over a vector expression | derived_scalar        |
| expression | Explicit algebraic combination            | derived_scalar        |

## Common Fields

| Field         | Applies to         | Description                                     |
| ------------- | ------------------ | ----------------------------------------------- |
| `mode`        | all                | One of `operator`, `reduction`, `expression`.   |
| `base`        | operator/reduction | Root quantity the chain applies to.             |
| `operators`   | operator           | Ordered list of operator identifiers.           |
| `operator_id` | operator           | Canonical id of the outermost operator.         |
| `reduction`   | reduction          | Reduction kind (e.g. `magnitude`).              |
| `domain`      | reduction          | Domain / qualifier for reduction (e.g. `none`). |
| `expression`  | expression         | Algebraic expression string.                    |
| `inputs`      | expression         | List of input standard names referenced.        |

## Examples

### Operator Chain (Vector → Vector)

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

### Magnitude Reduction (Vector → Scalar)

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

### Expression (Scalar Combination)

```yaml
name: weighted_average_electron_temperature
kind: derived_scalar
unit: keV
provenance:
  mode: expression
  expression: (a*core_electron_temperature + b*edge_electron_temperature)/(a+b)
  inputs:
    - core_electron_temperature
    - edge_electron_temperature
status: draft
```

## Guidelines

- Keep `operators` list normalized (lowercase identifiers).
- Prefer `reduction: magnitude` over manual sqrt-of-sum-of-squares expressions.
- Use `expression` mode sparingly; whenever an operator or reduction form exists, prefer structured representation.
- Avoid nesting a scalarizing reduction inside an operator chain unless physically required.

## Validation Notes

Current validation enforces only basic structural correctness (vector component existence and magnitude base). Future extensions will add:

- Rank checking across operator chains.
- Dimension/unit inference consistency.
- Cycle detection in `expression` inputs.

---

This reference will evolve; keep provenance blocks minimal and precise.
