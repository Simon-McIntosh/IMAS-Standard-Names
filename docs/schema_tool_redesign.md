# Schema Tool Redesign - Design Document

## Problems with Current Implementation

1. **Too much duplication**: Full JSON schemas in both overview and section='all'
2. **Wrong focus**: Emphasizes provenance models, de-emphasizes practical YAML structure
3. **Minimal sections**: 'name' and 'validation' produce trivial output
4. **No clear entry type hierarchy**: Scalar/vector/metadata not prominently shown
5. **Examples not in YAML**: Shows Python dicts instead of copy-paste-ready YAML

## New Design Principles

1. **Laser focus on YAML catalog entries** - this tool is about creating entries, not parsing names
2. **Show, don't tell** - provide complete YAML examples with inline comments
3. **Three entry types front-and-center** - scalar (most common), vector, metadata
4. **Minimal → Full progression** - show required fields first, then optional enrichment
5. **Remove duplication** - each piece of info appears once in optimal location

## Default Overview (section=None)

```yaml
entry_types:
  scalar:
    description: "Physical quantities with single value at each point"
    required_fields: [name, description, kind: scalar]
    minimal_example: |
      name: plasma_current
      kind: scalar
      description: Total toroidal plasma current flowing in the plasma

  vector:
    description: "Vector field quantities with multiple components"
    required_fields: [name, description, kind: vector]
    minimal_example: |
      name: magnetic_field
      kind: vector
      description: Total magnetic field vector in the plasma

  metadata:
    description: "Definitional entries (boundaries, regions, concepts)"
    required_fields: [name, description, kind: metadata]
    minimal_example: |
      name: plasma_boundary
      kind: metadata
      description: Last closed flux surface defining plasma edge

field_reference:
  name: "snake_case, starts with letter, no double underscores"
  description: "One sentence (<180 chars), no IMAS DD/COCOS refs"
  kind: "scalar | vector | metadata"
  unit: "SI or eV, lexicographic order (m.s^-2), '' for dimensionless"
  status: "draft (default) | active | deprecated | superseded"
  documentation: "Standalone with LaTeX. Call section='documentation'"
  tags: "tags[0]=PRIMARY, tags[1:]=secondary. Call section='tags'"
  links: "Internal 'name:' refs ONLY, NO DD URLs. Call section='links'"

workflow:
  1: "get_naming_grammar → compose valid name"
  2: "get_schema kind='scalar' → review scalar schema"
  3: "Write minimal entry (name, kind, description)"
  4: "section='documentation' → add standalone docs"
  5: "section='links' → add cross-references"
  6: "create_standard_names(entries=[...]) → stage"
  7: "write_standard_names() → persist"

complete_example: |
  name: electron_temperature
  kind: scalar
  description: Kinetic temperature of electrons in the plasma
  unit: eV
  status: active
  tags:
  - core-physics          # PRIMARY tag (tags[0])
  - spatial-profile       # secondary tags
  - measured
  documentation: |
    Electron kinetic temperature $T_e$ characterizing thermal state of
    electron population. In fusion plasmas, ranges from tens of eV at
    edge to several keV in core.
    
    **Typical values**: 100 eV (edge) to 10+ keV (core)
    
    **Diagnostic methods**: Thomson scattering (primary), ECE, X-ray
    
  links:
  - name:ion_temperature
  - name:electron_density
```

## Section Structure

### Keep: Enhanced Sections

1. **section='tags'** - Critical: primary/secondary vocabulary + ordering rules
2. **section='documentation'** - Critical: LaTeX formatting + standalone requirements
3. **section='links'** - Critical: DD prohibition + format rules
4. **section='yaml'** - NEW: Annotated complete YAML for all three types
5. **section='examples'** - Enhanced: Real YAML from catalog, not JSON dicts
6. **section='all'** - Complete reference with JSON schemas

### Remove: Merge into Overview

1. **section='name'** - Trivial pattern, shown in field_reference
2. **section='validation'** - Trivial rules, shown in field_reference
3. **section='description'** - Just max length, shown in field_reference
4. **section='unit'** - Just pattern, shown in field_reference
5. **section='provenance'** - Move to section='all' only (advanced users)

## New section='yaml'

Shows three complete annotated YAML examples:

```yaml
# SCALAR ENTRY - most common type
name: electron_temperature           # Required: snake_case pattern
kind: scalar                         # Required: entry type discriminator
description: Kinetic temperature of electrons in the plasma  # Required: one sentence
unit: eV                            # Optional: SI or eV, lexicographic order
status: active                      # Optional: draft|active|deprecated|superseded (default: draft)
tags:                              # Optional: controlled vocabulary
- core-physics                     #   tags[0] MUST be primary tag
- spatial-profile                  #   tags[1:] are secondary tags
- measured
documentation: |                   # Optional: standalone explanation with LaTeX
  Electron kinetic temperature $T_e$ ...

  **Typical values**: 100 eV to 10 keV

links:                            # Optional: internal 'name:' cross-refs only
- name:ion_temperature
- name:electron_density
constraints:                      # Optional: physical bounds
- T_e >= 0
validity_domain: core_plasma      # Optional: core_plasma|edge_plasma|vacuum|whole_plasma|whole_device

# VECTOR ENTRY - for vector fields
name: magnetic_field
kind: vector                       # Vector quantities have multiple components
description: Total magnetic field vector in the plasma
unit: T
# ... same optional fields as scalar

# METADATA ENTRY - for definitions
name: plasma_boundary
kind: metadata                     # Definitional, not measurable
description: Last closed flux surface defining plasma edge
# metadata entries don't require units
# ... same optional fields as scalar/vector
```

## Implementation Plan

1. Rewrite `_get_schema_overview()` with new structure
2. Add `_get_schema_section_yaml()` method
3. Update `_get_schema_examples()` to output YAML strings not dicts
4. Remove route handlers for removed sections
5. Simplify section='all' (less duplication with overview)
6. Update tests
