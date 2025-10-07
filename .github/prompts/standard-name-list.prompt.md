# Standard Name List Prompt (Quick Generation, No YAML Files)

Purpose: Rapidly produce vetted lists of proposed IMAS Standard Name tokens (no file scaffolding) for review or triage.

Version: v1.3 (adds interactive iteration loop with row numbering & deferred batch block; v1.2 added tabulated sections)

## Parameters
```
{domain_group: equilibrium|diagnostics|geometry|plasma_state|transport|generic|mixed}
{imas_ids_scope: auto}
{max_names: 40}
{include_vectors: true}
{include_components: true}
{include_derivatives: time_derivative, divergence, magnitude, gradient}
{allowed_axes: radial,toroidal,vertical}
{vector_threshold: 0.15}  # fraction of base scalars to nominate as vectors
{novelty_check: true}
{show_rationale: brief}
{output_sections: base_scalars,vectors,components,scalars_with_provenance,summary}
{strict_semantics: true}
{interactive_review: true}  # NEW: if true, engage iteration loop before final batch block
{max_iterations: 6}          # Safety cap; after this auto-prompt user to finalize
```

The model MUST echo the effective parameter values inside the machine-readable batch block (see Machine-Readable Batch Block section) so downstream tooling can parse and audit.

## MCP Data Acquisition (MANDATORY WHEN AVAILABLE)

Before generating candidates, query the IMAS MCP server for context relevant to `{domain_group}`:

1. Retrieve IDS structure (if not already cached):
	- TOOL: mcp_imas_analyze_ids_structure(ids_name="equilibrium"|"core_profiles"|"edge_profiles"|"magnetics")
2. Search for semantic matches to key physical concepts (examples):
	- TOOL: mcp_imas_search_imas(query="triangularity")
	- TOOL: mcp_imas_search_imas(query="elongation")
	- TOOL: mcp_imas_search_imas(query="psi axis")
	- TOOL: mcp_imas_search_imas(query="boundary outline")
3. (Optional) Explore relationships for a specific path to uncover dependent concepts:
	- TOOL: mcp_imas_explore_relationships(path="equilibrium/time_slice/boundary", relationship_type="semantic")
4. Use identifier exploration if a non-standard axis token emerges:
	- TOOL: mcp_imas_explore_identifiers(scope="identifiers")

Summarize harvested canonical field names (psi_axis, psi_boundary, elongation, triangularity_upper, etc.) and prefer adopting existing semantics over inventing new tokens.

If an MCP query returns no results, explicitly state: `MCP: no direct match for <term>; using domain knowledge.` Do **not** fabricate IDS paths.

## Generation Steps (Abbreviated)
0. (MCP Harvest) Run the MCP queries above; compile a short internal list of relevant existing IDS scalar names and geometry paths.
1. Collect candidate physical concepts for {domain_group} (favor MCP harvested names; else domain knowledge).
2. Normalize tokens to lowercase underscore form; drop coordinate/instrument indices.
3. Existing catalog scan & duplicate / near-duplicate pruning (EARLY DEDUP):
	- Load existing catalog names (scan `standard_names/` recursively for `name:` fields or file basenames).
	- Remove exact duplicates immediately (do not list them in sections).
	- Compute Levenshtein distance to already retained candidates; if distance ≤2 treat as near-duplicate:
		 * Exclude from main sets; append to `similar_rejected` in batch block with `reason: near_duplicate` and `similar_to: <kept_name>`.
	- Enforce canonical magnitude form: if both `magnitude_of_<vector_expression>` and `<vector_expression>_magnitude` appear, discard the suffix form and record it under `rejected` with reason `legacy_magnitude_suffix`.
