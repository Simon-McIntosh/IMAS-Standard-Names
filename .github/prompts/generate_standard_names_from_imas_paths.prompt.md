# Generate Standard Names from IMAS Paths

Create standard names following the project grammar for given IMAS IDS paths.

## Critical Rules

**IMAS DD Alignment**: Sign conventions, coordinate systems, physical definitions, and units MUST strictly follow the IMAS Data Dictionary documentation. Do not invent or redefine conventions.

## Output Format Specification

All output tables must follow these common rules:

**Table formatting:**
- Return tabulated markdown table
- Maintain exact order from input path list
- Preserve blank lines from original list
- Append vector parent entries at end
- Mark duplicate paths with `*duplicate*` qualifier

**Non-convertible path qualifiers:**
- `*metadata - excluded*` for ids_properties, code/*, type indices, iteration counts
- `*path not found in {IDS_NAME} IDS*` for invalid paths
- `*not detailed here*` for complex structures (e.g., grids_ggd) explicitly noted in input
- `*duplicate*` for paths that appear multiple times in the input list

## Workflow

### Initial generation

- Get grammar rules: `get_grammar_and_vocabulary`
- Check and fetch IMAS paths using IMAS MCP tools
- Extract IMAS DD documentation, units, and sign conventions
- Generate scalar standard names aligned with IMAS DD
- Generate vector components from scalars 

**Output:** Markdown table with columns: `| IDS Path | Standard Name |`

Apply format specification rules above.

### Confirmation

After presenting the table ask user for confirmation.
Do not create entries without user confirmation.

### Catalog creation

If user confirms creation:

- Get catalog schema: `get_schema`
- Generate tags, units, descriptions and documentation
- Create entries: `create_standard_names`
- Fix errors: `edit_standard_names`
- Write to disk: `write_standard_names`

**Output:** Markdown table with columns: `| IDS Path | Standard Name | Grammar | Unit | Description | Tags |`

Apply format specification rules above, plus:

**Grammar column:**
- Show ONLY segment placeholders: `<component>`, `<coordinate>`, `<subject>`, `<base>`, `<object>`, `<source>`, `<geometry>`, `<position>`, `<process>`
- Include templates: `<component>_component_of`, `of_<object>`, `from_<source>`, `of_<geometry>`, `at_<position>`, `due_to_<process>`
- Examples:
  - `radial_position_of_flux_loop` → `<coordinate> <base> of_<object>`
  - `toroidal_component_of_magnetic_field_at_magnetic_axis` → `<component>_component_of <base> at_<position>`
  - `flux_surface_averaged_elongation` → `<base>`

**Additional:**
- Do not distinguish newly created vs existing entries
