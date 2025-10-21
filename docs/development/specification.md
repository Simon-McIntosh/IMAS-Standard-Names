# IMAS Standard Names Specification

## Overview

This specification defines the canonical grammar, validation rules, and semantic constraints for IMAS Standard Names. The grammar provides a structured, deterministic naming convention for fusion data variables.

**Single Source of Truth:** `imas_standard_names/grammar/specification.yml`

**Auto-Generated Code:** `imas_standard_names/grammar/types.py` (Python enums and metadata)

### Design Principles

| Principle              | Description                                                                 |
| ---------------------- | --------------------------------------------------------------------------- |
| Deterministic Parsing  | Names decompose unambiguously via grammar rules                             |
| Controlled Vocabulary  | Segments use enumerated tokens from specification.yml                       |
| Canonical Form         | Exactly one valid name per concept                                          |
| IMAS DD Alignment      | Sign conventions, coordinates, units follow IMAS Data Dictionary            |
| Segment Order          | Fixed left-to-right sequence enforced                                       |
| Split Base Structure   | Geometric vs physical bases are mutually exclusive                          |

---

## Grammar Structure

### Canonical Pattern

```text
[<component>_component_of | <coordinate>]? 
[<subject>]? 
<geometric_base | physical_base> 
[of_<object> | from_<source>]? 
[of_<geometry> | at_<position>]? 
[due_to_<process>]?
```

### Segment Definitions

For detailed segment descriptions and auto-generated vocabulary tables, see [Grammar Reference](../grammar-reference.md).

| Segment          | Required | Description                                      | Exclusive With   |
| ---------------- | -------- | ------------------------------------------------ | ---------------- |
| component        | No       | Physical vector component direction              | coordinate       |
| coordinate       | No       | Geometric vector coordinate axis                 | component        |
| subject          | No       | Particle species or plasma population            |                 |
| geometric_base   | No*      | Spatial/geometric quantity                       | physical_base    |
| physical_base    | No*      | Physical measurement/property                    | geometric_base   |
| object           | No       | Hardware whose property is described (of_)       | source           |
| source           | No       | Device from which measurement obtained (from_)   | object           |
| geometry         | No       | Geometric object property (of_)                  | position         |
| position         | No       | Location where field evaluated (at_)             | geometry         |
| process          | No       | Physical mechanism (due_to_)                     |                 |

*One of geometric_base or physical_base is required.

### Split Base Semantics

**Geometric Base:**

- Represents spatial/geometric quantities: position, vertex, centroid, outline, displacement, etc.
- Must be qualified with object or geometry segment
- Uses `coordinate` prefix for vector components (not `component`)
- Example: `radial_position_of_flux_loop`, `vertex_of_plasma_boundary`

**Physical Base:**

- Represents physical measurements, fields, or properties
- Open-ended vocabulary (defined in catalog entries, not grammar)
- Uses `component` prefix for vector components
- Example: `electron_temperature`, `radial_component_of_magnetic_field`, `voltage_from_flux_loop`

### Segment Templates

| Segment   | Template                         | Example                                      |
| --------- | -------------------------------- | -------------------------------------------- |
| component | `{token}_component_of_`        | `radial_component_of_magnetic_field`       |
| coordinate| `{token}_`                     | `radial_position_of_flux_loop`             |
| object    | `of_{token}`                   | `area_of_flux_loop`                        |
| source    | `from_{token}`                 | `voltage_from_flux_loop`                   |
| geometry  | `of_{token}`                   | `major_radius_of_plasma_boundary`          |
| position  | `at_{token}`                   | `electron_temperature_at_magnetic_axis`    |
| process   | `due_to_{token}`               | `heat_flux_due_to_conduction`              |

---

## Validation Rules

### Structural Invariants

| Rule ID | Description                                                    |
| ------- | -------------------------------------------------------------- |
| GRM001  | Name must contain exactly one base (geometric_base XOR physical_base) |
| GRM002  | Segment order must follow canonical pattern                    |
| GRM003  | component and coordinate are mutually exclusive                |
| GRM004  | object and source are mutually exclusive                       |
| GRM005  | geometry and position are mutually exclusive                   |
| GRM006  | coordinate requires geometric_base                             |
| GRM007  | component requires physical_base                               |
| GRM008  | All vocabulary tokens must exist in specification.yml          |

