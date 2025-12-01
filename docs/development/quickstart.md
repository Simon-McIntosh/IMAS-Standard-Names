# Quick Start Guide

This guide shows you how to create new standard names for common scenarios.

!!! tip "Complete Example"
For a comprehensive worked example, see the IMAS Magnetics Diagnostic documentation.

---

## Before You Start

1. Review [Grammar Reference](../grammar-reference.md) to understand available vocabularies
2. Check [Guidelines](../guidelines.md) for naming patterns
3. Decide if you need a geometric_base or physical_base

---

## Scenario 1: Simple Physical Measurement

**Goal:** Add a basic plasma measurement like electron temperature.

**Template:**

```yaml
name: <subject>_<physical_base>
kind: scalar
unit: <unit>
description: <one-line description>
tags: [<primary_tag>]
status: draft
```

**Example:**

```yaml
name: electron_temperature
kind: scalar
unit: eV
description: Electron temperature.
tags: [plasma]
status: draft
```

---

## Scenario 2: Hardware Geometric Property

**Goal:** Add a geometric property of diagnostic hardware (e.g., flux loop position).

**Pattern:** `{coordinate}_{geometric_base}_of_{object}`

**Template:**

```yaml
name: <coordinate>_<geometric_base>_of_<object>
kind: scalar
unit: m
description: <Coordinate> <geometric_base> of <object>.
tags: [<primary_tag>, geometry]
status: draft
```

**Example:**

```yaml
name: radial_position_of_flux_loop
kind: scalar
unit: m
description: Radial position of flux loop.
tags: [magnetics, geometry]
status: draft
```

---

## Scenario 3: Diagnostic Measurement Signal

**Goal:** Add a measurement obtained from diagnostic hardware.

**Pattern:** `<physical_base>_from_{source}`

**Template:**

```yaml
name: <physical_base>_from_<source>
kind: scalar
unit: <unit>
description: <physical_base> from <source>.
tags: [<primary_tag>, measured]
status: draft
```

**Example:**

```yaml
name: voltage_from_flux_loop
kind: scalar
unit: V
description: Voltage from flux loop.
tags: [magnetics, measured]
status: draft
```

---

## Scenario 4: Physical Vector Component

**Goal:** Add a component of a physical vector field (e.g., radial magnetic field).

**Pattern:** `{component}_component_of_{physical_base}`

**Template:**

```yaml
name: <component>_component_of_<physical_base>
kind: scalar
unit: <unit>
description: <Component> component of <physical_base>.
tags: [<primary_tag>]
status: draft
```

**Example:**

```yaml
name: radial_component_of_magnetic_field
kind: scalar
unit: T
description: Radial component of magnetic field.
tags: [magnetics]
status: draft
```

---

## Scenario 5: Field at Spatial Location

**Goal:** Add a physical quantity evaluated at a specific location.

**Pattern:** `<subject>_<physical_base>_at_{position}`

**Template:**

```yaml
name: <subject>_<physical_base>_at_<position>
kind: scalar
unit: <unit>
description: <Subject> <physical_base> at <position>.
tags: [<primary_tag>]
status: draft
```

**Example:**

```yaml
name: electron_temperature_at_magnetic_axis
kind: scalar
unit: eV
description: Electron temperature at magnetic axis.
tags: [plasma]
status: draft
```

---

## Scenario 6: Geometric Property of Spatial Object

**Goal:** Add a geometric characteristic of a plasma structure.

**Pattern:** `<physical_base>_of_{geometry}`

**Template:**

```yaml
name: <physical_base>_of_<geometry>
kind: scalar
unit: m
description: <Physical_base> of <geometry>.
tags: [<primary_tag>, geometry]
status: draft
```

**Example:**

```yaml
name: major_radius_of_plasma_boundary
kind: scalar
unit: m
description: Major radius of plasma boundary.
tags: [equilibrium, geometry]
status: draft
```

---

## Validation

Use the MCP tools to validate your new standard name:

```python
# Via MCP tool
check_standard_names(names=["electron_temperature"])

# Or validate the entire catalog
validate_catalog()
```

Or use the CLI with the catalog repository:

```bash
validate_catalog $STANDARD_NAMES_CATALOG_ROOT
```

Fix any reported issues and re-run until validation passes.

---

## Common Patterns Reference

| Pattern                                     | Use Case                             | Example                                 |
| ------------------------------------------- | ------------------------------------ | --------------------------------------- |
| `<subject>_<physical_base>`                 | Basic physical measurement           | `electron_temperature`                  |
| `<coordinate>_<geometric_base>_of_<object>` | Hardware geometry                    | `radial_position_of_flux_loop`          |
| `<physical_base>_from_<source>`             | Diagnostic measurement               | `voltage_from_flux_loop`                |
| `<component>_component_of_<physical_base>`  | Physical vector component            | `radial_component_of_magnetic_field`    |
| `<physical_base>_at_<position>`             | Field at location                    | `electron_temperature_at_magnetic_axis` |
| `<physical_base>_of_<geometry>`             | Geometric property of spatial object | `major_radius_of_plasma_boundary`       |

---

## Next Steps

- Review [Style Guide](style-guide.md) for detailed authoring rules
- See [Guidelines](../guidelines.md) for more patterns and examples
- Check [Specification](specification.md) for validation rules
- Explore [Provenance](provenance.md) for derived quantities
