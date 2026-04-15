# Feature 07: Rename `ids_paths` → `dd_paths`

**Repository:** imas-standard-names
**Status:** Planned
**Coordinated with:** imas-codex plan `plans/features/sn-extraction-coverage-gaps.md` Phase 0d

---

## Problem

The `ids_paths` field name is ambiguous — "IDS" could refer to IMAS Interface Data Structures
or be confused with generic identifiers. The field exclusively stores IMAS Data Dictionary paths.
Renaming to `dd_paths` makes the semantics explicit and aligns with the codex project's
source-agnostic architecture where DD paths are one of several source types.

The codex project is introducing `source_paths` (a union of DD paths and facility signal IDs)
on its StandardName graph nodes. The ISN catalog field stores only the DD subset and should
be named accordingly.

## Scope

Rename `ids_paths` → `dd_paths` across all ISN code, schema, and database.
No backward compatibility period — clean break.

## Impact Analysis

**14 references across 5 source files:**

| File | References | Changes |
|------|-----------|---------|
| `imas_standard_names/models.py` | 1 | Field rename on `StandardNameEntry` |
| `imas_standard_names/field_types.py` | 1 | Type alias `IdsPaths` → `DdPaths` |
| `imas_standard_names/grammar/specification.yml` | 4 | Field name + type_specific optional_fields |
| `imas_standard_names/grammar/field_schemas.py` | 6 | JSON schema, descriptions, type requirements |
| `imas_standard_names/services.py` | 3 | SQLite read query |
| `imas_standard_names/database/readwrite.py` | 4 | SQLite table + write query |

## Implementation

### Phase 1: Code and schema rename

**1.1 Type alias** (`field_types.py`):
```python
# Old
IdsPaths = Annotated[list[str], Field(description="IMAS Data Dictionary paths...")]

# New
DdPaths = Annotated[list[str], Field(description="IMAS Data Dictionary paths...")]
```

Update `__all__` export.

**1.2 Pydantic model** (`models.py`):
```python
# Old
ids_paths: IdsPaths = Field(default_factory=list)

# New
dd_paths: DdPaths = Field(default_factory=list)
```

**1.3 Grammar specification** (`grammar/specification.yml`):
- Rename field definition `ids_paths:` → `dd_paths:`
- Update all `optional_fields` lists in `type_specific` section (scalar, vector, metadata)
- Update description, format, examples, guidance (content unchanged, just field name)

**1.4 Field schemas** (`grammar/field_schemas.py`):
- Rename key in `FIELD_DESCRIPTIONS` dict
- Rename key in `FIELD_CONSTRAINTS` dict
- Rename key in `FIELD_GUIDANCE` dict
- Update all `optional_fields` lists in `TYPE_SPECIFIC_REQUIREMENTS`

**1.5 Services** (`services.py`):
- Variable rename `ids_paths` → `dd_paths`
- Dict key `"ids_paths"` → `"dd_paths"`

### Phase 2: Database schema migration

**2.1 SQLite table rename** (`database/readwrite.py`):

Schema DDL change:
```sql
-- Old
CREATE TABLE ids_path (
    name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE,
    ids_path TEXT NOT NULL,
    PRIMARY KEY(name, ids_path)
);

-- New
CREATE TABLE dd_path (
    name TEXT NOT NULL REFERENCES standard_name(name) ON DELETE CASCADE,
    dd_path TEXT NOT NULL,
    PRIMARY KEY(name, dd_path)
);
```

Write query:
```python
# Old
"INSERT INTO ids_path(name, ids_path) VALUES (?,?)"

# New
"INSERT INTO dd_path(name, dd_path) VALUES (?,?)"
```

Read query in `services.py`:
```python
# Old
"SELECT ids_path FROM ids_path WHERE name=?"

# New
"SELECT dd_path FROM dd_path WHERE name=?"
```

**2.2 Database is regenerated from YAML on each build** — no migration needed.
The SQLite database is built from catalog YAML files at package build time.
Renaming the DDL and queries is sufficient.

### Phase 3: Tests and validation

- Update any test fixtures referencing `ids_paths`
- `rg '\bids_paths\b|\bids_path\b|\bIdsPaths\b' imas_standard_names/ tests/` → 0 matches
- `uv run pytest` passes
- `uv run ruff check . && uv run ruff format .`

## Acceptance Criteria

- [ ] Zero references to `ids_paths`, `ids_path`, or `IdsPaths` in source code
- [ ] `StandardNameEntry` model has `dd_paths: DdPaths` field
- [ ] Grammar specification uses `dd_paths` field name
- [ ] SQLite schema uses `dd_path` table with `dd_path` column
- [ ] All tests pass
- [ ] `create_standard_name_entry({"dd_paths": [...]})` works

## Coordination with imas-codex

The codex project's Phase 0d renames:
- Graph property: `imas_paths` → `source_paths` (generic union list)
- Code variables: `ids_paths` → `dd_paths` (DD-specific)
- Catalog export: outputs `dd_paths` key in YAML
- Catalog import: reads `dd_paths` key from YAML

**Ordering:** Either repo can land first. Codex catalog_import already maps field names
explicitly (`"dd_paths"` key in import dict), so the ISN model field name is not a
runtime dependency. The rename is a naming alignment, not a protocol change.
