# Guidelines for IMAS Standard Names

!!! info "Auto-Generated Vocabularies"
Token lists are automatically generated from `grammar/specification.yml`. See [Grammar Reference](grammar-reference.md) for complete tables.

## Overview

Standard names provide a controlled vocabulary for identifying physical quantities, diagnostic measurements, and geometric properties in fusion experiments. Each name follows a canonical pattern ensuring:

- **Deterministic parsing** — names decompose unambiguously into structured components
- **Controlled vocabularies** — segments use enumerated tokens from the grammar specification
- **Physical clarity** — distinctions between intrinsic properties, measurements, spatial locations
- **IMAS DD alignment** — conventions follow IMAS Data Dictionary standards

## Basic RulesStandard names follow these fundamental requirements:

| Rule                    | Description                                                                                              | Example                                                        |
| ----------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Characters**          | Lowercase letters, digits, underscores only                                                              | `electron_temperature` ✓<br>`Electron_Temperature` ✗           |
| **Start**               | Must begin with a letter                                                                                 | `temperature` ✓<br>`1_temperature` ✗                           |
| **Spelling**            | Use US spelling                                                                                          | `analyze`, `center`                                            |
| **Units**               | Never include units in the name                                                                          | `temperature` ✓<br>`temperature_ev` ✗                          |
| **Order**               | Follow fixed segment order (see below)                                                                   | Must respect grammar                                           |
| **IMAS DD Conventions** | Sign conventions, coordinate systems, and physical definitions MUST strictly follow IMAS Data Dictionary | Follow IMAS DD documentation exactly                           |
| **Tags Primary First**  | First tag (tags[0]) must be primary tag; secondary tags like 'cylindrical-coordinates' must follow       | `['magnetics', 'measured']` ✓<br>`['measured', 'magnetics']` ✗ |

## Grammar Structure

Standard names follow a fixed segment pattern:

```text
[<component>_component_of | <coordinate>]?
[<subject>]?
<geometric_base | physical_base>
[of_<object> | from_<source>]?
[of_<geometry> | at_<position>]?
[due_to_<process>]?
```

See [Grammar Reference](grammar-reference.md) for the complete specification and auto-generated segment documentation.

### Key Concepts

**Split Base Structure:**

- Every name must have either a `geometric_base` OR a `physical_base` (mutually exclusive)
- **Geometric base**: Spatial/geometric quantities (position, vertex, centroid, outline, etc.)
- **Physical base**: Physical measurements, fields, properties (temperature, magnetic_field, voltage, area, etc.)

**Component vs Coordinate:**

- Use `component` with `physical_base` for physical vectors: `{axis}_component_of_{physical_vector}`
- Use `coordinate` with `geometric_base` for geometric vectors: `{axis}_{geometric_base}`

**Object vs Source:**

- `of_<object>` — intrinsic property OF hardware/equipment (e.g., `area_of_flux_loop`)
- `from_<source>` — measurement/signal FROM device (e.g., `voltage_from_flux_loop`)

**Geometry vs Position:**

- `of_<geometry>` — geometric property OF spatial object (e.g., `major_radius_of_plasma_boundary`)
- `at_<position>` — field quantity evaluated AT location (e.g., `electron_temperature_at_magnetic_axis`)

### Segment Reference

For detailed segment descriptions, templates, and exclusivity rules, see [Grammar Reference](grammar-reference.md#segment-rules).

---

## Vocabulary Overview

Standard names use controlled vocabularies for specific segments. For complete token lists and detailed usage, see [Grammar Reference](grammar-reference.md#vocabularies).

### Components

Specify vector direction (e.g., `radial`, `toroidal`, `vertical`, `x`, `y`, `z`, `parallel`, `perpendicular`).

**Usage:**

- Physical vectors: `radial_component_of_magnetic_field`
- Geometric vectors: `radial_position_of_flux_loop`

### Subjects

Identify particle species or plasma populations (e.g., `electron`, `ion`, `deuterium`, `tritium`).

**Example:** `electron_temperature`, `ion_density`

### Geometric Bases

Spatial/geometric quantities that require object or geometry qualification (e.g., `position`, `vertex`, `centroid`, `outline`).

**Examples:**

- `position_of_flux_loop`
- `radial_position_of_flux_loop`
- `vertex_of_plasma_boundary`

### Objects

Hardware or equipment whose intrinsic properties you describe (template: `of_{token}`).

**Examples:**

- `area_of_flux_loop` — equipment characteristic
- `major_radius_of_poloidal_field_coil` — geometric property
- `turn_count_of_rogowski_coil` — hardware parameter

### Sources

Devices from which measurements or signals originate (template: `from_{token}`).

**Examples:**

- `voltage_from_flux_loop` — diagnostic measurement
- `current_from_poloidal_field_coil` — actuator signal
- `magnetic_field_from_toroidal_magnetic_field_probe` — sensor reading

### Positions

Spatial locations or geometric objects (templates: `at_{token}` or `of_{token}`).

**Examples:**

- `electron_temperature_at_magnetic_axis` — field at location
- `pressure_at_plasma_boundary` — measurement at position
- `major_radius_of_plasma_boundary` — geometric property

### Processes

Physical mechanisms (template: `due_to_{token}`).

**Examples:**

- `heat_flux_due_to_conduction`
- `particle_flux_due_to_diffusion`
- `heating_due_to_neutral_beam_injection`

---

## Common Patterns

### Physical Measurements

Basic physical quantities use subject + physical_base:

```text
electron_temperature
ion_density
plasma_pressure
```

### Physical Vector Components

Physical vectors use component + physical_base:

```text
radial_component_of_magnetic_field
toroidal_component_of_plasma_velocity
parallel_heat_flux
```

### Geometric Quantities

Geometric quantities use coordinate + geometric_base + object/geometry:

```text
position_of_flux_loop
radial_position_of_flux_loop
vertex_of_plasma_boundary
centroid_of_divertor_tile
```

### Hardware Properties vs Measurements

Distinguish intrinsic properties (of_object) from measurements (from_source):

```text
area_of_flux_loop                    (intrinsic property)
voltage_from_flux_loop               (measurement)
major_radius_of_poloidal_field_coil  (geometric property)
current_from_poloidal_field_coil     (actuator signal)
```

### Spatial Qualification

Use at_position for fields evaluated at locations:

```text
electron_temperature_at_magnetic_axis
pressure_at_plasma_boundary
density_at_outer_midplane
```

Use of_geometry for geometric properties of spatial objects:

```text
major_radius_of_plasma_boundary
area_of_first_wall
curvature_of_flux_surface
```

---

## Quick Reference

**Complete vocabularies:** [Grammar Reference](grammar-reference.md#vocabularies)

**Step-by-step guide:** [Quick Start](development/quickstart.md)

**Authoring rules:** [Style Guide](development/style-guide.md)

**Formal specification:** [Specification](development/specification.md)

**Worked example:** [IMAS Magnetics Diagnostic](magnetics-example.md)
