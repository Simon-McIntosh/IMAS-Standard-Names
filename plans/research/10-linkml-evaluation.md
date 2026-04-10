# LinkML Evaluation for Standard Names

**Date:** 2026-04-08  
**Status:** Complete — LinkML rejected for both grammar and catalog schema

---

## Context

LinkML is used extensively in the imas-codex project to define graph ontology schemas (e.g., `schemas/facility.yaml`). The question: should it also define either the standard name grammar or the catalog entry schema in imas-standard-names?

## Assessment 1: Grammar System

**Verdict: Not suitable.**

The standard name grammar is a **compositional string DSL** — it defines how tokens are assembled into canonical names following ordered segment templates (e.g., `"{component}_component_of_{physical_base}"`). Key requirements:

- Ordered segment assembly with template patterns
- Mutual exclusivity rules (`component` XOR `coordinate`, `geometry` XOR `position`)
- Open vocabulary for `physical_base` (any physics quantity in snake_case)
- Prefix/suffix parsing with connector words (`_of_`, `_at_`, `_from_`)
- Codegen producing StrEnum types from vocabulary lists

LinkML defines **data schemas** — classes, attributes, relationships, enumerations, and constraints over structured data. It has no facility for:

- String template composition and parsing
- Ordered segment assembly
- Open vocabulary segments mixed with controlled vocabulary
- Connector word detection in composite strings

The current `specification.yml` (715 lines) + codegen pipeline is purpose-built for this exact use case and is the correct approach.

## Assessment 2: Catalog Entry Schema

**Verdict: Not suitable.**

The catalog entry schema (`models.py`, 681 lines) defines `StandardNameEntryBase` and three discriminated union variants: `StandardNameScalarEntry`, `StandardNameVectorEntry`, `StandardNameMetadataEntry`.

### What LinkML could express

- Basic field definitions (name, kind, unit, tags, description)
- Simple type constraints (string patterns, enumerations)
- Required/optional field declarations
- The discriminated union structure (via `ClassRule` or `any_of`)

### What LinkML cannot express

1. **Custom field validators with business logic:**
   - Unit canonicalization (dot-exponent parsing, lexicographic reordering)
   - Pint integration for SI unit validation
   - Grammar vocabulary consistency checks
   - Double-underscore enforcement

2. **Model-level cross-field validation:**
   - Provenance chain normalization tied to entry name
   - Operator naming enforcement (`_enforce_operator_naming`)
   - Reduction naming enforcement (`enforce_reduction_naming`)

3. **Complex discriminated unions with per-variant validation:**
   - Scalar/vector require `unit` field; metadata does not
   - Scalar/vector have provenance with variant-specific validation
   - Vector has computed `magnitude` property

4. **Computed properties and rendering:**
   - `magnitude` property on vectors
   - Multi-format unit rendering (pint, LaTeX)

### Why the hybrid approach fails

If we defined the schema in LinkML and generated Pydantic models with `gen-pydantic`, we'd get flat models with basic type constraints. Then we'd need to:

- Override every validator with hand-written code
- Add all model validators manually
- Add computed properties manually
- Maintain two sources of truth (LinkML schema + Python overrides)

This is strictly worse than the current approach where `models.py` is the single source of truth.

## Decision: Pydantic-Native JSON Schema

Feature 04 (JSON Schema Contract) will export the schema directly from Pydantic:

```python
from imas_standard_names.models import _STANDARD_NAME_ENTRY_ADAPTER
schema = _STANDARD_NAME_ENTRY_ADAPTER.json_schema()
```

This captures the full type structure. The Pydantic models remain the single source of truth for both validation logic and schema generation. Codex imports the JSON schema for lightweight pre-validation; full validation happens via `pip install imas-standard-names` and the Pydantic models.

## Codex Integration Path

The codex `schemas/facility.yaml` already defines a `StandardName` graph node (L2088-2110). This represents the **graph entity**, not the catalog entry. The two schemas serve different purposes:

| Schema | Purpose | Format | Location |
|--------|---------|--------|----------|
| Catalog entry | YAML file structure for catalog | JSON Schema (from Pydantic) | imas-standard-names |
| Graph node | Neo4j node properties | LinkML (in facility.yaml) | imas-codex |

The graph node schema will reference the catalog entry schema but does not need to duplicate it. When codex mints a standard name, it:

1. Validates against the JSON schema (lightweight, from Feature 04)
2. Validates with full Pydantic models (authoritative, from `pip install`)
3. Populates the graph `StandardName` node (from the LinkML schema)
