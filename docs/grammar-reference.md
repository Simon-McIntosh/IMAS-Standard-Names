# Grammar Reference (Auto-Generated)

!!! info "Single Source of Truth"
This page is automatically generated from `imas_standard_names/resources/grammar.yml`
and reflects the current authoritative grammar at build time.

    **All content on this page is generated programmatically** — do not edit manually.

## Overview

The IMAS Standard Names grammar defines a structured, deterministic naming convention
for fusion data variables. Names are composed of segments in a fixed order, with
each segment drawing from controlled vocabularies.

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

Component tokens specify the direction of vector components.

{{ grammar_vocabulary_table('components') }}

### Subjects

Subject tokens specify the particle species or plasma component:

{{ grammar_vocabulary_table('subjects') }}

### Positions

Position tokens specify spatial locations or regions within the plasma:

{{ grammar_vocabulary_table('positions') }}

### Processes

Process tokens specify physical mechanisms or processes:

{{ grammar_vocabulary_table('processes') }}

---

## Exclusivity Rules

Certain segments cannot appear together in the same standard name:

{{ grammar_exclusive_pairs() }}

---

## Examples

### Valid Names

Using the grammar rules above, here are examples of valid standard names:

**Base scalars:**

- `electron_temperature` — simple subject + base
- `ion_density` — subject + base

**Components:**

- `radial_component_of_magnetic_field` — component + vector
- `toroidal_component_of_plasma_velocity` — component + vector

**With position:**

- `electron_temperature_at_plasma_boundary` — scalar + position
- `radial_component_of_magnetic_field_at_magnetic_axis` — component + vector + position

**With process:**

- `heat_flux_due_to_conduction` — scalar + process
- `particle_flux_due_to_diffusion` — scalar + process

**Complex:**

- `electron_temperature_at_outer_midplane_due_to_electron_cyclotron_heating` — subject + base + position + process

### Invalid Names

Examples that violate the grammar:

❌ `magnetic_field_radial_component` — component must come first  
❌ `at_plasma_boundary_electron_temperature` — segments out of order  
❌ `electron_temperature_at_plasma_boundary_of_magnetic_axis` — both position and geometry (exclusive)

---

## Grammar Version

{{ grammar_version() }}

---

## Parser Implementation

The grammar is implemented in the following modules:

- **Grammar Specification:** `imas_standard_names/resources/grammar.yml`
- **Type Generation:** `imas_standard_names/grammar_codegen/generate.py`
- **Runtime Types:** `imas_standard_names/grammar/types.py` (auto-generated)
- **Parser/Composer:** `imas_standard_names/grammar/support.py`
- **Pydantic Models:** `imas_standard_names/grammar/model.py`

See the [specification](specification.md) for detailed semantic rules and validation requirements.
