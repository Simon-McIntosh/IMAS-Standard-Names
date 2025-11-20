# Guidelines for IMAS Standard Names

!!! info "Auto-Generated Vocabularies"
Token lists are automatically generated from `grammar/specification.yml`. See [Grammar Reference](grammar-reference.md) for complete tables.

## Overview

Standard names provide a controlled vocabulary for identifying physical quantities, diagnostic measurements, and geometric properties in fusion experiments. Each name follows a canonical pattern ensuring:

- **Deterministic parsing** — names decompose unambiguously into structured components
- **Controlled vocabularies** — segments use enumerated tokens from the grammar specification
- **Physical clarity** — distinctions between intrinsic properties, measurements, spatial locations
- **IMAS DD alignment** — conventions follow IMAS Data Dictionary standards

## Basic Rules

Standard names follow these fundamental requirements:

| Rule                   | Description                                                                                                                                                               | Example                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Characters**         | Lowercase letters, digits, underscores only                                                                                                                               | `electron_temperature` ✓<br>`Electron_Temperature` ✗           |
| **Start**              | Must begin with a letter                                                                                                                                                  | `temperature` ✓<br>`1_temperature` ✗                           |
| **Spelling**           | Use US spelling                                                                                                                                                           | `analyze`, `center`                                            |
| **Units**              | Never include units in the name                                                                                                                                           | `temperature` ✓<br>`temperature_ev` ✗                          |
| **Order**              | Follow fixed segment order (see below)                                                                                                                                    | Must respect grammar                                           |
| **Documentation**      | Document sign conventions, coordinate systems, and physical definitions explicitly and standalone (avoid bare references to external sources like IMAS DD or COCOS specs) | Define conventions in documentation text                       |
| **Tags Primary First** | First tag (tags[0]) must be primary tag; secondary tags like 'cylindrical-coordinates' must follow                                                                        | `['magnetics', 'measured']` ✓<br>`['measured', 'magnetics']` ✗ |

## Grammar Structure

Standard names follow a fixed segment pattern:

```text
[<component>_component_of | <coordinate>]?
[<subject>]?
[<device> | of_<object>]?
<geometric_base | physical_base>
[of_<geometry> | at_<position>]?
[due_to_<process>]?
```

See [Grammar Reference](grammar-reference.md) for the complete specification and auto-generated segment documentation.

### Key Concepts

**Physical Quantity Identification:**

- Standard names identify **what** is being measured or calculated (the physical/geometric quantity)
- Information about **how** (method), **from where** (device), or **processing** goes in **metadata** (per fusion conventions), not the name
- Ask: "What is this quantity?" not "How was it measured?"
- See [Metadata Conventions](metadata-conventions.md) for details on separating quantities from acquisition context
- **Exception**: Tags like `measured`, `reconstructed`, and `calibrated` are appropriate for categorizing data use cases
- **Do not** include method qualifiers like "measured*" or "reconstructed*" in the standard name itself

**Split Base Structure:**

- Every name must have either a `geometric_base` OR a `physical_base` (mutually exclusive)
- **Geometric base**: Spatial/geometric quantities (position, vertex, centroid, outline, etc.)
- **Physical base**: Physical measurements, fields, properties (temperature, magnetic_field, voltage, area, etc.)

**Component vs Coordinate:**

- Use `component` with `physical_base` for physical vectors: `{axis}_component_of_{physical_vector}`
- Use `coordinate` with `geometric_base` for geometric vectors: `{axis}_{geometric_base}`

**Device vs Object:**

- Use `<device>_<signal>` for device signals/outputs where the device IS the source (e.g., `flux_loop_voltage`, `passive_loop_current`)
- Use `<property>_of_<object>` for intrinsic properties OF hardware (e.g., `area_of_flux_loop`, `position_of_poloidal_field_coil`)
- Device and object segments are mutually exclusive

**Object Segment:**

- `of_<object>` — intrinsic property OF hardware/equipment (e.g., `area_of_flux_loop`, `current_of_poloidal_field_coil`)
- Use for geometric properties and intrinsic characteristics of physical objects

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

Hardware or equipment for describing intrinsic properties and device signals (template: `of_{token}` or `<object>_`).

**Two naming patterns:**

