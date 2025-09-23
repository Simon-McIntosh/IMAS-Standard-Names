## Reusable Prompt Template: IMAS Standard Name Batch Generation

Purpose: Drive an LLM (or MCP-enabled agent) to propose VALID new IMAS Standard Names (scalars, vectors, components, derived scalars/vectors) that:

1. Obey repository specification (`docs/specification.md`) & style guide (`docs/style-guide.md`).
2. Pass current Pydantic model validators in `imas_standard_names/models.py` (notably the stricter magnitude naming rule).
3. Produce per‑entry YAML conforming to existing examples in `standard_names/magnetic_field/`.
4. Derive names from the IMAS Data Dictionary (IMAS DD) via MCP server queries when available (see `imas_standard_names/name_generator.py`).
5. Support optional domain grouping (e.g. equilibrium, diagnostics, geometry) and IMAS IDS scoping.

> NOTE – Temporary divergence: The documentation (spec/style) treats `<vector>_magnitude` as canonical. The current Pydantic validator REQUIRES the magnitude scalar name form `magnitude_of_<vector>` (vector entry must reference this name via its `magnitude` field) and rejects `<vector>_magnitude`. Until harmonized, this template defaults to validator‑safe prefix form. A switch (`magnitude_style`) allows choosing either.

---

### 1. Parameter Block (Fill or Leave Defaults)

```
{task_mode: generate|extend|refine}
{domain_group: equilibrium|diagnostics|geometry|plasma_state|transport|generic|mixed}
{imas_ids_scope: list of IDS names or 'auto'}
{exclude_ids: optional list}
{max_base_scalars: 25}
{vector_ratio: 0.2}  # approximate fraction of total proposals that are base vectors
{include_derived_vectors: true}
{include_scalar_derivatives: time_derivative, divergence, magnitude, curl (if valid), gradient}
{allowed_axes: radial,toroidal,vertical}  # extend if frame registry updated
{frame_name: cylindrical_r_tor_z}  # or other registered frame
{magnitude_style: prefix|suffix}  # prefix => magnitude_of_<vector>; suffix => <vector>_magnitude
{units_policy: infer|explicit|placeholder}
{description_length_max: 120}
{status: draft}
{batch_size: 10}  # number of *new* base scalars per batch before expansion
{batches: 2}
{novelty_check: true}  # cross-check against docs/generic_names.csv + already generated set
{emit_validation_report: true}
{output_format: yaml}  # one YAML block per file candidate
{yaml_fields_min: name,kind,unit,status,description}
{yaml_fields_full: name,kind,unit,status,description,frame,components,magnitude,axis,parent_vector,parent_operation,derivation,tags}
{dependency_expansion: full}  # include all component dependencies for derived scalars
{reject_patterns: ["__", "magnitude_of_.*_magnitude"]}
{strict_semantics: true}  # enforce operator rank rules from spec §7
```

---

### 2. High-Level Workflow (Agent Should Follow Exactly)

1. Harvest Domain Signals

   - If `imas_ids_scope=auto`, query MCP IMAS server: "List IDS and key physical fields for {domain_group}." Collect candidate physical quantities (prefer scalars).
   - Normalize raw IMAS DD field labels to lowercase underscore tokens (strip units, indices, device IDs).

2. Filter & Classify

   - Remove generic or disallowed names (see `docs/generic_names.csv`).
   - Discard names violating lexical rules (style guide §2) or containing axis tokens unnecessarily.
   - Classify into potential base scalars vs. inherent vectors (rare – only if naturally multi-component, e.g. magnetic_field, plasma_velocity).

3. Propose Base Scalars (Batch Loop)
   For each batch (size = `batch_size`, up to `batches`):

   - Select the most domain-relevant unmodeled physical quantities.
   - Ensure uniqueness against earlier batches.
   - Output YAML entries (kind: scalar, status: draft, concise description). Units: infer from physics (SI; conform to style guide §8). If unknown, choose placeholder consistent with dimension (e.g. `1` for dimensionless) ONLY if `units_policy != infer`.

4. Introduce Vectors

   - From chosen scalar set identify groups that represent components of a coherent physical vector (must have >=2 axes from `allowed_axes`). If missing components, propose new scalar component names using pattern `<axis>_component_of_<vector_expression>` but keep them as separate scalar entries.
   - Emit vector YAML with: `kind: vector`, `frame`, `components` mapping, `magnitude` (validator form: `magnitude_of_<vector>` if `magnitude_style=prefix`, else `<vector>_magnitude`). Do NOT add derived vectors yet.

5. Derived Scalars (From Vectors)

   - For each vector, if appropriate: propose magnitude scalar (style conditional), divergence (if frame + physics meaningful), optionally time derivatives, normalized variants (future – skip if uncertain).
   - Derived scalar YAML must include either `parent_operation` (operator + operand_vector) or `derivation` with `expression` + `dependencies` (see `magnetic_field_magnitude.yml` example but ADAPT name to validator form if prefix style in effect).