### Semantic Constraints

| Rule ID | Description                                                    |
| ------- | -------------------------------------------------------------- |
| SEM001  | geometric_base must be qualified with object or geometry       |
| SEM002  | Sign conventions must follow IMAS DD documentation             |
| SEM003  | Units must be SI-consistent and match IMAS DD where applicable |
| SEM004  | First tag (tags[0]) must be primary tag from controlled list   |
| SEM005  | Provenance dependencies must form a DAG (no cycles)            |

---

## Provenance

Standard names may include a `provenance` block describing their derivation. See [Provenance](provenance.md) for detailed schema.

### Provenance Modes

| Mode       | Description                               | Example                          |
| ---------- | ----------------------------------------- | -------------------------------- |
| operator   | Derived via transformation operators      | `time_derivative_of_temperature` |
| reduction  | Scalar reduction from vector/array        | `magnitude_of_magnetic_field`    |
| expression | Explicit algebraic combination            | `ratio_of_pressure_to_field`     |

---

## Examples

### Geometric Base Examples

```text
position_of_flux_loop                     (geometric_base + object)
radial_position_of_flux_loop              (coordinate + geometric_base + object)
vertex_of_plasma_boundary                 (geometric_base + geometry)
centroid_of_divertor_tile                 (geometric_base + object)
```

### Physical Base Examples

```text
electron_temperature                      (subject + physical_base)
magnetic_field                            (physical_base)
radial_component_of_magnetic_field        (component + physical_base)
voltage_from_flux_loop                    (physical_base + source)
area_of_poloidal_magnetic_field_probe     (physical_base + object)
electron_temperature_at_magnetic_axis     (subject + physical_base + position)
major_radius_of_plasma_boundary           (physical_base + geometry)
```

### Anti-Patterns

| Invalid                                         | Violation    | Correct                                      |
| ----------------------------------------------- | ------------ | -------------------------------------------- |
| `magnetic_field_radial_component`             | Segment order| `radial_component_of_magnetic_field`       |
| `radial_component_of_position`                | GRM007       | `radial_position_of_flux_loop`             |
| `radial_position_component_of_flux_loop`      | GRM006       | `radial_position_of_flux_loop`             |
| `electron_temperature_at_boundary_of_axis`    | GRM005       | Pick one: at_boundary OR of_axis             |
| `voltage_of_flux_loop`                        | Semantic     | `voltage_from_flux_loop`                   |

---

## Vocabularies

All controlled vocabularies are defined in:

- `imas_standard_names/grammar/vocabularies/components.yml`
- `imas_standard_names/grammar/vocabularies/subjects.yml`
- `imas_standard_names/grammar/vocabularies/geometric_bases.yml`
- `imas_standard_names/grammar/vocabularies/objects.yml`
- `imas_standard_names/grammar/vocabularies/sources.yml`
- `imas_standard_names/grammar/vocabularies/positions.yml`
- `imas_standard_names/grammar/vocabularies/processes.yml`

See [Grammar Reference](../grammar-reference.md#vocabularies) for complete auto-generated token lists.

---

## Grammar Code Generation

The grammar specification drives automatic code generation:

1. **Source:** `imas_standard_names/grammar/specification.yml`
2. **Generator:** `imas_standard_names/grammar_codegen/generate.py`
3. **Output:** `imas_standard_names/grammar/types.py` (Python enums)
4. **Trigger:** Automatic during package build via Hatch
5. **Manual:** `python -m imas_standard_names.grammar_codegen.generate`

---

## Authoring Workflow

1. Review [Grammar Reference](../grammar-reference.md) for available vocabularies
2. Choose appropriate base type (geometric or physical)
3. Compose name following canonical pattern
4. Create YAML entry (see [Quick Start](quickstart.md))
5. Validate with catalog validator
6. Submit for review

---

## References

- **[Grammar Reference](../grammar-reference.md):** Complete vocabulary tables and rules
- **[Guidelines](../guidelines.md):** Naming conventions and patterns  
- **[Quick Start](quickstart.md):** Step-by-step authoring guide
- **[Style Guide](style-guide.md):** Detailed authoring rules
- **[Provenance](provenance.md):** Derivation schema reference