1. **Intrinsic properties** (using `of_<object>`):

   - `area_of_flux_loop` — equipment geometric property
   - `major_radius_of_poloidal_field_coil` — hardware dimension
   - `number_of_turns_of_rogowski_coil` — hardware parameter

2. **Device signals** (using `<object>_<signal>`):
   - `flux_loop_voltage` — voltage signal from flux loop
   - `passive_loop_current` — induced current in passive loop
   - `poloidal_magnetic_field_probe_voltage` — probe output signal

**Key distinction**: Use `<device>_<signal>` when the quantity IS a property/output of the device itself. Use generic names with metadata when describing physics quantities measured BY the device.

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

## Device Signals vs Physics Quantities

### Decision Tree

When naming a quantity, follow this decision tree:

**1. Is this a property or signal of the device itself?**

- **Yes** → Use `<device>_<signal>` pattern
  - Examples: `flux_loop_voltage`, `passive_loop_current`, `interferometer_beam_phase`
  - The device is the source/conductor/emitter of this quantity
- **No** → Continue to question 2

**2. Does the quantity have physical meaning independent of the device?**

- **Yes** → Use generic name (document device in metadata per fusion conventions)
  - Example: `electron_density` (not `thomson_scattering_electron_density`)
  - The device measures/observes this physics quantity, but doesn't define it
- **No** → Use `<device>_<signal>` pattern
  - Example: `interferometer_beam_path_length` (beam-specific geometry)

**3. Could multiple different devices measure the same physical quantity?**

- **Yes** → Use generic name, distinguish devices via metadata
  - Both interferometer and Thomson scattering can measure `electron_density`
- **No** → Consider whether device context is essential to physical meaning

**4. Is this a raw/calibrated signal or a derived physics quantity?**

- **Raw/calibrated signal** → `<device>_<signal>` pattern preferred
- **Derived physics quantity** → Generic name preferred

### Pattern Examples

**Device signals and properties:**

```text
flux_loop_voltage                          (induced voltage in the loop)
passive_loop_current                       (eddy current in the conductor)
poloidal_magnetic_field_probe_voltage      (probe output signal)
interferometer_beam_phase                  (phase of the beam)
soft_xray_detector_etendue                 (detector geometric property)
interferometer_beam_path_length            (beam-specific geometry)
```

**Physics quantities (device in metadata):**

```text
electron_density                           (measured by various diagnostics)
poloidal_magnetic_flux                     (measured by flux loops)
plasma_current                             (measured by multiple methods)
magnetic_field                             (measured by probes at various locations)
```

### Rationale

This separation follows fusion metadata conventions:

- **Standard names identify what** (the physical/geometric quantity)
- **Metadata describes how/where** (measurement method, device ID, processing)

Device signals are different: the device **is** the physical system being described, not just the measurement apparatus.

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

Distinguish intrinsic properties from device signals:

**Device signals (quantity is device property):**

```text
flux_loop_voltage                       (induced voltage in the loop)
passive_loop_current                    (eddy current in the conductor)
poloidal_magnetic_field_probe_voltage   (probe output signal)
```

**Intrinsic properties (property of device):**

```text
area_of_flux_loop                       (loop geometric property)
major_radius_of_poloidal_field_coil     (coil dimension)
number_of_turns_of_flux_loop            (hardware parameter)
```

**Physics quantities (measured by device, documented in metadata):**

