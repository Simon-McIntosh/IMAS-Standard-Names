# Reduction Provenance Grammar

This document describes the canonical reduction naming grammar and associated
`provenance` metadata used by the IMAS Standard Names catalog. Reductions map a
higher-rank or multi-component entity (vector field, time history, volume) to a
scalar (or lower rank) quantity via a well-defined aggregation operation.

## Provenance Schema (mode: reduction)

```
provenance:
  mode: reduction            # Discriminator for ReductionProvenance
  reduction: <id>            # One of: magnitude, time_average, root_mean_square, volume_integral (extensible)
  domain: <domain>           # Aggregation domain: none | time | space | volume | ensemble | frequency | custom
  base: <standard_name>      # The base standard name being reduced
  # (Future) parameters: optional structured metadata (e.g., window, bounds)
```

### Required Fields

- `reduction`: Identifier registered in `REDUCTION_PATTERNS` (see `imas_standard_names/reductions.py`).
- `domain`: Context of aggregation. Use `none` for reductions that purely collapse vector components (e.g., magnitude).
- `base`: The standard name (vector, scalar, or derived type) that is the input to the reduction.

## Current Reduction Patterns

| Reduction        | Naming Pattern Prefix  | Domain Constraint                | Requires Vector Base | Example Name                                     |
| ---------------- | ---------------------- | -------------------------------- | -------------------- | ------------------------------------------------ |
| magnitude        | `magnitude_of_`        | domain == none                   | yes (vector)         | magnitude_of_magnetic_field                      |
| time_average     | `time_average_of_`     | domain == time                   | no                   | time_average_of_electron_temperature (future)    |
| root_mean_square | `root_mean_square_of_` | domain in {time, ensemble, none} | no                   | root_mean_square_of_density_fluctuation (future) |
| volume_integral  | `volume_integral_of_`  | domain == volume                 | no                   | volume_integral_of_radiated_power (future)       |

(Only `magnitude` is presently instantiated in the catalog; others are scaffolded for forward compatibility.)

## Naming Rules

1. The filesystem/YAML `name` MUST begin with the pattern prefix registered for the reduction.
2. The substring following the prefix MUST equal the `base` name exactly.
3. `magnitude` reductions require that `base` resolves to a `vector` kind entry (enforced by validation).
4. Reductions yield a scalar quantity; catalog entries should use `kind: scalar` with provenance.
5. Deprecated suffix magnitude forms have been removed from the catalog; always use `magnitude_of_<base>`.

## Migration Guidance

- Use reduction provenance blocks for all reductions (magnitude, mean, rms, etc.).
- Magnitude entries should reference the base vector via `provenance.base`.
- Avoid redundant analytic expressions; standard reductions are well-defined.

### Example: Canonical Magnitude

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

### (Removed) Deprecated Suffix Forms

Legacy suffix forms like `<base>_magnitude` have been fully removed. Tools should rely
solely on the prefix grammar `magnitude_of_<base>`.

## Future Extensions

Planned enhancements:

- Parameterized reductions (e.g., time windows: `window: {start: t0, end: t1}`)
- Multi-stage reductions (e.g., time_average_of_magnitude_of_velocity_field) validated via recursive provenance inspection.
- Vector base validation helper (pending) to ensure correctness of magnitude bases.

## Validation Lifecycle

1. Parse YAML into Pydantic model (`StandardName*`).
2. If `provenance.mode == reduction`, apply `enforce_reduction_naming()`.
3. (Upcoming) Post-catalog validation pass ensures structural integrity (vector existence, absence of circular reductions).

## Deprecation Policy

Any legacy or alternative pattern MUST:

- Set `status: deprecated`.
- Provide a note referencing the canonical form.
- Maintain functional provenance for backward compatibility until removal.

## Authoring Checklist

- [ ] Name matches `<pattern_prefix><base>`.
- [ ] `kind: scalar` set with provenance.
- [ ] Units consistent with reduction semantics.
- [ ] `provenance.reduction` registered.
- [ ] `domain` aligned with pattern (magnitude -> none).
- [ ] Vector entry lists this magnitude in its `magnitude:` field (if applicable).
- [ ] Deprecated variants clearly labeled.

---

Revision: initial draft.
