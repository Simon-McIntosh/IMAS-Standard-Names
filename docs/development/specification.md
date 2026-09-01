# IMAS Standard Names Specification

## Overview

This specification defines the canonical grammar, validation rules, and semantic constraints for IMAS Standard Names. The grammar provides a structured, deterministic naming convention for fusion data variables.

**Single Source of Truth:** `imas_standard_names/grammar/specification.yml`

**Auto-Generated Code:** `imas_standard_names/grammar/types.py` (Python enums and metadata)

### Design Principles

| Principle             | Description                                                      |
| --------------------- | ---------------------------------------------------------------- |
| Deterministic Parsing | Names decompose unambiguously via grammar rules                  |
| Controlled Vocabulary | Segments use enumerated tokens from specification.yml            |
| Canonical Form        | Exactly one valid name per concept                               |
| IMAS DD Alignment     | Sign conventions, coordinates, units follow IMAS Data Dictionary |
| Segment Order         | Fixed left-to-right sequence enforced                            |
| Split Base Structure  | Geometric vs physical bases are mutually exclusive               |

---

## Grammar Structure

### Canonical Pattern

```text
[<operator application>]?
[<axis>_]?
[<section_plane>_plane_]?
[<ordered prefix segments>]?
[<geometry_representation>_]?
<geometry carrier | physical base>
[of_<entity> | at_<position> | over_<geometry-or-region> | along_<path>]?
[due_to_<process>]?
[<postfix operator>]?
```

### Segment Definitions

For detailed segment descriptions and auto-generated vocabulary tables, see [Grammar Reference](../grammar-reference.md).

| Segment        | Required | Description                                     | Exclusive With |
| -------------- | -------- | ----------------------------------------------- | -------------- |
| component      | No       | Axis of a physical vector projection             | coordinate     |
| coordinate     | No       | Axis of a geometry-carrier projection            | component      |
| section_plane  | No       | Plane containing a cross-sectional identity       |                |
| subject        | No       | Particle species or plasma population           |                |
| geometric_base | No\*     | Spatial/geometric quantity                      | physical_base  |
| physical_base  | No\*     | Physical measurement/property                   | geometric_base |
| geometry_representation | No | Object-local construction representation       |                |
| device         | No       | Compatibility-only hardware prefix               | object         |
| object         | No       | Preferred entity relation for signals/properties | device         |
| geometry       | No       | Geometric object property (of\_)                | position       |
| position       | No       | Location where field evaluated (at\_)           | geometry       |
| process        | No       | Physical mechanism (due*to*)                    |                |

\*One of geometric_base or physical_base is required.

### Split Base Semantics

**Geometric Base:**

- Represents spatial/geometric quantities: position, vertex, centroid, outline, displacement, etc.
- Must be qualified with object or geometry segment
- Uses `coordinate` prefix for vector components (not `component`)
- Example: `radial_position_of_flux_loop`, `vertex_of_plasma_boundary`

**Physical Base:**

- Represents physical measurements, fields, or properties
- Closed vocabulary defined in `physical_bases.yml`
- Uses a direct axis prefix for vector components
- Example: `electron_temperature`, `radial_magnetic_field`, `voltage_of_flux_loop`

### Segment Templates

| Segment    | Template                | Example                                 |
| ---------- | ----------------------- | --------------------------------------- |
| component  | `{token}_`              | `radial_magnetic_field`                 |
| coordinate | `{token}_`              | `radial_position_of_flux_loop`          |
| section_plane | `{token}_plane_`     | `poloidal_plane_cross_sectional_area_of_conductor_cross_section` |
| geometry_representation | `{token}_` | `local_circle_radius_of_passive_loop_element` |
| object     | `of_{token}`            | `voltage_of_flux_loop`                  |
| device     | `{token}_`              | `flux_loop_voltage` (compatibility only) |
| geometry   | `of_{token}`            | `radial_coordinate_of_plasma_boundary`  |
| position   | `at_{token}`            | `electron_temperature_at_magnetic_axis` |
| process    | `due_to_{token}`        | `heat_flux_due_to_conduction`           |

---

## Validation Rules

### Structural Invariants