```text
electron_density                        (plasma property)
poloidal_magnetic_flux                  (field quantity)
plasma_current                          (global quantity)
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

## Description Writing Principles

Descriptions should focus on the physical or geometric meaning of the quantity, not on how the data is organized or stored. Tags capture structural and organizational metadata, while descriptions capture semantic content.

### Core Principle: Separate Organization from Meaning

Describe what the data represents, not how it is organized.

**Key distinctions:**

- Tags capture structural properties: `spatial-profile`, `time-dependent`, `flux-surface-average`
- Descriptions capture physical meaning: what quantity, what domain, what physics

### Tag Implications

Certain tags already convey structural information. Avoid repeating this in descriptions:

**Spatial structure tags:**

- `spatial-profile` — implies radial/poloidal profiles, 1D/2D/3D arrays
- Avoid: "Radial profile of...", "1D profile of...", "Profile of..."
- Prefer: "Temperature distribution", "Density variation"

**Temporal structure tags:**

- `time-dependent` — implies time series, evolution, dynamic behavior
- Avoid: "Time series of...", "Evolution of...", "Time trace of..."
- Prefer: "Plasma current", "Temperature"

**Averaging/integration tags:**

- `flux-surface-average` — categorizes quantities involving flux surface averaging
- `volume-average` — categorizes quantities involving volume integration
- `line-integrated` — categorizes quantities involving line integrals

**When operations define the quantity:**

Mathematical operations (averaging, integration, differentiation) should appear in descriptions when they define what the quantity fundamentally is, not when they describe data processing:

- Include operation when it **defines** the quantity: The operation creates a physically distinct quantity
- Omit operation when it describes **processing**: The operation is applied to an existing quantity for analysis

Examples where operation defines the quantity:

- Geometric moments and flux-surface-averaged geometric properties (operation creates new quantity)
- Derivatives and gradients (operation fundamentally transforms the quantity)
- Line-integrated densities (integration defines the observable)

Examples where operation describes processing:

- Temperature or pressure that happens to be flux-surface-averaged for transport analysis
- Density profiles that are volume-averaged for comparison

**Rule of thumb:** When the standard name contains the operation term (e.g., `flux_surface_averaged_`, `derivative_of_`, `gradient_of_`), the description typically should too.

**Data provenance tags:**

- `measured` — observational/experimental data from diagnostics
- `reconstructed` — derived from inverse problems (equilibrium reconstruction, tomography, fitting)
- `calibrated` — processed/calibrated diagnostic signals
- `raw-data` — unprocessed diagnostic signals
- These tags categorize data use cases and are **appropriate to use**
- Avoid: Including "measured" or "reconstructed" **in the standard name itself**
- Prefer: Use the physical quantity name with appropriate provenance tag
- Note: Detailed metadata fields (measurement method, device ID, etc.) are defined by fusion metadata conventions, not by standard names

### Structural Phrases to Avoid

These phrases leak structural/organizational metadata into descriptions:

- "stored on profiles_1d" — storage detail, not physics
- "calculated from" — provenance, not definition
- "1D/2D/3D array" — data structure, not meaning
- "time_slice" — IMAS DD path structure, not physics

### Examples

Effect of spatial-profile tag:

```yaml
# Problematic
name: electron_temperature
tags: [core-physics, spatial-profile]
description: Radial profile of electron temperature

# Better
name: electron_temperature
tags: [core-physics, spatial-profile]
description: Electron temperature distribution in the plasma
```

Effect of time-dependent tag:

```yaml
# Problematic
name: plasma_current
tags: [equilibrium, time-dependent]
description: Time evolution of total plasma current

# Better
name: plasma_current
tags: [equilibrium, time-dependent]
description: Total toroidal current flowing in the plasma
```

Effect of flux-surface-average and operation tags:

```yaml
# Operation in name → operation in description (defines quantity):
name: flux_surface_averaged_major_radius
tags: [equilibrium, flux-surface-average, spatial-profile]
description: Flux surface averaged major radius

name: time_derivative_of_magnetic_field
tags: [equilibrium, time-dependent]
description: Time derivative of magnetic field

# No operation in name → no operation in description (processing):
name: pressure
tags: [core-physics, flux-surface-average]
description: Plasma pressure including thermal and magnetic components

