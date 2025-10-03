# Guidelines for Construction of IMAS Standard Names

!!! info "Complete Reference"
For auto-generated vocabulary tables and formal specification, see the [Grammar Reference](grammar-reference.md).

## Basic Rules

Standard names follow these fundamental requirements:

| Rule           | Description                                 | Example                                              |
| -------------- | ------------------------------------------- | ---------------------------------------------------- |
| **Characters** | Lowercase letters, digits, underscores only | `electron_temperature` ✓<br>`Electron_Temperature` ✗ |
| **Start**      | Must begin with a letter                    | `temperature` ✓<br>`1_temperature` ✗                 |
| **Spelling**   | Use US spelling                             | `analyze`, `center`                                  |
| **Units**      | Never include units in the name             | `temperature` ✓<br>`temperature_ev` ✗                |
| **Order**      | Follow fixed segment order (see below)      | Must respect grammar                                 |

## Grammar Structure

Standard names are constructed from segments in a fixed order:

{{ grammar_segment_order() }}

### Segment Descriptions

!!! info "Auto-Generated Vocabularies"
Token lists below are generated from `grammar.yml`. See [Grammar Reference](grammar-reference.md) for complete tables.

| Segment       | Required | Description                                      | Tokens                                                                    |
| ------------- | -------- | ------------------------------------------------ | ------------------------------------------------------------------------- |
| **component** | No       | Vector component direction                       | {{ grammar_component_tokens() }}                                          |
| **subject**   | No       | Particle species or plasma subject               | {{ grammar_subject_tokens() }}                                            |
| **base**      | **Yes**  | Physical quantity or transformed expression      | User-defined (e.g., `temperature`, `pressure`, `gradient_of_temperature`) |
| **basis**     | No       | Coordinate system (template: `in_{token}_basis`) | {{ grammar_basis_tokens() }}                                              |
| **geometry**  | No       | Geometric target (template: `of_{token}`)        | {{ grammar_position_tokens() }}                                           |
| **position**  | No       | Spatial location (template: `at_{token}`)        | {{ grammar_position_tokens() }}                                           |
| **process**   | No       | Physical mechanism (template: `due_to_{token}`)  | {{ grammar_process_tokens() }}                                            |

### Exclusivity Rules

Certain segments cannot coexist in the same name:

{{ grammar_exclusive_pairs() }}

### Examples

| Valid Name                                   | Segments Used             | Explanation                   |
| -------------------------------------------- | ------------------------- | ----------------------------- |
| `electron_temperature`                       | subject + base            | Simple scalar                 |
| `radial_component_of_magnetic_field`         | component + base          | Vector component              |
| `electron_temperature_at_plasma_boundary`    | subject + base + position | Scalar at location            |
| `heat_flux_due_to_conduction`                | base + process            | Process contribution          |
| `radial_magnetic_field_in_cylindrical_basis` | component + base + basis  | Component with explicit basis |

## Grammar Source

**Single source of truth:** `imas_standard_names/resources/grammar.yml`

**Code generation:**

- Auto-generates: `imas_standard_names/grammar/types.py` (Python enums)
- Triggers: Automatically during build/install via Hatch
- Manual: `python -m imas_standard_names.grammar_codegen.generate` or `build-grammar`

---

## Vocabulary Details

### Components

Component tokens specify vector directions. Available components depend on the coordinate basis:

{{ grammar_basis_components() }}

**All component tokens:**

{{ grammar_vocabulary_table('components') }}

**Consistency rules:**

- Component tokens must match the declared or implied basis
- Do not mix component vocabularies (e.g., no `x` with cylindrical basis)

**Examples:**

- `radial_component_of_magnetic_field` — cylindrical component
- `x_component_of_electric_field` — Cartesian component
- `parallel_heat_flux` — field-aligned component

### Subjects

Subject tokens identify particle species or plasma populations:

{{ grammar_vocabulary_table('subjects') }}

**Examples:**

- `electron_temperature` — electron quantity
- `ion_density` — ion quantity
- `deuterium_velocity` — specific isotope

### Positions

Position tokens (template: `at_{token}`) specify spatial locations:

{{ grammar_vocabulary_table('positions') }}

**Examples:**

- `temperature_at_plasma_boundary` — at last closed flux surface
- `pressure_at_magnetic_axis` — on-axis value
- `density_at_outer_midplane` — at specific location

### Processes