| Rule ID | Description                                                           |
| ------- | --------------------------------------------------------------------- |
| GRM001  | Name must contain exactly one base (geometric_base XOR physical_base) |
| GRM002  | Segment order must follow canonical pattern                           |
| GRM003  | component and coordinate are mutually exclusive                       |
| GRM004  | object and device are mutually exclusive                              |
| GRM005  | geometry and position are mutually exclusive                          |
| GRM006  | coordinate requires geometric_base                                    |
| GRM007  | component requires physical_base                                      |
| GRM008  | All vocabulary tokens must exist in specification.yml                 |
| GRM009  | Cross-sectional identities must carry one registered section plane    |
| GRM010  | Local geometry representations must carry their owner locus            |

### Semantic Constraints

| Rule ID | Description                                                    |
| ------- | -------------------------------------------------------------- |
| SEM001  | geometric_base must be qualified with object or geometry       |
| SEM002  | Sign conventions must follow IMAS DD documentation             |
| SEM003  | Units must be SI-consistent and match IMAS DD where applicable |
| SEM004  | `physics_domain` must be a valid `PhysicsDomain` enum value    |
| SEM005  | Provenance dependencies must form a DAG (no cycles)            |
| SEM006  | A local-circle radius is distinct from cylindrical R and outline coordinates |
| SEM007  | Endpoint and sample order remain source provenance, not identity tokens |

---

## Provenance

Standard names may include a `provenance` block describing their derivation. See [Provenance](provenance.md) for detailed schema.

### Provenance Modes

| Mode       | Description                          | Example                          |
| ---------- | ------------------------------------ | -------------------------------- |
| operator   | Derived via transformation operators | `time_derivative_of_temperature` |
| reduction  | Scalar reduction from vector/array   | `magnitude_of_magnetic_field`    |
| expression | Explicit algebraic combination       | `ratio_of_pressure_to_field`     |

---

## Examples

### Geometric Base Examples

<!-- isn-authoring-examples:start -->
```text
position_of_flux_loop                     (geometric_base + object)
radial_position_of_flux_loop              (coordinate + geometric_base + object)
vertex_of_plasma_boundary                 (geometric_base + geometry)
centroid_of_divertor_tile                 (geometric_base + object)
```
<!-- isn-authoring-examples:end -->

### Physical Base Examples

<!-- isn-authoring-examples:start -->
```text
electron_temperature                      (subject + physical_base)
magnetic_field                            (physical_base)
radial_magnetic_field                     (component + physical_base)
voltage_of_flux_loop                      (physical_base + object)
area_of_poloidal_magnetic_field_probe     (physical_base + object)
electron_temperature_at_magnetic_axis     (subject + physical_base + position)
radial_coordinate_of_plasma_boundary      (geometry carrier + geometry)
poloidal_plane_cross_sectional_area_of_conductor_cross_section (section_plane + physical_base + object)
poloidal_plane_cross_section_of_coil_conductor (section_plane + geometric_base + object)
local_circle_radius_of_passive_loop_element    (geometry_representation + physical_base + object)
```
<!-- isn-authoring-examples:end -->

### Anti-Patterns

| Invalid                                    | Violation     | Correct                              |
| ------------------------------------------ | ------------- | ------------------------------------ |
| `magnetic_field_radial`                    | Segment order | `radial_magnetic_field`              |
| `position_radial_of_flux_loop`             | GRM006        | `radial_position_of_flux_loop`       |
| `radial_position_at_flux_loop`             | GRM005        | `radial_position_of_flux_loop`       |
| `electron_temperature_at_boundary_of_axis` | GRM005        | Pick one: at_boundary OR of_axis     |
| `voltage_from_flux_loop`                   | Semantic      | `voltage_of_flux_loop`               |
| `flux_loop_voltage`                        | Compatibility | `voltage_of_flux_loop`               |
| `cross_sectional_area_of_conductor_cross_section` | Missing plane | `poloidal_plane_cross_sectional_area_of_conductor_cross_section` |
| `radial_local_circle_radius_of_passive_loop_element` | Frame conflation | `local_circle_radius_of_passive_loop_element` |
| `first_local_circle_radius_of_passive_loop_element` | Sample order in identity | `local_circle_radius_of_passive_loop_element` |

---

## Vocabularies

All controlled vocabularies are defined in:

- `imas_standard_names/grammar/vocabularies/components.yml`
- `imas_standard_names/grammar/vocabularies/section_planes.yml`
- `imas_standard_names/grammar/vocabularies/geometry_representations.yml`
- `imas_standard_names/grammar/vocabularies/subjects.yml`
- `imas_standard_names/grammar/vocabularies/geometric_bases.yml`
- `imas_standard_names/grammar/vocabularies/objects.yml`
- `imas_standard_names/grammar/vocabularies/locus_registry.yml`
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