4. Filter out generic or disallowed names (consult `docs/generic_names.csv`); record filtered items under `rejected` with reason `generic`.
5. Select base scalar list (unique, unambiguous). Provide short rationale if `show_rationale=brief`.
6. Identify potential vectors; synthesize missing component scalar names using `<axis>_component_of_<vector>`.
7. Add derived forms respecting rank rules (gradient of scalar, divergence of vector, magnitude_of_<vector_expression>, time derivatives, curl where valid 3D).
8. Validate each proposal logically (naming grammar + operator rank); exclude invalid chains (e.g. `curl_of_divergence_of_*`) and record under `rejected` with reason.
9. Present output in requested sections (now REQUIRED to be markdown tables; see Output Format).
10. Provide a concise summary & next-step suggestions.
11. Emit a machine-readable batch block EXACTLY once at the end (deferred until user "finalize" if interactive_review=true).
12. Immediately after emitting the batch block, prompt the user: "Would you like these approved standard names to be scaffolded into YAML files in the repository? (yes/no)" and await a response before any further action.
		- If the user responds affirmatively (yes|y|sure|ok|proceed|do it|create|generate), invoke the batch generation prompt (`standard-name-batch.prompt.md`) passing:
				* `analysis_type` derived from `handoff.anaysis_type_hint` if present else a mapping of `parameters.domain_group`.
				* `input_standard_name_batch` = the full YAML block just produced.
			Then merge any newly proposed tokens (excluding duplicates) and scaffold YAML files for all names (original + new) under an inferred domain directory (e.g. `standard_names/<domain_group>/`). Do not overwrite existing files; if a file exists, record a collision note instead.
		- If the user responds negatively (no|n|not now|later|skip), end the workflow with no scaffolding.
		- If ambiguous, repeat the confirmation request without regenerating names or batch block.

## Interactive Iteration Loop

When `{interactive_review: true}`:
1. Produce an INITIAL DRAFT consisting ONLY of the human-readable tables (numbered rows) plus a short prompt asking the user for actions. DO NOT output the machine-readable batch block yet.
2. A SINGLE GLOBAL SEQUENTIAL NUMBERING must be used across ALL tables (do NOT restart at 1 per table). The numbering begins at 1 for the first row of Base Scalars, then continues incrementally through Vectors, Components, Derived Vectors, Derived Scalars, and finally (if the Summary is numbered—see note below) the Summary is NOT numbered. Only data-bearing proposal tables are numbered; the Summary table is excluded from numbering. The numbering is transient and not part of the token.
3. After showing tables, append an "Action Prompt" section listing accepted commands:
	- `remove 3,5-7,12` → remove listed row numbers (supports ranges)
	- `modify 4 -> new_token_name` (optionally add `| rationale: <text>`)
	- `rename 4 new_token_name`
	- `rationale 8 Updated rationale text`
	- `swap 2 5` (optional; reorder two entries)
	- `move 7 after 2` or `move 7 to 1`
	- `undo` (reverts the last mutation, keep up to last 5 in history)
	- `finalize` / `approve` / `accept` / `done` → triggers finalization
	- `list rejected` → (re)show currently tracked rejected/near-duplicate items (if any)