6. Derived Vectors

   - Apply rank-valid operators (spec §7): gradient(scalar) → vector, curl(vector) → vector (only if 3D valid), time_derivative maintains rank.
   - Chain left-to-right: outermost first (style guide §5). Stop once scalarizing operator used.
   - Each derived vector: `kind: derived_vector`, `parent_operation` {operator, operand_vector}, full `components` set, optional magnitude.

7. Dependency & Consistency Pass

   - Every component scalar lists `axis` + `parent_vector`.
   - Vector lists all component names (must already be defined as scalar or derived_scalar).
   - Derived scalar with magnitude or divergence lists dependencies = ALL base component names of parent vector.
   - Enforce rejection: no `curl_of_divergence_*`, no double magnitude, no legacy suffix derivatives.

8. Magnitude Naming Switch

   - If `magnitude_style=prefix`: Use ONLY `magnitude_of_<vector>`; disallow `<vector>_magnitude`.
   - If `magnitude_style=suffix`: Use ONLY `<vector>_magnitude`; set vector `magnitude` field to that name (NOTE: this will FAIL current Pydantic model; supply a warning comment line in output). Default is `prefix` to pass validators.

9. Validation Simulation (Pre-Flight)
   For each proposed YAML entry, conceptually check:

   - `name` regex: `^[a-z][a-z0-9_]*$`, no `__` (models.py & style §2).
   - Component naming: `<axis>_component_of_...` with axis in allowed set.
   - Vector magnitude reference matches chosen magnitude style.
   - Derived kinds specify `derivation` or `parent_operation` (models.py rule).
   - No deprecated magnitude suffix (if prefix mode active).
   - Operator rank transitions valid (spec §7).

10. Emission Order
    Output blocks grouped logically:
11. Base scalars
12. Component scalars
13. Vectors
14. Derived vectors
15. Derived scalars (magnitude/divergence/etc.)
    Provide an index summary at end (name → kind).

16. Post-Step Guidance (Optional)
    Suggest running locally: `validate_catalog resources/standard_names` (or `python -m imas_standard_names.validation.cli validate_catalog resources/standard_names`) and (future) loading with Pydantic models to confirm.

---

### 3. YAML Field Templates

Base Scalar Template:

```yaml
name: <base_scalar>
kind: scalar
unit: <SI_or_1>
status: draft
description: <Concise (<=120 chars) description sentence or fragment>
```

Component Scalar Template:

```yaml
name: <axis>_component_of_<vector_expression>
kind: scalar
unit: <same as vector>
axis: <axis>
parent_vector: <vector_name>
status: draft
description: <Axis capitalized> component of <vector_name>.
```

Vector Template (validator-compatible magnitude):

```yaml
name: <vector_name>
kind: vector
frame: <frame_name>
unit: <SI>
components:
  radial: radial_component_of_<vector_name>
  toroidal: toroidal_component_of_<vector_name>
  vertical: vertical_component_of_<vector_name>
magnitude: magnitude_of_<vector_name>
status: draft
description: <Vector description in frame>.
```

Magnitude Scalar (prefix style – RECOMMENDED for current validators):

```yaml
name: magnitude_of_<vector_name>
kind: derived_scalar
unit: <SI>
parent_vector: <vector_name>
derivation:
  expression: |
    sqrt(<radial_component>^2 + <toroidal_component>^2 + <vertical_component>^2)
  dependencies:
    - <radial_component>
    - <toroidal_component>
    - <vertical_component>
status: draft
description: Magnitude of <vector_name>.
```

Derived Vector (example: time derivative):

```yaml
name: time_derivative_of_<vector_name>
kind: derived_vector
frame: <frame_name>
unit: <SI>
parent_operation:
  operator: time_derivative
  operand_vector: <vector_name>
components:
  radial: radial_component_of_time_derivative_of_<vector_name>
  toroidal: toroidal_component_of_time_derivative_of_<vector_name>
  vertical: vertical_component_of_time_derivative_of_<vector_name>
magnitude: magnitude_of_time_derivative_of_<vector_name>
status: draft
description: Time derivative of <vector_name>.
```

Derived Scalar (divergence):

```yaml
name: divergence_of_<vector_name>
kind: derived_scalar
unit: s^-1
parent_operation:
  operator: divergence
  operand_vector: <vector_name>
derivation:
  expression: <leave empty or future analytic form>
  dependencies:
    - <radial_component>
    - <toroidal_component>
    - <vertical_component>
status: draft
description: Divergence of <vector_name>.
```

Gradient (scalar → derived vector) example:

