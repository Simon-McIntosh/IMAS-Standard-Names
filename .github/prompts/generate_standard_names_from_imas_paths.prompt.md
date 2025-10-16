# Generate Standard Names from IMAS Paths

Create standard names following the project grammar for given IMAS IDS paths.

## Critical Rules

1. **Tag Order**: First tag (tags[0]) MUST be a primary tag from controlled vocabulary (e.g., 'magnetics', 'fundamental', 'equilibrium'). Secondary tags like 'cylindrical-coordinates', 'measured', 'local-measurement' MUST come after. See tag vocabulary in grammar.

2. **IMAS DD Alignment**: Sign conventions, coordinate systems, physical definitions, and units MUST strictly follow the IMAS Data Dictionary documentation. Do not invent or redefine conventions.

## Workflow

### Initial generation

- Get grammar rules: `get_grammar_and_vocabulary`
- Check and fetch IMAS paths using IMAS MCP tools
- Extract IMAS DD documentation, units, and sign conventions
- Generate scalar standard names aligned with IMAS DD
- Generate vector components from scalars 
- Get catalog schema: `get_catalog_entry_schema`
- Generate tags, units, and descriptions for each entry

### Output format

Return tabulated markdown table with columns:

`| IDS Path | Standard Name | Units | Tag | Description |`

### Formatting requirements

- Maintain exact order from input path list
- Preserve skipped entries and blank lines from original list
- Include vector names at end of table

### Confirmation

After presenting the table, ask user to:

1. Create catalog entries
2. Generate IMAS path mappings
3. Create catalog entries and path mappings
4. Edit specific entries
5. Cancel

Do not create entries without user confirmation.

### Catalog creation

If user confirms creation:

- Generate documentation for each entry
- Create entries: `create_standard_names`
- Write to disk: `write_standard_names`

### Path mappings (optional)

If requested, create `docs/generated/[ids_name]_standard_names.md` with path mappings, vector relationships, and usage examples.
