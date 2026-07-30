# Grammar Reference

!!! info "Auto-Generated from Grammar Specification"
This page is automatically generated from `imas_standard_names/grammar/specification.yml`
and reflects the current authoritative grammar at build time.

## Overview

The IMAS Standard Names grammar defines a structured, deterministic naming convention
for fusion data variables. Names are composed of segments in a fixed order, with
each segment drawing from controlled vocabularies.

### Canonical Pattern

The non-operator core follows the generated segment pattern shown below.
Operators wrap that core recursively:

```text
<expression> :=
    <core>
  | <unary_prefix>_of_<expression>
  | <expression>_<unary_postfix>
  | <binary>_of_<expression>_<separator>_<expression>
```

**Key concepts:**

- **Split Base Structure**: Names must have either a `geometric_base` (spatial/geometric quantities) OR a `physical_base` (physical measurements/properties), but not both.
- **Strict authority**: `parse(name, strict=True)` is the validity oracle.
  The default parse and `validate_round_trip()` are diagnostic.
- **Recursive operators**: `StandardNameIR.operators` is outermost first;
  binary operands and explicit unary operands are themselves
  `StandardNameIR` values.
- **component vs coordinate**: An axis directly prefixes a physical vector
  component (`radial_magnetic_field`) or a geometric carrier coordinate
  (`radial_position_of_flux_loop`). The base determines which projection is
  meant; there is no `_component_of_` marker.
- **instrument and object relations**: Author both signals and intrinsic
  properties with the `of_<entity>` postfix (for example,
  `voltage_of_flux_loop` and `area_of_flux_loop`). The `<device>_<signal>`
  prefix remains parseable only for compatibility with existing names.
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

- Physical vectors: `{token}_{physical_vector}` (e.g., `radial_magnetic_field`)
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

- `radial_coordinate_of_flux_loop` — intrinsic geometric property
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

### Operators

The unified operator registry defines bare tokens, kinds, precedence,
separators, index parameters, and semantic constraints. The renderer supplies
the punctuation around the bare token:

| Kind | Template |
|------|----------|
| Unary prefix | `<op>_of_<inner>` |
| Registry-declared bare prefix | `<op>_<inner>` |
| Unary postfix | `<inner>_<op>` |
| Binary | `<op>_of_<A>_<separator>_<B>` |

Examples:

- `square_of_inverse_of_pressure` — ordered unary chain
- `square_of_magnetic_field_magnitude` — prefix outside a postfix operator
- `ratio_of_electron_density_to_ion_density` — binary ratio
- `flux_surface_averaged_ratio_of_square_of_toroidal_flux_coordinate_gradient_magnitude_to_square_of_magnetic_field_magnitude`
  — reduction over a recursive binary expression

Higher precedence wraps farther out; equal-precedence operators keep authored
order. Binary split candidates are tried right-to-left and accepted only when
both recursive operands resolve. Successful and failed substring parses are
memoized per validation mode.

#### Unary operator tokens

{{ grammar_vocabulary_table('transformations') }}

#### Binary operator surface tokens

{{ grammar_vocabulary_table('binary_operators') }}

---

## Exclusivity Rules

Certain segments cannot appear together in the same standard name:

{{ grammar_exclusive_pairs() }}

---

## Examples

### Valid Names Using Split Base Structure

<!-- isn-authoring-examples:start -->
**Geometric base examples (spatial/geometric quantities):**

- `position_of_flux_loop` — geometric_base with object
- `radial_position_of_flux_loop` — coordinate + geometric_base + object
- `vertex_of_plasma_boundary` — geometric_base with geometry
- `toroidal_centroid_of_divertor_tile` — coordinate + geometric_base + object

**Physical base examples (measurements/physical properties):**

- `electron_temperature` — subject + physical_base
- `magnetic_field` — physical_base (vector)
- `radial_magnetic_field` — component + physical_base
- `voltage_of_flux_loop` — physical_base + object (instrument signal)
- `area_of_poloidal_magnetic_field_probe` — physical_base + object

**With position or geometry:**

- `electron_temperature_at_plasma_boundary` — physical scalar + position
- `radial_magnetic_field_at_magnetic_axis` — component + physical_base + position
- `radial_coordinate_of_plasma_boundary` — geometric carrier + geometry

**With process:**

- `heat_flux_due_to_conduction` — physical_base + process
- `particle_flux_due_to_diffusion` — physical_base + process
<!-- isn-authoring-examples:end -->

### Invalid Names

Examples that violate the grammar:

❌ `magnetic_field_radial` — component must come first
❌ `at_plasma_boundary_electron_temperature` — segments out of order  
❌ `electron_temperature_at_plasma_boundary_of_magnetic_axis` — both position and geometry (mutually exclusive)  
❌ `radial_position_at_flux_loop` — an entity property uses `_of_`, not `_at_`
❌ `position_radial_of_flux_loop` — the axis prefix must precede the carrier

---

## Implementation

The package-level public surface is `parse`, `compose`, and `StandardNameIR`.
Use `parse(name, strict=True)` for validation. Use
`parse_standard_name(name)` only when a strict-valid name must also project
into the flat `StandardName` facade; valid nested binary trees may be
unrepresentable there.

See the [canonical grammar](architecture/grammar-vnext.md) for recursive
operator semantics and the [project boundary](architecture/boundary.md) for
the stable API contract.
