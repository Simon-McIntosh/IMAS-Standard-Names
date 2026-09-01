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
| `parse(name, strict=True)` | `imas_standard_names` | Authoritative validity oracle for flat names and recursive ordered expressions |
| `parse(name)` | `imas_standard_names` | Diagnostic parse into a lossless `StandardNameIR`; this is the default mode |
| `compose()` | `imas_standard_names` | Renders a `StandardNameIR` into its canonical string |
| `StandardNameIR` | `imas_standard_names` | Public recursive representation; operator lists are ordered outermost first |
| `get_operator_semantics(token)` | `imas_standard_names` | Returns the immutable semantic-effect set for an operator token; unknown tokens return an empty set |
| `validate_round_trip()` | `imas_standard_names` | Diagnostic parse/render drift check; not a validity test |
| `parse_standard_name()` | `imas_standard_names.grammar.model` | Strict-validating projection into the flat `StandardName` facade |
| `compose_standard_name()` | `imas_standard_names.grammar.model` | Builds a valid name string from a `StandardName` or dict of parts |

```python
from imas_standard_names import (
    StandardNameIR,
    compose,
    get_operator_semantics,
    parse,
)
from imas_standard_names.grammar.context import get_grammar_context
from imas_standard_names.grammar.model import parse_standard_name, compose_standard_name

# Get complete grammar context for an LLM pipeline
ctx = get_grammar_context()

# Validate and project a flat name into segments
parsed = parse_standard_name("radial_magnetic_field")
print(parsed.component)  # "radial"

# Compose from parts
name = compose_standard_name({"component": "radial", "physical_base": "magnetic_field"})

# Validate and inspect a nested operator chain without relying on internals
validated = parse("square_of_inverse_of_pressure", strict=True)
assert isinstance(validated.ir, StandardNameIR)
assert [operator.op for operator in validated.ir.operators] == ["square", "inverse"]
assert compose(validated.ir) == "square_of_inverse_of_pressure"

# Operator meaning is owned by the same registry as the token. Bare-prefix
# operators can parse as qualifiers, so consumers query semantics by token.
changed = parse("change_in_electron_density", strict=True).ir
assert "change_in" in [qualifier.token for qualifier in changed.qualifiers]
assert get_operator_semantics("change_in") == frozenset({"temporal_change"})
assert get_operator_semantics("electron") == frozenset()
```

**Parse contract — `parse(name, strict=True)` is the sole validity oracle.** It
validates registry metadata, closed operand vocabulary, flat segment
compatibility, generic-base qualification, recursive flux-surface semantics,
operator precedence, and canonical spelling without first flattening the
ordered expression. A name is valid if and only if this call returns without
raising `ParseError`.

The default `parse(name)` mode is diagnostic. It preserves the lossless IR and
reports aliases or ambiguities, but it intentionally does not apply every
semantic gate. `validate_round_trip(name)` also uses that diagnostic mode and
answers only whether the parsed IR renders byte-for-byte to the input.

`parse_standard_name(name)` first performs strict validation and then projects
the result into the flat `StandardName` model. Use it when a consumer needs
flat segment fields. A recursively ordered expression can be valid according
to the oracle yet raise because the flat facade cannot represent its tree; for
example, a binary operator nested inside another binary operator. That
projection limitation does not make the name invalid.

`StandardNameIR.operators` is ordered outermost first. Unary operands and both
ordered binary operands are recursive `StandardNameIR` values. Equal-precedence
operators retain authored order; different precedence levels must place the
higher-precedence wrapper farther out. Binary split candidates are tried from
right to left and accepted only when both recursive operands resolve, so
separator words embedded in registered operands do not determine the split.

`get_grammar_context()["grammar"]["vocabularies"]["qualifier_categories"]`
exposes the category-to-token mapping in canonical category order. The mapping
is derived from the same registry that canonical composition applies, so prompt
consumers can stack qualifiers in an order that the validity oracle accepts.
Its `parse_api` metadata names the strict oracle, diagnostic default, round-trip
diagnostic, and flat-projection boundary explicitly.

Each entry under
`get_grammar_context()["grammar"]["vocabularies"]["operators"]` also exposes
its sorted `semantic_effects` list. The metadata is authored beside the token in
the operator registry and is available through `get_operator_semantics()` as a
`frozenset`. Consumers should traverse both `StandardNameIR.operators` and
`StandardNameIR.qualifiers` and query each token; this keeps the lookup correct
when a bare-prefix operator is normalized into the qualifier group. The initial
stable effect, `temporal_change`, identifies a finite change, tendency, or time
derivative without encoding those tokens in a consumer.

### Models

| Symbol | Module | Purpose |
|--------|--------|---------|
| `StandardNameEntryBase` | `imas_standard_names.models` | Pydantic model for a complete catalog entry |
| `create_standard_name_entry()` | `imas_standard_names.models` | Factory function to construct a validated entry from a dict |

```python
from imas_standard_names.models import create_standard_name_entry

entry = create_standard_name_entry(
    {
        "name": "electron_temperature",
        "kind": "scalar",
        "unit": "eV",
        "description": "Electron temperature.",
        "documentation": "Temperature of the electron population.",
    }
)
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
