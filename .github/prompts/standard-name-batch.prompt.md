Batch IMAS Standard Name Generation Prompt

Purpose: Generate a curated batch (set) of proposed IMAS Standard Names for a specified analysis type WITHOUT producing documentation, units, or references yet. Output ONLY the list of proposed standard names. This prompt orchestrates a focused workflow using the IMAS MCP server tools and the IMAS naming guidelines.

Input Parameters (required unless marked optional):
- analysis_type: A short description of the analysis domain or task (e.g. "equilibrium reconstruction", "core transport modeling", "heating and current drive", "edge plasma", "runaway electron analysis").
- desired_count (optional): Target number of names to generate (default 25; must be 1–200).
- include_transformations (optional, default true): Whether to include derivative/ratio/square/etc. transformation-based names.
- restrict_components (optional): Comma-separated subset of components to allow (from: radial, vertical, toroidal, poloidal, parallel, diamagnetic). If omitted, all may be considered where physically meaningful.
- disallow_processes (optional): Comma-separated list of process qualifiers to exclude (e.g. conduction, convection, radiation, diffusion, induction).
- refinement_instruction (optional): If present, treat this as a follow-up refinement request instead of a fresh generation.

Output Requirements:
- Produce ONLY a markdown bullet list of proposed standard names (one per line) preceded and followed by a blank line.
- No units, no documentation text, no equations, no explanatory prose.
- Names must follow formatting rules (see below) and be unique within the list.

Context Files to Load:

- file:../docs/guidelines.md
- file:../docs/generic_names.csv
- file:../docs/transformations.csv

Guideline Essentials (embedded summary – authoritative source remains guidelines.md):
- Pattern skeleton (optionally chained): [component_] base_quantity [ _at_<position> ] [ _due_to_<process> ] possibly wrapped by transformation prefixes (e.g. derivative_of_, ratio_of_, square_of_, magnitude_of_, product_of_, tendency_of_, change_over_time_in_ ).
- Allowed components: radial, vertical, toroidal, poloidal, parallel, diamagnetic.
- at_<position> examples: at_magnetic_axis, at_boundary, at_current_center (positions must start with a letter and use underscores; only include if physically justified by analysis_type evidence from IDS data paths or commonly used global surfaces / landmarks).
- due_to_<process> examples: due_to_conduction, due_to_convection, due_to_radiation, due_to_diffusion, due_to_induction (only include if analysis_type implies decomposition of a flux / source term; do NOT invent obscure processes).
- Transformations (from transformations.csv) may stack but avoid redundancy (e.g. square_of_square_of_X is invalid). Do not combine mutually unclear constructs (e.g. ratio_of_derivative_of_X_wrt_Y_to_derivative_of_X_wrt_Z is out of scope for batch stage).
- Generic base nouns (from generic_names.csv) are NOT themselves valid final names; they must be contextualized (e.g. pressure -> poloidal_pressure is acceptable only if representing a directional component, else just pressure if already specific enough in fusion context). Avoid meaningless qualifiers.
- Regex compliance: ^[a-z][a-z0-9_]*$ ; no double underscores; no trailing underscore; no embedded uppercase or hyphens.
- No repetition: e.g. radial_radial_pressure invalid; temperature_temperature invalid; derivative_of_derivative_of_X invalid at this stage.

Targeted MCP Tool Workflow:
1. Normalize Input
   - Parse analysis_type; derive key domain tokens (e.g. "equilibrium", "transport", "heating", "edge", "diagnostics", "runaway", "mhd").
   - Infer initial candidate physics domains (mapping examples):
     equilibrium reconstruction -> equilibrium, magnetic_diagnostics
     core transport modeling -> transport, heating
     heating and current drive -> heating, current_drive, transport
     edge plasma -> edge_physics, transport, divertor
     runaway electron analysis -> mhd, transport
2. Discover IDS Scope
   - Use get_overview ONLY if no prior cached domain to IDS mapping exists for this session.
   - For each inferred domain (max 3 to stay focused):
     - Option A (primary): use export_physics_domain(domain, analysis_depth = "focused", max_paths ~ 25–40) to harvest representative paths.
     - Option B (fallback if export_physics_domain not sufficiently granular): use search_imas(query) with a composed query string containing domain tokens and core physical quantities (e.g. "current density temperature pressure flux magnetic field").
3. Structural Deepening (conditional)
   - If candidate base nouns < desired_count/3, run analyze_ids_structure on up to 2 high-yield IDS (e.g. plasma_profiles, core_transport, equilibrium) and extract terminal attribute names (leaf nodes) that are semantically physical quantities (exclude indices, flags, validity markers, *_fit containers, enumerations, metadata, source references, state descriptors unless central to analysis_type).
