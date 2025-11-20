# Style Guide

This guide provides authoring best practices for creating well-formed, consistent standard names.

**See also:** [Specification](specification.md) for validation rules | [Guidelines](../guidelines.md) for patterns | [Quick Start](quickstart.md) for examples

---

## Naming Rules

### Lexical Constraints

| Rule          | Requirement                                                 | Example                          |
| ------------- | ----------------------------------------------------------- | -------------------------------- |
| Characters    | Lowercase a-z, digits 0-9, underscores only                 | `electron_temperature`           |
| Start         | Must begin with a letter                                    | `1_temperature`                  |
| No            | Double underscores, trailing underscore, camelCase, hyphens | `electron__temp`                 |
| Pluralization | Use singular unless inherently plural                       | `coefficient` not `coefficients` |
| Abbreviations | Avoid unless universally canonical                          | Prefer `poloidal_field_coil`     |
| Numbers       | Use plain digits without zero padding                       | `coil_1` not `coil_01`           |

### Grammar Compliance

- Follow canonical pattern from [Specification](specification.md#canonical-pattern)
- Respect segment order (see [Grammar Reference](../grammar-reference.md#segment-order))
- Use correct templates (`of_`, `from_`, `at_`, `due_to_`)
- Choose exactly one base type (geometric_base XOR physical_base)

---

## Split Base Usage

### Geometric Base

**When to use:** Spatial/geometric quantities describing locations, shapes, extents.

**Requirements:**

- Must be qualified with `object` or `geometry` segment
- Use `coordinate` prefix for vector components (NOT `component`)
- Common tokens: `position`, `vertex`, `centroid`, `outline`, `displacement`

**Examples:**

```text
position_of_flux_loop
radial_position_of_flux_loop
vertex_of_plasma_boundary
centroid_of_divertor_tile
```

### Physical Base

**When to use:** Physical measurements, fields, hardware properties.

**Requirements:**

- Open-ended vocabulary (defined in catalog entries)
- Use `component` prefix for physical vector components
- Can combine with `object`, `source`, `position`, `geometry`, `process`

**Examples:**

```text
electron_temperature
radial_component_of_magnetic_field
voltage_from_flux_loop
area_of_poloidal_magnetic_field_probe
electron_temperature_at_magnetic_axis
```

---

## Segment Distinctions

### component vs coordinate

| Segment    | Use With       | Pattern                          | Example                              |
| ---------- | -------------- | -------------------------------- | ------------------------------------ |
| component  | physical_base  | `{axis}_component_of_{physical}` | `radial_component_of_magnetic_field` |
| coordinate | geometric_base | `{axis}_{geometric}`             | `radial_position_of_flux_loop`       |

### device vs object

| Segment | Pattern/Template    | Meaning                        | Example             |
| ------- | ------------------- | ------------------------------ | ------------------- |
| device  | `{device}_{signal}` | Dynamic signal FROM device     | `flux_loop_voltage` |
| object  | `of_{token}`        | Intrinsic property OF hardware | `area_of_flux_loop` |

**Same device/object, different patterns:**

```text
flux_loop_voltage                        (dynamic signal from device)
area_of_flux_loop                        (intrinsic property of object)
current_of_poloidal_field_coil           (intrinsic property of coil)
```

### of_geometry vs at_position

| Segment  | Template     | Meaning                              | Example                                 |
| -------- | ------------ | ------------------------------------ | --------------------------------------- |
| geometry | `of_{token}` | Geometric property OF spatial object | `major_radius_of_plasma_boundary`       |
| position | `at_{token}` | Field quantity evaluated AT location | `electron_temperature_at_magnetic_axis` |

**Same token, different prepositions:**

```text
major_radius_of_plasma_boundary           (geometric property of the boundary)
electron_temperature_at_plasma_boundary   (field evaluated at the boundary)
```

---

## YAML Field Guidelines

### Required Fields

```yaml
name: <follows grammar>
kind: scalar
unit: <SI-consistent>
description: <concise, starts with capital>
tags: [<primary_tag>, <secondary_tags...>]
status: draft | active | deprecated
```

### Field Rules

| Field         | Rule                                                           | Example                               |
| ------------- | -------------------------------------------------------------- | ------------------------------------- |
| `name`        | Must match grammar exactly                                     | `radial_component_of_magnetic_field`  |
| `kind`        | `scalar` for all entries (vector metadata is inferred)         | `scalar`                              |
| `unit`        | SI symbols, use `.` for multiplication, `^` for powers         | `T`, `eV`, `m.s^-1`                   |
| `status`      | `draft` `active` `deprecated` `superseded`                     | `draft`                               |
| `tags`        | PRIMARY tag first (tags[0]), secondary tags after              | `[magnetics, measured, geometry]`     |
| `description` | 120 chars, begins with capital, no trailing period if fragment | `Radial component of magnetic field.` |

### Tags Ordering

**Critical:** The first tag (`tags[0]`) MUST be a primary tag:

- Primary tags: `magnetics`, `plasma`, `equilibrium`, `fundamental`, `heating`, `diagnostics`
- Secondary tags: `measured`, `geometry`, `cylindrical-coordinates`, `derived`

**Valid:**

```yaml
tags: [magnetics, measured, geometry]
```

**Invalid:**

```yaml
tags: [measured, magnetics] # measured is secondary, must come after primary
```

---

## Documentation Guidelines

**Standalone Documentation:** Documentation should be self-contained and comprehensive. When documenting sign conventions, coordinate systems, or physical definitions, define them explicitly within the documentation text rather than relying on bare external references.

**Best Practices:**

- Define sign conventions explicitly: "Sign convention: Positive when normal to loop points downward (negative Z direction)."
- Document coordinate system conventions fully within the documentation text
- Make documentation understandable without consulting external sources
- When concepts align with IMAS Data Dictionary or other standards, extract and expand the physics content to make it standalone
- Use inline links `[standard_name](#standard_name)` for cross-references to other standard names

**Avoid:**

- Bare references like "see IMAS DD" or "follows COCOS convention" without explanation
- Statements like "refer to [external source]" without providing the actual information
- Assuming readers have access to external documentation

---

## Anti-Patterns

| Invalid                                  | Problem                   | Correct                               |
| ---------------------------------------- | ------------------------- | ------------------------------------- |
| `magnetic_field_radial_component`        | Wrong segment order       | `radial_component_of_magnetic_field`  |
| `radial_component_of_position`           | component with geometric  | `radial_position_of_flux_loop`        |
| `radial_position_component_of_flux_loop` | coordinate with component | `radial_position_of_flux_loop`        |
| `voltage_from_flux_loop`                 | Wrong pattern for signal  | `flux_loop_voltage`                   |
| `electron_temperature_ev`                | Units in name             | `electron_temperature` (unit in YAML) |
| `pf_coil_current_1`                      | Index after quantity      | `pf_coil_1_current`                   |
| `Electron_Temperature`                   | Not lowercase             | `electron_temperature`                |
| `electron__temperature`                  | Double underscore         | `electron_temperature`                |

---

## Submission Checklist

Before proposing a new standard name:

- [ ] Name follows grammar (run validator)
- [ ] Correct base type chosen (geometric vs physical)
- [ ] Component/coordinate used correctly with base type
- [ ] object/source distinction correct
- [ ] geometry/position distinction correct
- [ ] Tags ordered correctly (primary first)
- [ ] Units SI-consistent and match IMAS DD
- [ ] Description concise and clear
- [ ] IMAS DD alignment verified
- [ ] Validator passes (exit code 0)

---

## Quick Reference

**Geometric patterns:**

```text
<coordinate>_<geometric_base>_of_<object>       radial_position_of_flux_loop
<geometric_base>_of_<geometry>                  vertex_of_plasma_boundary
```

**Physical patterns:**

```text
<subject>_<physical_base>                       electron_temperature
<component>_component_of_<physical_base>        radial_component_of_magnetic_field
<device>_<physical_base>                        flux_loop_voltage
<physical_base>_of_<object>                     area_of_flux_loop
<physical_base>_at_<position>                   electron_temperature_at_magnetic_axis
<physical_base>_of_<geometry>                   major_radius_of_plasma_boundary
<physical_base>_due_to_<process>                heat_flux_due_to_conduction
```

---

## References

- [Grammar Reference](../grammar-reference.md) — Complete vocabularies
- [Specification](specification.md) — Validation rules
- [Guidelines](../guidelines.md) — Naming patterns
- [Quick Start](quickstart.md) — Step-by-step examples
- [Provenance](provenance.md) — Derived quantities
