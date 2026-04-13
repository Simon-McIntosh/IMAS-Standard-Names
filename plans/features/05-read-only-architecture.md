# Plan 05: Read-Only Architecture

> Make imas-standard-names a **grammar library + read-only catalog server**.
> All name generation, review, and persistence moves to imas-codex.

## Problem Statement

ISN currently conflates three concerns:

1. **Grammar library** — parse/compose, validation, vocabulary (solid, stable)
2. **Read-only server** — MCP tools for LLM agents to look up names (solid, stable)
3. **Name generator** — agent workflows, create/edit/write tools, UnitOfWork (demo-grade, superseded by imas-codex's production pipeline)

The generation surface (concern 3) is now dead weight:
- Agent workflows have no DD context → inferior name quality vs codex
- The UnitOfWork/EditCatalog CRUD pattern adds 1,200+ lines of complexity
- Write MCP tools (`create`, `edit`, `write`) are unused in production
- The Textual GUI is a non-functional stub
- GitHub issue integration (`update_standardnames`) is an unmaintained CI path

Meanwhile, codex imports 5 private `_` functions from `tools/grammar.py` because
ISN lacks a public API for grammar context. This is fragile coupling that breaks on
any ISN internal refactor.

## Approach

**Remove the write path entirely.** Not deprecate — remove. The project is pre-1.0
with no external consumers of the write MCP tools. Clean removal now avoids the
maintenance burden of deprecated code paths that will never be un-deprecated.

**Add a public grammar context API** so codex can stop importing private functions.

**Reduce dependencies** by removing packages only needed by dead code (pydantic-ai,
textual, nest-asyncio).

## Evidence: Dead Code Inventory

### Fully dead (write-only, no read-path consumers)

| Module | Lines | Purpose | Why dead |
|--------|-------|---------|----------|
| `tools/create.py` | ~280 | CreateTool MCP | Stages new entries in memory |
| `tools/edit.py` | ~170 | CatalogTool MCP (edit) | Modify/rename/delete entries |
| `tools/write.py` | ~85 | WriteTool MCP | Persist to YAML disk |
| `catalog/edit.py` | ~580 | EditCatalog façade | Staging, diff, undo, rollback |
| `unit_of_work.py` | ~160 | UnitOfWork | add/update/remove/commit/rollback |
| `editing/edit_models.py` | ~200 | ApplyInput union types | Dispatch models for edit ops |
| `editing/batch_utils.py` | ~80 | Topological sort | Dependency ordering for batch create |
| `decorators/mode.py` | ~30 | @requires_write_mode | Write-mode guard decorator |
| `agents/*.py` | ~500 | pydantic-ai workflows | Generate-review-improve loops |
| `gui/*.py` | ~200 | Textual TUI | Non-functional demo app |
| `issues/cli.py::update_standardnames` | ~100 | CI write script | Persists issue submissions |
| `vocabulary/editor.py` | ~150 | VocabularyEditor | Add/remove tokens + codegen |
| `capabilities.py` | ~40 | Feature detection | Gates write tool registration |
| **Total** | **~2,575** | | |

### Shared modules requiring cleanup (not removal)

| Module | Write-path code to remove | Read-path code to keep |
|--------|---------------------------|------------------------|
| `repository.py` | `start_uow()`, `_end_uow()`, `_active_uow` | `get()`, `list()`, `search()`, `exists()` |
| `yaml_store.py` | `write()`, `delete()` | `load()`, `load_all()` |
| `tools/__init__.py` | Write tool registration (lines 70-86) | Read tool registration |
| `tools/list.py` | `edit_catalog.diff()` integration | Core listing (already degrades gracefully) |
| `tools/vocabulary.py` | `add`/`remove` actions | `audit`/`check` actions (read-only) |
| `vocabulary/vocab_models.py` | `AddTokens`/`RemoveTokens` models | `AuditRequest`/`CheckRequest` models |
| `database/readwrite.py` | `delete()` method | `insert()` (used during catalog load), `search()` |
| `issues/cli.py` | `update_standardnames` function | `has_standardname`, `get_standardname`, `is_genericname` |
| `tools/schema.py` | Workflow guidance referencing create/write tools | Field schema documentation |

### Dependency removals

| Package | Only used by | Can remove? |
|---------|-------------|-------------|
| `pydantic-ai` | `agents/*.py` | ✅ Yes |
| `textual` | `gui/*.py` | ✅ Yes |
| `nest-asyncio` | `agents/*.py` | ✅ Yes |
| `requests` | `issues/image_assets.py` | ✅ Yes (issue integration dead) |
| `dotenv` | `agents/*.py` | ✅ Yes |

## Phases

### Phase 0: Public Grammar Context API

**Goal:** Expose a comprehensive public function that replaces all private imports in codex
and serves as the single source of truth for ALL naming knowledge needed by LLM pipelines.

**Design principle:** ISN owns ALL naming knowledge. If a rule would change when ISN
updates the grammar spec, it belongs in `get_grammar_context()`. Codex should never
hardcode naming rules — it should always consume them from this API.

**Files to create/modify:**

- `imas_standard_names/grammar/context.py` (NEW ~120 lines)

```python
"""Public grammar context API for external consumers.

This is the single entry point for any system that needs to understand
standard name grammar, naming conventions, and validation rules.
"""

def get_grammar_context() -> dict[str, Any]:
    """Return complete grammar context for prompt rendering and validation.

    Returns a dict with keys:

    Grammar mechanics:
    - canonical_pattern: str — the composition pattern
    - segment_order: str — ordering constraint text
    - template_rules: str — template application rules
    - exclusive_pairs: list[tuple[str, str]] — mutually exclusive segments
    - vocabulary_sections: list[dict] — per-segment tokens with descriptions
    - segment_descriptions: dict[str, str] — per-segment usage guidance

    Naming conventions (ISN-authoritative):
    - naming_guidance: dict — composition rules, naming conventions
    - documentation_guidance: dict — documentation writing rules
    - kind_definitions: dict — scalar/vector/metadata classification guidance
    - anti_patterns: list[dict] — common naming mistakes with corrections
    - tag_descriptions: dict — primary and secondary tag descriptions
    - applicability: dict — what should/shouldn't get standard names
    - field_guidance: dict — per-field content rules and validation
    - type_specific_requirements: dict — requirements per kind type

    LLM orientation context:
    - quick_start: str — 5-step guide for generating a standard name
    - common_patterns: list[dict] — 11 most frequent naming patterns with examples
    - critical_distinctions: list[dict] — frequently confused concepts (base vs
      modifier, orientation vs direction, etc.)
    - base_requirements: dict — required segments for valid names

    Vocabulary usage statistics:
    - vocabulary_usage_stats: dict — per-segment token frequency data:
      {segment: {token: count, ...}, most_common: [...], unused: [...]}
      Derived from the published catalog.
    """
```

- `imas_standard_names/grammar/__init__.py` — add `get_grammar_context` to `__all__`
- Move the 5 private functions from `tools/grammar.py` to `grammar/context.py` as private
  helpers, expose only `get_grammar_context()` as public
- Aggregate naming conventions from existing ISN sources:
  - `NAMING_GUIDANCE` from `grammar/field_schemas.py`
  - `DOCUMENTATION_GUIDANCE` from `grammar/field_schemas.py`
  - `FIELD_GUIDANCE`, `TYPE_SPECIFIC_REQUIREMENTS` from `grammar/field_schemas.py`
  - `PRIMARY_TAG_DESCRIPTIONS`, `SECONDARY_TAG_DESCRIPTIONS` from `grammar/tag_types.py`
  - `APPLICABILITY_INCLUDE/EXCLUDE/RATIONALE` from `grammar/constants.py`
  - Kind definitions derived from the `Kind` enum and its usage patterns
  - Anti-patterns derived from common validation failures
  - `quick_start` from `tools/grammar.py::_build_grammar_help()` → "Key Steps"
  - `common_patterns` from `tools/grammar.py::_build_grammar_help()` → "Common Patterns"
  - `critical_distinctions` from `tools/grammar.py::_build_grammar_help()` → "Critical Distinctions"
  - `base_requirements` from `grammar/constants.py` → BASE_REQUIREMENTS
  - `vocabulary_usage_stats` from catalog scan: count token usage across all
    published entries, report per-segment frequencies, most_common top-10, unused tokens

**Tests:**
- `tests/grammar/test_context.py` — verify all keys present, types correct, values non-empty
- Verify `get_grammar_context()` output matches what codex's `build_compose_context()` currently
  assembles from private imports (backward compatibility)
- Verify naming_guidance, kind_definitions, anti_patterns are non-empty and well-formed
- Verify quick_start, common_patterns, critical_distinctions are present and non-empty
- Verify vocabulary_usage_stats has per-segment data with most_common and unused lists
- Verify base_requirements is a dict with segment keys

**Why first:** Unblocks codex plan Phase 1 (replace private imports). No breaking changes.

### Phase 1: Remove Agent Workflows

**Goal:** Delete the `agents/` package and `gui/` package.

**Files to delete:**
- `imas_standard_names/agents/agent_loop_workflow.py`
- `imas_standard_names/agents/agent_list_generage_workflow.py`
- `imas_standard_names/agents/schema.py`
- `imas_standard_names/agents/node.py`
- `imas_standard_names/agents/workflow_base.py`
- `imas_standard_names/agents/namelist.py`
- `imas_standard_names/agents/load_mcp.py`
- `imas_standard_names/agents/__init__.py`
- `imas_standard_names/gui/generate.py`
- `imas_standard_names/gui/tree.py`
- `imas_standard_names/gui/standard_name.tcss`
- `imas_standard_names/gui/__init__.py`
- `.github/prompts/workflows/` (external prompt files for agent workflows)

**Dependencies to remove from pyproject.toml:**
- `pydantic-ai` (>=1.56.0)
- `textual` (>=6.1.0)
- `nest-asyncio` (>=1.6.0)
- `dotenv` (>=0.9.9)

**Tests to delete:**
- Any tests in `tests/agents/` or `tests/gui/`

**Verification:** `uv run pytest` passes. `python -m imas_standard_names` still starts MCP server.

### Phase 2: Remove Write MCP Tools

**Goal:** Remove create/edit/write tools from the MCP server.

**MUST run before Phase 3.** Write tools import from `catalog/edit.py` and `editing/`.
If Phase 3 deletes those modules first, importing the tools package crashes.

**Files to delete:**
- `imas_standard_names/tools/create.py`
- `imas_standard_names/tools/edit.py`
- `imas_standard_names/tools/write.py`

**Files to modify:**

- `imas_standard_names/tools/__init__.py` — Remove:
  - Import of `CreateTool`, `CatalogTool` (edit), `WriteTool`
  - The write-mode branch (lines ~70-86) that creates `EditCatalog` and registers write tools
  - Import of `EditCatalog`

- `imas_standard_names/tools/list.py` — Remove:
  - `edit_catalog` parameter from constructor
  - `diff()` integration for pending changes display
  - The tool still works — it already degrades gracefully when `edit_catalog` is None

- `imas_standard_names/tools/schema.py` — Simplify:
  - Remove workflow guidance that references create/write tool calls
  - Keep field schema documentation (useful for understanding entries)
  - Remove `UPSERT_GUIDANCE` import and references
  - Note: `UPSERT_GUIDANCE` constant in `grammar/field_schemas.py` is auto-generated
    from `specification.yml`. Remove from the `entry_schema` section of `specification.yml`
    and regenerate: `uv run build-grammar`

- `imas_standard_names/tools/vocabulary.py` — Remove write actions:
  - Remove `add` and `remove` action handlers
  - Keep `audit` and `check` (read-only)
  - Update action enum/dispatch

**Tests to update:**
- `tests/tools/test_create.py` → delete
- `tests/tools/test_edit.py` → delete
- `tests/tools/test_write.py` → delete
- `tests/tools/test_vocabulary.py` → remove write-action tests
- `tests/tools/test_list.py` → remove pending-diff tests
- `tests/tools/test_schema.py` → update for simplified output

### Phase 3: Remove Write Infrastructure

**Goal:** Remove UnitOfWork, EditCatalog, and supporting write code.

**Files to delete:**
- `imas_standard_names/unit_of_work.py`
- `imas_standard_names/catalog/edit.py`
- `imas_standard_names/editing/edit_models.py`
- `imas_standard_names/editing/batch_utils.py`
- `imas_standard_names/editing/__init__.py`
- `imas_standard_names/decorators/mode.py`
- `imas_standard_names/capabilities.py`
- `imas_standard_names/vocabulary/editor.py`

**Files to modify:**

- `imas_standard_names/catalog/__init__.py` — Remove `EditCatalog` re-export. Keep package
  if other modules exist, otherwise delete.

- `imas_standard_names/repository.py` — Remove:
  - `start_uow()`, `_end_uow()`, `_active_uow` attribute
  - `UnitOfWork` import
  - `reload_from_disk()` (only called after write commits)
  - Keep: `get()`, `list()`, `search()`, `exists()`, `__init__()`

- `imas_standard_names/yaml_store.py` — Remove:
  - `write()`, `delete()` methods
  - Keep: `load()`, `load_all()`, `__init__()`

- `imas_standard_names/database/readwrite.py` — Remove:
  - `delete()` method
  - Keep: `CatalogReadWrite` class, `insert()` (used during catalog load), `search()`

- `imas_standard_names/issues/cli.py` — Remove:
  - `update_standardnames` function and its Click command
  - `UnitOfWork` import
  - Keep: `has_standardname`, `get_standardname`, `is_genericname` (read-only scripts)

- `imas_standard_names/vocabulary/vocab_models.py` — Remove:
  - `AddTokens`, `RemoveTokens` models
  - Keep: `AuditRequest`, `CheckRequest`, `VocabularyInput` (if still needed for read dispatch)

- `imas_standard_names/decorators/__init__.py` — Remove `mode` re-export if present

**pyproject.toml entry points to remove:**
- `update_standardnames` console script

**Dependencies to remove:**
- `requests` (only used by `issues/image_assets.py` which is dead without `update_standardnames`)

**Tests to delete/update:**
- `tests/test_unit_of_work.py` → delete
- `tests/catalog/test_edit.py` → delete
- `tests/editing/` → delete directory
- `tests/test_repository.py` → remove write-path tests, keep read-path tests

### Phase 4: Clean Up Remaining Code

**Goal:** Remove dead imports, simplify server startup, update documentation.

**Files to modify:**

- `imas_standard_names/server.py` — Simplify `Tools` initialization (no write-mode branch)
- `imas_standard_names/services.py` — No changes needed (both functions are read-path)
- `imas_standard_names/issues/image_assets.py` — Delete (only used by dead `update_standardnames`)
- `imas_standard_names/issues/gh_repo.py` — Keep only if used by remaining issue scripts

**Remove empty packages:**
- `imas_standard_names/editing/` (if fully emptied)
- `imas_standard_names/agents/` (already deleted in Phase 1)
- `imas_standard_names/gui/` (already deleted in Phase 1)

### Phase 5: Documentation and Boundary Definition

**Goal:** Document the project boundary clearly for both human developers and AI agents.

**Files to create:**

- `docs/architecture/boundary.md` (NEW):
  - **What ISN is:** Grammar library + read-only catalog server
  - **What ISN is NOT:** A name generator (that's imas-codex)
  - **Public API contract:** `get_grammar_context()`, `compose_standard_name()`,
    `parse_standard_name()`, grammar enums, validation functions, constants
  - **MCP tool contract:** 10 read-only tools (grammar, schema, compose, search,
    check, fetch, list, validate, vocabulary tokens, tokamak params)
  - **Data flow diagram:** codex generates → YAML catalog → ISN builds .db → ISN serves

- `docs/architecture/data-flow.md` (NEW):
  - End-to-end lifecycle: DD paths → codex mint → graph → publish → YAML catalog →
    human review → ISN catalog build → .db distribution → MCP read tools
  - Where each project fits in the pipeline

- Update `AGENTS.md`:
  - Remove references to agent workflows, create/edit/write tools
  - Add `get_grammar_context()` documentation
  - Document the boundary: "ISN defines what a valid standard name IS.
    imas-codex decides what standard names to CREATE."

- Update `README.md`:
  - Remove generate/create workflow examples
  - Focus on: install, grammar reference, read-only MCP tools, catalog building

### Phase 6: Testing and Validation

**Goal:** Ensure all remaining functionality works, test suite is clean.

**Actions:**
1. Run full test suite: `uv run pytest`
2. Start MCP server: `python -m imas_standard_names` — verify 10 tools registered
3. Verify catalog build: `standard-names build <path>` still works
4. Verify catalog search: `standard-names search <query>` still works
5. Verify validation CLI: `validate_catalog <path>` still works
6. Verify grammar codegen: `build-grammar` still works
7. Check import surface: no remaining imports of deleted modules

**New tests to add:**
- `tests/grammar/test_context.py` — public API tests for `get_grammar_context()`
- `tests/tools/test_readonly_server.py` — integration test: start server, verify only
  read-only tools are registered, verify write tools are absent

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Python files | ~95 | ~65 |
| Lines of code | ~12,000 | ~8,500 |
| MCP tools | 15 | 10 |
| Dependencies | 12 core | 7 core |
| Console scripts | 10 | 7 |
| Test files | ~60 | ~45 |

## Implementation Notes

- **Order matters:** Phase 0 first (unblocks codex). Phase 1 (agents) is independent.
  **Phase 2 MUST precede Phase 3** — write tools import from `catalog/edit.py` which
  Phase 3 deletes. If Phase 3 runs first, importing the tools package crashes.
  Phase 1 can parallel with Phase 2.
- **Each phase is one commit.** Atomic, reviewable, revertible.
- **Run `uv run pytest` after every phase.** Fix any import errors immediately.
- **Coordinate with codex plan:** Phase 0 here enables codex Phase 1 there.
  Codex should update its ISN pin after Phase 0 lands.

## Documentation Updates

| Target | When |
|--------|------|
| `AGENTS.md` | Phase 5 — remove write workflow docs, add boundary definition |
| `README.md` | Phase 5 — remove generation examples, focus on read-only usage |
| `docs/architecture/boundary.md` | Phase 5 — NEW, defines project scope |
| `docs/architecture/data-flow.md` | Phase 5 — NEW, end-to-end lifecycle |
| `pyproject.toml` | Phases 1-3 — remove deps and entry points |
| `CONTRIBUTING.md` | Phase 5 — update development workflow |