```yaml
name: gradient_of_<scalar_name>
kind: derived_vector
frame: <frame_name>
unit: <scalar_unit>.m^-1 # adjust dimensionally
parent_operation:
  operator: gradient
  operand_vector: <scalar_name> # logically a scalar operand; retained field name for consistency
components:
  radial: radial_component_of_gradient_of_<scalar_name>
  toroidal: toroidal_component_of_gradient_of_<scalar_name>
  vertical: vertical_component_of_gradient_of_<scalar_name>
magnitude: magnitude_of_gradient_of_<scalar_name>
status: draft
description: Gradient of <scalar_name>.
```

---

### 4. Operator Rank Constraints (Enforce During Generation)

From spec §7 (summarized):

- curl(vector) → vector (3D only)
- divergence(vector) → scalar (terminal)
- gradient(scalar) → vector
- magnitude(vector) → scalar (terminal)
- time_derivative(scalar|vector) → same rank (chainable)
- laplacian(scalar) → scalar; laplacian(vector) → vector (component-wise)
  Invalid chains examples: `curl_of_divergence_of_*`, double magnitude, scalar input to gradient.

Algorithmic check pseudo‑rules:

1. Parse left-to-right tokens split by `_of_` where token ∈ operator set.
2. Track current rank (scalar|vector). Reject illegal transitions.
3. If scalarizing operator (divergence|magnitude|curl_magnitude|normalized_magnitude) encountered, no further vector-producing operator may follow.

---

### 5. Validation Checklist (Pre-Emit for Each Entry)

| Check                                             | Rule Source                                |
| ------------------------------------------------- | ------------------------------------------ |
| Name pattern                                      | models.py `validate_name` + style guide §2 |
| No double underscores                             | models.py                                  |
| Vector has >=2 components                         | models.py structural_rules                 |
| Component pattern matches axis + `_component_of_` | spec §3 / validator script                 |
| Component scalar kind is scalar / derived_scalar  | models.py                                  |
| Derived kinds have derivation or parent_operation | models.py                                  |
| Magnitude naming matches `magnitude_style`        | models.py vs. spec                         |
| Dependencies complete (all base components)       | validator script MAGNITUDE check           |
| No forbidden chains                               | spec §7 / style guide §5                   |
| Description length <= limit                       | parameter `description_length_max`         |

---

### 6. Emission Format

Return final answer as:

```
---
# Batch 1: Base Scalars
<YAML entries>
---
# Batch 1: Expanded (Vectors, Components, Derived)
<YAML entries>
---
# Batch 2: ...
...
---
# Index
<tabular summary or markdown list>
---
# Validation Report
<summary of simulated passes/failures (expect all pass)>
```

If `emit_validation_report=false`, omit last section.

---

### 7. Prompt Assembly Template (Copy & Use)

Paste the following to drive generation (fill the parameter block first):

```
SYSTEM:
You are an IMAS Standard Name authoring assistant. You MUST emit only validator-compliant YAML proposals unless explicitly instructed to show diagnostics. Follow repository specification (docs/specification.md) & style (docs/style-guide.md). Prefer prefix magnitude naming (magnitude_of_<vector>) unless `magnitude_style=suffix` is set.

USER PARAMETERS:
{<insert filled parameter block>}

TASK:
1. Execute the High-Level Workflow steps 1–11.
2. For IMAS DD mining request concise structured data (list field → physical meaning → suggested base scalar name candidate). If unavailable, proceed with physics-informed assumptions for {domain_group}.
3. Generate up to {max_base_scalars} new base scalars (over {batches} batch(es)).
4. Expand into vectors, components, derived entities respecting operator rank.
5. Provide YAML entries (one logical item per block) in required order.
6. Include dependency lists for derived scalars using ALL component names.
7. Produce a validation report summarizing any detected risk or uncertainty.
8. Do NOT duplicate existing canonical examples (magnetic_field family) unless extending with new derived forms legitimately.

OUTPUT STRICTLY:
- Valid YAML blocks only (no extraneous prose inside blocks) preceded by comment headers as defined in Emission Format.
- After YAML sections, include an Index and optional Validation Report.

If any rule conflicts (e.g. spec vs. current validators on magnitude naming), prefer validator compliance and note the divergence in the Validation Report.
```

---

### 8. Example Minimal Invocation (Narrative Only)

> domain_group: equilibrium; imas_ids_scope: equilibrium; max_base_scalars: 5; vector_ratio: 0.2; include_derived_vectors: true; include_scalar_derivatives: time_derivative,magnitude,divergence; magnitude_style: prefix.

Agent would: mine IDS → propose scalars like `plasma_current`, `poloidal_flux` (already exists? then skip), etc., then decide if a new vector (e.g. `plasma_velocity`) merits introduction, generate components + derived scalars.

---

### 9. Future Adjustments

Once code & docs converge on magnitude naming, remove `magnitude_style` switch and always use suffix `<vector>_magnitude` while updating `models.py` accordingly.

---

End of reusable prompt template.