name: electron_temperature
tags: [core-physics, spatial-profile, flux-surface-average]
description: Electron temperature
```

### When Structural Context is Needed

In rare cases, structural context helps clarify ambiguous quantities. Use metadata fields instead:

- `documentation` field for detailed context
- `links` field for references to other standard names
- `provenance` field for derivation relationships

### Validation

The description validation system warns about potential tag-description redundancy:

- Detected during entry creation and modification
- Returns warnings, not errors (allows informed overrides)
- Available via `validate_catalog` tool with `checks=["descriptions"]`

**Important:** Validation warnings about operation terms (averaging, derivatives, gradients) appearing in both name and description may be false positives. If the operation term appears in the standard name itself, it typically should appear in the description too, as the operation defines the quantity rather than describing processing.

---

## Vocabulary Management

The grammar uses controlled vocabularies for six segments. The vocabulary management tool helps identify gaps, validate tokens, and maintain consistency.

### Controlled Vocabularies

1. **components** — Vector directions (`radial`, `toroidal`, `vertical`, `x`, `y`, `z`)
2. **subjects** — Particle species (`electron`, `ion`, `deuterium`, `tritium`)
3. **geometric_bases** — Spatial quantities (`position`, `vertex`, `centroid`, `outline`)
4. **objects** — Hardware/equipment (`flux_loop`, `antenna`, `coil`, `limiter`)
5. **positions** — Spatial locations (`magnetic_axis`, `separatrix`, `midplane`)
6. **processes** — Physical mechanisms (`collisions`, `turbulence`, `transport`)

### Vocabulary Operations

The `manage_vocabulary` tool supports five operations:

#### List Vocabularies

View all tokens in a vocabulary with usage statistics:

```json
{
  "action": "list",
  "segment": "components",
  "include_usage": true
}
```

#### Audit for Gaps

Scan the catalog to find tokens used in standard names but missing from vocabularies:

```json
{
  "action": "audit",
  "vocabulary": "positions",
  "frequency_threshold": 3
}
```

Returns missing tokens with:

- Frequency count
- Evidence quality (`robust`, `strong`, `moderate`, `weak`)
- Affected standard names
- Recommendations

#### Check Specific Name

Validate if a specific standard name uses only existing vocabulary tokens:

```json
{
  "action": "check",
  "name": "radial_position_of_flux_loop"
}
```

Returns parsing result and identifies any vocabulary gaps.

#### Add Tokens

Add new tokens to a vocabulary:

```json
{
  "action": "add",
  "vocabulary": "components",
  "tokens": ["helical", "spiral"]
}
```

**Response structure:**

```json
{
  "action": "add",
  "vocabulary": "components",
  "added": ["helical", "spiral"],
  "already_present": [],
  "status": "success",
  "requires_restart": true,
  "details": "Vocabulary updated and codegen completed successfully. **Important:** Restart the MCP server to load the updated grammar types."
}
```

**Status values:**

- `"success"` — Tokens added, codegen succeeded
- `"failed"` — Token format invalid OR codegen failed (see `details`)
- `"unchanged"` — All tokens already present

**Action required:** When `requires_restart: true`, restart the MCP server to load updated grammar enums.

#### Remove Tokens

Remove tokens from a vocabulary:

```json
{
  "action": "remove",
  "vocabulary": "processes",
  "tokens": ["deprecated_mechanism"]
}
```

Response structure matches `add` operation.

### Token Format Rules

All vocabulary tokens must follow these rules:

1. **Lowercase only** — `radial` ✅, `Radial` ❌
2. **Start with letter** — `x` ✅, `1st` ❌
3. **Alphanumeric + underscores** — `flux_loop` ✅, `flux-loop` ❌
4. **No double underscores** — `flux_loop` ✅, `flux__loop` ❌
5. **No leading/trailing underscores** — `radial` ✅, `_radial_` ❌
6. **No purely numeric segments** — `co2_laser` ✅, `co_2_laser` ❌

**Pattern:** `^[a-z][a-z0-9_]*[a-z0-9]$` or `^[a-z]$` (single letter)

### Workflow Example

1. **Identify gap:**

   ```json
   { "action": "audit", "frequency_threshold": 3 }
   ```

2. **Review recommendations:**

   ```json
   {
     "missing_tokens": {
       "positions": [{
         "token": "x_point",
         "frequency": 5,
         "evidence_quality": "robust",
         "affected_names": ["position_of_x_point", ...]
       }]
     }
   }
   ```

3. **Add token:**

   ```json
   {
     "action": "add",
     "vocabulary": "positions",
     "tokens": ["x_point"]
   }
   ```

4. **Restart server** (when `requires_restart: true`)

5. **Verify:**
   ```json
   { "action": "check", "name": "position_of_x_point" }
   ```

---

## Quick Reference

**Complete vocabularies:** [Grammar Reference](grammar-reference.md#vocabularies)

**Step-by-step guide:** [Quick Start](development/quickstart.md)

**Authoring rules:** [Style Guide](development/style-guide.md)

**Formal specification:** [Specification](development/specification.md)
