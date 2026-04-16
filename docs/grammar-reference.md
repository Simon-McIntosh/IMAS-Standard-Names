# Grammar Reference

!!! info "Auto-Generated from Grammar Specification"
This page is automatically generated from `imas_standard_names/grammar/specification.yml`
and reflects the current authoritative grammar at build time.

## Overview

The IMAS Standard Names grammar defines a structured, deterministic naming convention
for fusion data variables. Names are composed of segments in a fixed order, with
each segment drawing from controlled vocabularies.

### Canonical Pattern

The grammar follows this pattern:

```text
[<component>_component_of | <coordinate>]?
[<subject>]?
[<device> | of_<object>]?
<geometric_base | physical_base>
[of_<geometry> | at_<position>]?
[due_to_<process>]?
```

**Key concepts:**

- **Split Base Structure**: Names must have either a `geometric_base` (spatial/geometric quantities) OR a `physical_base` (physical measurements/properties), but not both.
- **component vs coordinate**: Use `component` for physical vectors (with `physical_base`), use `coordinate` for geometric vectors (with `geometric_base`).
- **device vs object**: Use `<device>_<signal>` for dynamic signals FROM device (e.g., `flux_loop_voltage`); use `<property>_of_<object>` for static properties OF object (e.g., `area_of_flux_loop`).
- **of_geometry vs at_position**: Use `of_<geometry>` for geometric properties OF spatial objects; use `at_<position>` for fields evaluated AT locations.

### Vocabularies Summary

{{ grammar_all_vocabularies() }}

---

## Segment Order

The canonical order for constructing standard names:

{{ grammar_segment_order() }}

---

## Segment Rules

Detailed rules for each segment, including optionality, templates, and exclusivity constraints:

{{ grammar_segment_rules_table() }}

---

## Vocabularies

### Components

Component tokens specify the direction of physical or geometric vector components.
Available directions include `radial`, `poloidal`, `toroidal`, `parallel`, `perpendicular`,
and others.

**Usage:**

- Physical vectors: `{token}_component_of_{physical_vector}` (e.g., `radial_component_of_magnetic_field`)
- Geometric vectors: `{token}_{geometric_base}` (e.g., `radial_position_of_flux_loop`)

{{ grammar_vocabulary_table('components') }}

### Subjects

Subject tokens specify the particle species or plasma population.
Subjects are organized in tiers: core species (electron, ion, neutral), hydrogenic
isotopes (hydrogen, deuterium, tritium), impurity elements (helium, beryllium, carbon,
nitrogen, neon, argon, tungsten, lithium), extended species (alpha particle, fast ion),
and reaction mixtures (deuterium-tritium).

{{ grammar_vocabulary_table('subjects') }}

### Geometric Bases

Geometric bases represent spatial/geometric quantities like positions, vertices, centroids, etc. These must be qualified with an `object` or `geometry` segment.

**Usage:** `{coordinate}_{geometric_base}_of_{object}` or `{coordinate}_{geometric_base}_at_{geometry}`

{{ grammar_vocabulary_table('geometric_bases') }}

### Objects

Object tokens specify physical hardware or equipment whose intrinsic properties are described.

**Template:** `of_{token}`

**Examples:**

- `major_radius_of_flux_loop` — intrinsic geometric property
- `area_of_poloidal_magnetic_field_probe` — equipment characteristic

{{ grammar_vocabulary_table('objects') }}

### Positions

Position tokens specify spatial locations or regions within the plasma.

**Templates:**

- Geometry: `of_{token}` — intrinsic property of geometric object
- Position: `at_{token}` — field evaluated at location

{{ grammar_vocabulary_table('positions') }}

### Processes

Process tokens specify physical mechanisms or processes. Categories include energy
transport (conduction, convection, radiation), particle transport (diffusion), fueling
(gas_puff, pellet_injection), and fusion reactions (fusion, deuterium_tritium_fusion).

{{ grammar_vocabulary_table('processes') }}

### Transformations

Transformation tokens modify a physical base by applying a mathematical operation.
Transformations are prefixed to the physical base.

**Template:** `{transformation}_{physical_base}`

**Examples:**

- `square_of_electron_temperature` — square of temperature
- `volume_averaged_electron_density` — spatial average
- `time_derivative_of_magnetic_flux` — temporal derivative
- `maximum_over_flux_surface_electron_pressure` — extremum over surface

**Categories:**

- **Existing:** `square_of`, `change_over_time_in`, `logarithm_of`, `inverse_of`
- **Scaling:** `normalized`
- **Spatial averages:** `volume_averaged`, `flux_surface_averaged`, `line_averaged`
- **Spatial integrals:** `surface_integrated`, `volume_integrated`
- **Temporal:** `time_integrated`, `time_derivative_of`
- **Extrema:** `maximum_of`, `minimum_of`, `maximum_over_flux_surface`, `minimum_over_flux_surface`
- **Calculus:** `derivative_of`, `radial_derivative_of`

**Note:** `time_derivative_of` and `change_over_time_in` are both valid transformation tokens
describing the same mathematical operation. The parser accepts either form.

**Exclusivity:** Transformations cannot be combined with `component`, `coordinate`, or `geometric_base`.

{{ grammar_vocabulary_table('transformations') }}

---

## Exclusivity Rules

Certain segments cannot appear together in the same standard name:

{{ grammar_exclusive_pairs() }}

---

## Examples

### Valid Names Using Split Base Structure

**Geometric base examples (spatial/geometric quantities):**

- `position_of_flux_loop` — geometric_base with object
- `radial_position_of_flux_loop` — coordinate + geometric_base + object
- `vertex_of_plasma_boundary` — geometric_base with geometry
- `toroidal_centroid_of_divertor_tile` — coordinate + geometric_base + object

**Physical base examples (measurements/physical properties):**

- `electron_temperature` — subject + physical_base
- `magnetic_field` — physical_base (vector)
- `radial_component_of_magnetic_field` — component + physical_base
- `flux_loop_voltage` — device + physical_base (device signal)
- `area_of_poloidal_magnetic_field_probe` — physical_base + object

**With position or geometry:**

- `electron_temperature_at_plasma_boundary` — physical scalar + position
- `radial_component_of_magnetic_field_at_magnetic_axis` — component + physical_base + position
- `major_radius_of_plasma_boundary` — physical_base + geometry

**With process:**

- `heat_flux_due_to_conduction` — physical_base + process
- `particle_flux_due_to_diffusion` — physical_base + process

### Invalid Names

Examples that violate the grammar:

❌ `magnetic_field_radial_component` — component must come first  
❌ `at_plasma_boundary_electron_temperature` — segments out of order  
❌ `electron_temperature_at_plasma_boundary_of_magnetic_axis` — both position and geometry (mutually exclusive)  
❌ `radial_component_of_position` — component requires physical_base, not geometric_base  
❌ `radial_position_component_of_flux_loop` — should use coordinate form, not component

---

## Implementation

The grammar lives in these modules:

- **Grammar Specification:** `imas_standard_names/grammar/specification.yml`
- **Type Generation:** `imas_standard_names/grammar_codegen/generate.py`
- **Runtime Types:** `imas_standard_names/grammar/types.py` (auto-generated)
- **Parser/Composer:** `imas_standard_names/grammar/support.py`
- **Pydantic Models:** `imas_standard_names/grammar/model.py`

See the [specification](development/specification.md) for detailed semantic rules and validation requirements.
