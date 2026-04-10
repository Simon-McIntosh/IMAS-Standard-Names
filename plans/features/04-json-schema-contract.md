# Feature 04: JSON Schema Contract

**Repository:** imas-standard-names  
**Wave:** 2 (after Feature 01)  
**Depends on:** Feature 01 (Grammar API Exports)  
**Enables:** Feature 05 (codex SN Build Pipeline — validation at mint boundary)  

---

## Goal

Publish a versioned JSON schema that defines the contract between imas-codex (producer) and imas-standard-names (validator). Codex generates candidate names as structured data matching this schema; standard-names validates and persists them.

## Design Decision: Pydantic-Native (Not LinkML)

LinkML was evaluated and **rejected** for generating the catalog entry schema. The `models.py` Pydantic models (681 lines) contain:

- **Custom field validators** — unit canonicalization with dot-exponent parsing and pint integration, grammar vocabulary consistency checks, double-underscore enforcement
- **Discriminated union** — `scalar | vector | metadata` with per-kind required fields and validation
- **Provenance system** — `OperatorProvenance`, `ReductionProvenance` with operator chain normalization and naming enforcement cross-referencing the entry name
- **Computed properties** — vector magnitude derivation, formatted unit rendering

LinkML `gen-pydantic` produces flat models with basic type constraints. It cannot express custom validators, model-level cross-field validation, complex discriminated unions with per-variant logic, or computed properties. We'd generate a skeleton and override everything — the worst of both worlds.

**Approach:** Export JSON schema directly from the Pydantic models using `StandardNameEntry`'s `TypeAdapter.json_schema()`. This captures the full type structure while the Pydantic models remain the single source of truth for validation logic.

## Deliverables

### Phase 1: Extract and version the schema

- Export `StandardNameEntry` Pydantic JSON schema via `_STANDARD_NAME_ENTRY_ADAPTER.json_schema()`
- Include all discriminated union variants (scalar, vector, metadata)
- Version the schema with semver, linked to grammar version
- Store at `imas_standard_names/schemas/entry_schema.json`
- Include schema generation in build hooks or as a CLI command

### Phase 2: Validation utility

- Create `validate_against_schema(data: dict) -> list[str]` utility
- Validates arbitrary JSON/YAML against the published schema
- Returns list of validation errors (empty = valid)
- Usable by codex's mint phase without importing full standard-names

### Phase 3: YAML file format contract

- Document the exact YAML structure codex must produce for minted names
- Include: required fields, tag ordering rules, provenance format
- Include: `ids_paths` population expectations
- Publish as part of the schema artifact

## Acceptance Criteria

- JSON schema file generated and included in package distribution
- Schema versioned and linked to grammar version
- Validation utility works standalone
- Contract documentation covers all edge cases
