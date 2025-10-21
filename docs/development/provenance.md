# Provenance Schema

This document describes the `provenance` block used in derived standard names to document how quantities are produced.

**See also:** [Specification](specification.md) for validation rules | [Reductions](reductions.md) for reduction patterns

---

## Overview

The `provenance` block provides structured metadata for derived quantities. It enables:

- Traceability of derivation paths
- Validation of dependencies
- Documentation of transformation methods

---

| Mode       | Description                               | Applies to     |
| ---------- | ----------------------------------------- | -------------- |
| operator   | One or more chained operators on a base   | scalar, vector |
| reduction  | Scalar reduction over a vector expression | scalar         |
| expression | Explicit algebraic combination            | scalar         |

## Field Reference

### Common Fields (All Modes)

| Field  | Applies to | Description                                  |
| ------ | ---------- | -------------------------------------------- |
| `mode` | all        | One of `operator`, `reduction`, `expression` |

### Operator Mode Fields

| Field         | Required | Description                            |
| ------------- | -------- | -------------------------------------- |
| `operators`   | Yes      | Ordered list of operator identifiers   |
| `base`        | Yes      | Root quantity the chain applies to     |
| `operator_id` | Yes      | Canonical id of the outermost operator |

### Reduction Mode Fields

| Field       | Required | Description                               |
| ----------- | -------- | ----------------------------------------- |
| `reduction` | Yes      | Reduction kind (e.g., `magnitude`)        |
| `domain`    | Yes      | Domain / qualifier (e.g., `none`, `time`) |
| `base`      | Yes      | Base quantity being reduced               |

### Expression Mode Fields

| Field        | Required | Description                             |
| ------------ | -------- | --------------------------------------- |
| `expression` | Yes      | Algebraic expression string             |
| `inputs`     | Yes      | List of input standard names referenced |

---

## Examples

### Operator Mode

Time derivative of a scalar:

```yaml
name: time_derivative_of_electron_temperature
kind: scalar
unit: eV.s^-1
provenance:
  mode: operator
  operators: [time_derivative]
  base: electron_temperature
  operator_id: time_derivative
status: draft
```

### Reduction Mode

Magnitude reduction from vector to scalar:

```yaml
name: magnitude_of_magnetic_field
kind: scalar
unit: T
provenance:
  mode: reduction
  reduction: magnitude
  domain: none
  base: magnetic_field
status: draft
```

### Expression Mode

Algebraic combination of scalars:

```yaml
name: ratio_of_thermal_pressure_to_magnetic_pressure
kind: scalar
unit: "1"
provenance:
  mode: expression
  expression: "thermal_pressure / magnetic_pressure"
  inputs:
    - thermal_pressure
    - magnetic_pressure
status: draft
```

---

## Guidelines

- Use `operator` mode for standard transformations (time_derivative, gradient, curl, divergence, etc.)
- Use `reduction` mode for aggregations (magnitude, time_average, volume_integral, etc.)
- Use `expression` mode sparingly; prefer structured operator/reduction forms when available
- Keep `operators` list normalized (lowercase identifiers matching operator registry)
- Ensure `base` references exist in the catalog
- Validate that `expression` inputs are valid standard names

---

## Validation

Current validation enforces:

- Basic structural correctness
- Existence of base quantities
- Valid operator identifiers

Future enhancements will add:

- Rank checking across operator chains
- Unit inference and consistency
- Cycle detection in expression dependencies
- Domain validation for reductions

---

## References

- [Specification](specification.md) — Grammar and validation rules
- [Reductions](reductions.md) — Detailed reduction patterns
- [Guidelines](../guidelines.md) — Naming conventions