Process tokens (template: `due_to_{token}`) identify physical mechanisms. Use when naming a single contribution term in a sum:

{{ grammar_vocabulary_table('processes') }}

**Examples:**

- `heat_flux_due_to_conduction` — conductive contribution
- `particle_flux_due_to_diffusion` — diffusive contribution
- `heating_due_to_neutral_beam_injection` — NBI heating term

### Basis

Basis tokens (template: `in_{token}_basis`) specify coordinate systems:

{{ grammar_vocabulary_table('basis') }}

**Usage:**

- Primarily for vector forms with component dimension
- Rare for scalar quantities
- Must match component token vocabulary

---

## Vector Representation

Vectors can be represented in two ways:

### 1. Component Form (Recommended)

Publish separate scalar variables for each component. The component token implies the basis.

**Available basis/component mappings:**

{{ grammar_basis_components() }}

**Examples:**

| Basis         | Component Names                                                               | Unit |
| ------------- | ----------------------------------------------------------------------------- | ---- |
| Cartesian     | `x_magnetic_field`, `y_magnetic_field`, `z_magnetic_field`                    | T    |
| Cylindrical   | `radial_magnetic_field`, `toroidal_magnetic_field`, `vertical_magnetic_field` | T    |
| Field-aligned | `parallel_heat_flux`, `perpendicular_heat_flux`                               | W/m² |

### 2. Vector Form (Single Array)

Publish single variable with component dimension. Include basis explicitly in name (template: `in_{basis}_basis`).

**Examples:**

| Vector Name                                              | Component Labels                     | Notes                   |
| -------------------------------------------------------- | ------------------------------------ | ----------------------- |
| `magnetic_field_in_cartesian_basis`                      | `["x", "y", "z"]`                    | Explicit basis          |
| `magnetic_field_in_cylindrical_basis`                    | `["radial", "toroidal", "vertical"]` | Can append position     |
| `magnetic_field_in_cylindrical_basis_at_plasma_boundary` | `["radial", "toroidal", "vertical"]` | With position qualifier |

### Vector Naming Rules

- ✗ Never use the word "vector" in names → ✓ Use component or basis forms
- ✓ For magnitudes: `magnitude_of_magnetic_field` (scalar, not vector)
- ✓ Component labels in vector form must match declared basis
- ✗ Never mix component vocabularies in a single set

---

## Transformations

Derive new standard names from existing ones by applying transformation operators. Transformations may change units. Multiple transformations can be chained.

### Transformation Rules

{{ read_csv('transformations.csv') }}

### Transformation Examples

| Standard Name                                          | Transformation    | Description               |
| ------------------------------------------------------ | ----------------- | ------------------------- |
| `gradient_of_temperature`                              | gradient          | Spatial gradient          |
| `time_derivative_of_pressure`                          | time derivative   | Rate of change            |
| `magnitude_of_magnetic_field`                          | magnitude         | Vector magnitude (scalar) |
| `integral_of_density_over_volume`                      | integral          | Volume integration        |
| `ratio_of_thermal_pressure_to_magnetic_pressure`       | ratio             | Plasma beta               |
| `square_of_magnetic_field`                             | square            | Squared quantity          |
| `normalized_temperature`                               | normalized        | Dimensionless form        |
| `derivative_of_current_density_with_respect_to_radius` | derivative w.r.t. | Radial derivative         |

---

## Generic Quantity Names

Generic names represent physical quantities with consistent units across the catalog. These are building blocks for standard names but **are not themselves valid standard names**.

{{ read_csv('generic_names.csv') }}

### Unit Conventions

| Quantity Type         | Unit | Examples                                  |
| --------------------- | ---- | ----------------------------------------- |
| Plasma temperatures   | eV   | `electron_temperature`, `ion_temperature` |
| Material temperatures | K    | `wall_temperature`, `coil_temperature`    |
| Magnetic field        | T    | `toroidal_magnetic_field`                 |
| Density               | m⁻³  | `electron_density`, `ion_density`         |
| Energy                | J    | `plasma_energy`, `kinetic_energy`         |

---

## Quick Reference

**For complete vocabulary tables and formal specification:** See [Grammar Reference](grammar-reference.md)

**For step-by-step creation guide:** See [Quick Start](quickstart.md)

**For detailed authoring rules:** See [Style Guide](style-guide.md)

**For formal grammar and validation:** See [Specification](specification.md)