4. After each user command (except finalize), regenerate ONLY the affected tables (all tables if any insertion/removal changes downstream global indices). Recompute the single global index sequence and reissue the action prompt. Still DO NOT output the batch block.
5. On `finalize` (or equivalent), remove the numbering column from all tables, re-render final tables in the required order, then (and only then) append the single machine-readable batch block.
6. If `{max_iterations}` is reached without finalization, append a polite reminder: "Iteration limit reached—reply 'finalize' to emit batch block or 'extend iterations' to raise limit (max soft cap 12)."
7. During iteration phases: NEVER output `BEGIN_STANDARD_NAME_BATCH` or `END_STANDARD_NAME_BATCH`.
8. Ensure consistency: rows removed or modified must propagate across dependent sections (e.g., if a base scalar is deleted, derived forms including it must also be removed and optionally listed under a transient "auto_removed" note after finalization inside metadata notes section.
9. Maintain internal sets:
	- `current.base_scalars`, `current.vectors`, `current.components`, `current.scalars_with_provenance`
	- `rejected`, `similar_rejected`, `auto_removed`
10. Only the final batch block includes `rejected` and `similar_rejected`; iteration steps must not output YAML.
11. If `{interactive_review: false}` skip the loop and directly output final tables + batch block per legacy v1.2 behavior.

## Output Format
Plain text / markdown only (NO YAML in the human-readable part) and EACH SECTION MUST BE A MARKDOWN TABLE. No free-form bullet lists for names.

INTERACTIVE (iteration phase):
- Tables MUST have a leading `#` column, followed by the schema columns defined below.
- A single global index spans all proposal tables. Do NOT restart numbering per section.
- Example (iteration phase with global numbering across two sections):
```
# Base Scalars (N=3)
| # | Name | Rationale |
| - | ---- | --------- |
| 1 | poloidal_flux | Canonical poloidal flux (psi). |
| 2 | poloidal_flux_axis | Flux at magnetic axis. |
| 3 | poloidal_flux_boundary | Flux at plasma boundary. |

# Vectors (N=1)
| # | Name |
| - | ---- |
| 4 | gradient_of_poloidal_flux |
```
FINAL (after finalize):
- Remove the numbering column entirely (revert to v1.2 style).

General rules (superset):
1. Provide a level-1 markdown heading for each section (`# Base Scalars (N=..)`).
2. Immediately follow the heading with a markdown table.
3. Use pipe `|` separated columns. A header separator row (`---`) is mandatory.
4. Do not include blank rows inside a table.
5. Avoid trailing spaces around cell content. Keep names in the first column exactly as proposed tokens.
6. Rationale column may be omitted for sections where rationale is not required (Vectors, Components, Derived Vectors). If omitted, still supply a single header column `Name`.
7. Do NOT repeat the same name in multiple tables (enforced elsewhere, but format must not duplicate).
8. Use ONE global index across all proposal sections (Base Scalars through Derived Scalars). The Summary table is excluded from the numbering and has no `#` column.
9. Iteration "Action Prompt" appears AFTER the Summary during interactive phases (omit in final output).

Recommended table schemas (FINAL MODE):

Base Scalars:
```
| Name | Rationale |
| ---- | --------- |
| poloidal_flux_axis | Poloidal flux at magnetic axis (psi_axis). |
```

Vectors:
```
| Name |
| ---- |
| gradient_of_poloidal_flux |
```

Components:
```
| Name |
| ---- |
| radial_component_of_gradient_of_poloidal_flux |
```

Derived Vectors:
```
| Name |
| ---- |
| time_derivative_of_gradient_of_poloidal_flux |
```

Derived Scalars:
```
| Name | Rationale |
| ---- | --------- |
| magnitude_of_gradient_of_poloidal_flux | Scalar magnitude (norm) of gradient vector. |
```

Summary (example):
```
| Metric | Value | Notes |
| ------ | ----- | ----- |
| base_scalars_count | 12 | All pass grammar |
| vectors_count | 1 | gradient only |
| components_count | 3 | radial,toroidal,vertical |
```

Legacy non-tabular format is now INVALID; generation MUST use tables exactly once per section in the order: Base Scalars, Vectors, Components, Derived Vectors, Derived Scalars, Summary.

## Machine-Readable Batch Block (REQUIRED After Finalization Only)

After the human-readable sections (final mode), append **exactly one** sentinel-delimited YAML block. No text may appear after the `END_STANDARD_NAME_BATCH` line. After this, request user confirmation for YAML scaffolding per step 12 before executing any file generation logic.

```
BEGIN_STANDARD_NAME_BATCH
parameters:
	domain_group: <value>
	imas_ids_scope: <value>
	max_names: <int>
	include_vectors: <true|false>
	include_components: <true|false>
	include_derivatives: [time_derivative, divergence, magnitude, gradient]
	allowed_axes: [radial, toroidal, vertical]
	vector_threshold: <float>
	strict_semantics: <true|false>
	interactive_review: <true|false>
handoff:
	anaysis_type_hint: <auto-derived analysis_type string for batch prompt>
source_context:
	mcp_queries:
		- query: "triangularity"
			ids: equilibrium
		- query: "boundary outline"
			ids: equilibrium
	harvested_ids_terms:
		- psi_axis
		- psi_boundary
		- elongation
		- triangularity_upper
		- triangularity_lower
sections:
	base_scalars:
		- <name>
	vectors:
		- <vector_name>
	components:
		- <component_name>
	scalars_with_provenance:
		- <scalar_name_with_provenance>
rejected:
	- name: <token>
		reason: <reason>
similar_rejected:
	- name: <token>
		reason: near_duplicate
		similar_to: <kept_name>
metadata:
	prompt_version: v1.3
	generation_timestamp: <ISO8601>
	model: <model_id_if_available>
	notes: |
		Brief free-text generation notes (e.g. rationale for excluding curl). If interactive_review=true include iteration_count and any auto_removed cascades.
END_STANDARD_NAME_BATCH
```

Rules:
- Use valid YAML (2-space indent, no tabs).
- Omit empty section arrays entirely OR supply an empty list (`[]`).
- Do not repeat names across sections; components must not appear in base_scalars.
- Do not introduce fields outside `parameters`, `source_context`, `sections`, `metadata`.
- Ensure every vector has >=2 distinct axis components (if vectors present).
- If `include_vectors: false`, then `vectors`, `components` should be absent or empty.
- Use only the canonical `magnitude_of_` prefix form (never legacy `<vector>_magnitude`).
- If self-check detects malformed YAML, regenerate the entire block (no manual patching mid-output).

### Batch Prompt Handoff
Add a `handoff.anaysis_type_hint` field (note: intentional single `n` spelling preserved for backward compatibility if existing tooling already used it; downstream batch prompt must tolerate this) that provides a short phrase convertible into the `analysis_type` parameter for the batch generation prompt. If omitted, batch prompt will fall back to mapping `parameters.domain_group` via its internal mapping rules. Example:
```
handoff:
	anaysis_type_hint: equilibrium reconstruction
```
Downstream tooling invoking `standard-name-batch.prompt.md` SHOULD pass the entire `STANDARD_NAME_BATCH` block as `input_standard_name_batch` and MAY override with an explicit `analysis_type`. The batch prompt must suppress proposals already present in `sections` of the supplied batch.

## Rank & Naming Guards
- Never mix legacy `<vector>_magnitude` form.
- Component axes limited to {allowed_axes}.
- Operator chain left-to-right; stop after scalarizing operator.
- No gradient_of_vector unless defined tensor future (skip now).

## System Instruction Snippet 
```
You propose ONLY candidate standard name tokens (no YAML) using canonical magnitude_of_ naming, respecting IMAS spec & style. Provide brief rationales; exclude duplicates and legacy forms. Maintain a single global index across all proposal tables during interactive review; indices are removed entirely on finalization.

If interactive_review=true:
- Produce numbered tables and await user instructions.
- Do NOT output BEGIN_STANDARD_NAME_BATCH until user explicitly finalizes.
- Accept commands: remove, modify/rename, rationale, swap, move, undo, finalize.
- After finalize: remove numbering, output final tables, then batch block.

If interactive_review=false: behave per legacy v1.2 (output final tables + batch block immediately).

## Name Grammar (Hard Requirements)
Each proposed name MUST:
- Begin with a lowercase letter (a–z).
- Contain only lowercase letters, digits, single underscores.
- Not contain consecutive underscores or end with an underscore.
- Not exceed 60 characters (soft); absolute maximum 80 (hard) – if longer, omit.
- Avoid vague suffixes (`value`, `data`, `measurement`, `profile`) unless disambiguation is essential.
- Use location qualifiers (`at_magnetic_axis`, `at_plasma_boundary`) ONLY when two landmark scalars coexist.
- Use `magnitude_of_` for all magnitude scalars.

If a candidate violates any hard rule, exclude it and list under `rejected:` with a short reason inside the batch block (only appears after finalization when interactive).
```

End of quick list prompt.