4. Relationship Expansion (optional)
   - Only if fewer than desired_count unique base concepts found: explore_relationships(path) for 1–2 central paths to discover related physical quantities (relationship_type = semantic). Limit expansions to prevent noise.
5. Candidate Extraction & Normalization
   - Derive base_quantity terms by converting attribute names: j_phi -> toroidal_current_density ; j_parallel -> parallel_current_density ; density_thermal -> density (may later yield thermal_particle_density if direction/energy context required – avoid over elaboration here) ; t_e -> electron_temperature ; n_i_total_over_n_e -> ratio_of_ion_density_to_electron_density .
   - Map shorthand tokens: t_e -> electron_temperature ; t_i -> ion_temperature ; psi -> poloidal_flux ; q (if present in equilibrium context) -> safety_factor (BUT only include if strongly indicated by attribute paths; do not hallucinate q if absent).
   - Remove dataset-specific suffixes like _fit, _validity, _weight, _parameters, _reconstructed, _measured, _source unless they correspond to a physically distinct quantity conceptualizable as a standard name (they usually are not; discard them now).
6. Transformation Application (if include_transformations)
   - Apply at most one transformation per candidate for initial batch except derivative_of_X_wrt_radius or ratio_of_X_to_Y for especially salient diagnostic/transport ratios (limit to transformations present in transformations.csv list).
   - Avoid generating both X and transformation_of_X unless necessary to meet desired_count; prioritize raw/base forms first.
7. Component & Qualifier Injection
   - Add components (radial, poloidal, toroidal, parallel, diamagnetic, vertical) ONLY if the underlying attribute or context implies directionality or vector decomposition.
   - Add at_<position> ONLY when strongly justified (e.g. magnetic_axis, boundary) and keep to ≤ 3 position-qualified names in initial batch.
   - Add due_to_<process> ONLY if analysis_type context explicitly targets decomposition of a flux or source (e.g. a heating & current drive analysis). Limit to ≤ 3 process-qualified names.
8. Validation & Deduplication
   - Enforce uniqueness; remove near-duplicates differing only by superficial transformation where redundancy adds no analytical value.
   - Filter out overly compound or speculative constructs.
   - Sort logically: (a) base scalar quantities, (b) directional/vector component forms, (c) ratios / derived / transformed forms.
9. Output
   - Emit bullet list (markdown) of final names ONLY. Blank line before first and after last list item.
   - Count should match desired_count if feasible; if fewer produced (due to strict filtering) still output list (do NOT fabricate low-quality names to pad). Do not explain deficit—user can request refinement.
10. Refinement Loop (if refinement_instruction provided)
   - Compare newly requested constraints vs previous set. Categorize modifications internally then output ONLY the revised bullet list.

Mandatory Exclusions in This Batch Stage:
- NO documentation blocks, NO units, NO references, NO LaTeX, NO equations.
- NO images or diagrams.
- NO references to IMAS Data Dictionary paths in the output list.

Quality Heuristics (apply silently):
- Prefer concise semantic clarity over maximal qualification (e.g. electron_density over electron_thermal_particle_number_density unless ambiguity truly exists).
- Avoid stacking unrelated qualifiers (e.g. poloidal_derivative_of_radial_pressure is out of scope for batch stage).
- Avoid using generic_names.csv base tokens alone (they must be contextually specialized if ambiguous: e.g. power -> heating_power is acceptable only if tied to a source domain; else leave for later iteration).

Error Handling:
- If analysis_type is missing: return a single bullet list item: invalid_input_missing_analysis_type (and nothing else).
- If zero candidate names after filtering: return a single bullet list item: no_viable_names_found_refine_inputs .

Output Format Example (illustrative only – do NOT hardcode these actual names):

- electron_temperature
- ion_temperature
- electron_density
- ion_density
- poloidal_magnetic_field
- toroidal_magnetic_field
- parallel_current_density
- bootstrap_current_density
- ratio_of_ion_density_to_electron_density
- derivative_of_electron_temperature_wrt_radius

(End example – real output depends on analysis_type and live tool queries.)

Agent Operational Notes:
- Cache intermediate tool responses per session to minimize redundant calls.
- Do NOT call analyze_ids_structure, explore_relationships, or export_physics_domain unless earlier, cheaper steps (search_imas) yield insufficient diversity.
- Keep total MCP tool invocations ≤ 12 for an initial generation (soft cap) unless refinement requires deeper inspection.
- Prefer search_imas with combined multi-key queries (space separated) rather than multiple single-term calls.

Refinement Examples:
User provides refinement_instruction = "increase focus on current drive and include more ratio forms" → Re-run steps 2–7 emphasizing IDS with current drive (e.g. lh_antennas, ic_antennas, nbi) and bias transformation generation toward ratio_of_X_to_Y for current density / power deposition related quantities.

End of Prompt Specification.
