# Project Boundary

## What ISN Is

IMAS Standard Names (ISN) is a **grammar library**. It provides:

- A formal grammar for composing and validating standard names for fusion data variables
- Python APIs for parsing, composing, and validating standard names
- A SQLite-backed catalog of approved standard name entries
- The documentation site that publishes the grammar and the catalog

## What ISN Is Not

ISN is **not** a name generator. It does not decide *which* standard names should exist — it defines *what a valid standard name looks like* and holds the approved catalog.

ISN also does **not** serve tools to AI assistants. Model Context Protocol tools over standard names are served by [imas-codex](https://github.com/iterorganization/imas-codex), which calls the Python API below.

Name generation — discovering which IMAS Data Dictionary paths need standard names, minting candidates, and managing the approval pipeline — belongs to imas-codex as well.

**The boundary:**

> ISN defines what a valid standard name **is**.
> imas-codex decides what standard names to **create**, and serves them.

---

## Public API Contract

The following functions and models form the cross-project contract that imas-codex depends on. Renaming, removing, or changing signatures on these requires a coordinated release.

### Grammar

| Function | Module | Purpose |
|----------|--------|---------|
| `get_grammar_context()` | `imas_standard_names.grammar.context` | Returns all naming knowledge (patterns, vocabulary, rules) as a single dict for LLM pipelines |
| `parse_standard_name()` | `imas_standard_names.grammar.model` | Parses a name string into a typed `StandardName` with grammar segments |
| `compose_standard_name()` | `imas_standard_names.grammar.model` | Builds a valid name string from a `StandardName` or dict of parts |
| `parse()` | `imas_standard_names` | Parses a name into the diagnostic IR, preserving its operator chain outermost first |
| `compose()` | `imas_standard_names` | Renders a `StandardNameIR` into its canonical string |
| `StandardNameIR` | `imas_standard_names` | Ordered intermediate representation used for structural inspection |

```python
from imas_standard_names import StandardNameIR, compose, parse
from imas_standard_names.grammar.context import get_grammar_context
from imas_standard_names.grammar.model import parse_standard_name, compose_standard_name

# Get complete grammar context for an LLM pipeline
ctx = get_grammar_context()

# Parse a name into segments
parsed = parse_standard_name("radial_magnetic_field")
print(parsed.component)  # "radial"

# Compose from parts
name = compose_standard_name({"component": "radial", "physical_base": "magnetic_field"})

# Inspect a nested operator chain without relying on parser internals
diagnostic = parse("square_of_inverse_of_pressure")
assert isinstance(diagnostic.ir, StandardNameIR)
assert [operator.op for operator in diagnostic.ir.operators] == ["square", "inverse"]
assert compose(diagnostic.ir) == "square_of_inverse_of_pressure"
```

**Parse contract — `parse_standard_name` is the single validity oracle.** A
name is valid if and only if `parse_standard_name` returns without raising. It
enforces the full contract: known tokens, segment compatibility, the
generic-base qualification gate, the flux-surface reduction gate, and strict
canonical spelling (exactly one admissible spelling per name; a non-canonical
token order raises `NonCanonicalNameError` carrying the canonical form).

The package-level `parse`, `compose`, `StandardNameIR`, and
`validate_round_trip` exports form the stable structural-inspection surface.
`StandardNameIR.operators` is ordered outermost first. These tools are not the
validity oracle: `validate_round_trip` only answers "does this name render back
to itself?", which is strictly weaker than validity because it skips the
segment-compatibility and gating checks. Callers deciding whether a name is
acceptable must use `parse_standard_name`, then may use `parse` to inspect its
ordered structure.

`get_grammar_context()["grammar"]["vocabularies"]["qualifier_categories"]`
exposes the category-to-token mapping in canonical category order. The mapping
is derived from the same registry that canonical composition applies, so prompt
consumers can stack qualifiers in an order that the validity oracle accepts.

### Models

| Symbol | Module | Purpose |
|--------|--------|---------|
| `StandardNameEntryBase` | `imas_standard_names.models` | Pydantic model for a complete catalog entry |
| `create_standard_name_entry()` | `imas_standard_names.models` | Factory function to construct a validated entry from a dict |

```python
from imas_standard_names.models import create_standard_name_entry

entry = create_standard_name_entry({
    "name": "electron_temperature",
    "kind": "scalar",
    "unit": "eV",
    "physics_domain": "core_plasma_physics",
    "description": "Temperature of the electron population",
})
```

### Validation

| Function | Module | Purpose |
|----------|--------|---------|
| `run_semantic_checks()` | `imas_standard_names.validation.semantic` | Cross-entry consistency checks (duplicate detection, naming conflicts) |
| `validate_description()` | `imas_standard_names.validation.description` | Validates description field quality and formatting |
| `run_structural_checks()` | `imas_standard_names.validation.structural` | Validates catalog structure (required fields, types, references) |

### Constants

| Symbol | Module | Purpose |
|--------|--------|---------|
| Grammar vocabulary `StrEnum`s | `imas_standard_names.grammar.model_types` | Controlled vocabulary enums for each grammar segment |
| `PhysicsDomain` | `imas_standard_names.grammar.model_types` | Enum of valid physics domain classifications |
| Tag constants | `imas_standard_names.grammar.tag_types` | Valid tag values for secondary classification |

---

---

## Data Flow

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────┐
│  IMAS Data   │     │    imas-codex    │     │  YAML Catalog │
│  Dictionary  │────▶│  (name minting)  │────▶│  (reviewed)   │
└──────────────┘     └──────────────────┘     └───────┬───────┘
                                                      │
                                                      ▼
                                              ┌───────────────┐
                                              │  ISN catalog   │
                                              │  build (.db)   │
                                              └───────┬───────┘
                                                      │
                                                      ▼
                                              ┌───────────────┐
                                              │  docs site +   │
                                              │  Python API    │
                                              └───────────────┘
```

1. **imas-codex** reads the IMAS Data Dictionary and generates candidate standard names
2. Candidates are reviewed and merged into the **YAML catalog** repository
3. ISN **builds** the YAML into a SQLite `.db` file
4. ISN publishes the catalog through the **documentation site** and the Python API; imas-codex serves it to AI assistants

---

## Stability Commitment

The functions and models listed in the [Public API Contract](#public-api-contract) section are the cross-project interface between ISN and imas-codex. Changes to these require:

- A **coordinated release** between both projects
- A **deprecation period** for signature changes
- **Semantic versioning** — breaking changes require a major version bump

Internal modules, private functions, and tool implementation details may change without notice.
