# Unify PhysicsDomain: Rename Tags → PhysicsDomain

> **Repo**: imas-standard-names
> **Status**: planned
> **Depends on**: nothing (this is the upstream change)
> **Blocked by this**: imas-codex plan `15-import-physics-domain.md`

## Problem

The `tags[0]` field on StandardNameEntry serves as a physics domain classifier —
it determines catalog directory structure, groups entries by physics area, and
maps 1:1 to IMAS IDS families. But it's called "tags" alongside secondary
cross-cutting tags, obscuring its role as a controlled vocabulary enum.

Meanwhile, imas-codex maintains a parallel `PhysicsDomain` enum (22 values)
that classifies ~250K graph nodes. The two vocabularies overlap ~60% but use
different names, formats (hyphens vs underscores), and granularity levels.

## Goal

1. Rename `tags[0]` → `physics_domain` (typed `PhysicsDomain` enum)
2. Keep `tags` for secondary tags only (list of `SecondaryTag`)
3. Export `PhysicsDomain` enum so imas-codex can import it as canonical source
4. Maintain backward compatibility for existing YAML catalog entries

## Unified PhysicsDomain Enum (31 values)

Starting from imas-codex's 22 in-use values (preserving graph data), adding
9 semantically unique values from current primary tags.

### Kept from codex (22 — all in-use on ~250K graph nodes)

```
equilibrium                       transport
magnetohydrodynamics              turbulence
auxiliary_heating                  current_drive
plasma_wall_interactions          divertor_physics
edge_plasma_physics               particle_measurement_diagnostics
electromagnetic_wave_diagnostics  radiation_measurement_diagnostics
magnetic_field_diagnostics        mechanical_measurement_diagnostics
plasma_measurement_diagnostics    plasma_control
machine_operations                magnetic_field_systems
structural_components             plant_systems
data_management                   computational_workflow
general
```

### Added from primary tags (9 — semantically unique, not covered by codex)

| New value | From tag | Rationale |
|-----------|----------|-----------|
| `core_plasma_physics` | `core-physics` | Core profiles/kinetics — distinct from equilibrium/transport |
| `fast_particles` | `fast-particles` | Energetic particle physics |
| `runaway_electrons` | `runaway-electrons` | Safety-relevant physics |
| `waves` | `waves` | Wave propagation/RF — distinct from heating |
| `fueling` | `fueling` | Gas/pellet injection systems |
| `plasma_initiation` | `plasma-initiation` | Startup physics |
| `spectroscopy` | `spectroscopy` | Major diagnostic family |
| `neutronics` | `neutronics` | Neutron diagnostics |
| `gyrokinetics` | (codex only) | Already in codex enum, carry forward |

### NOT added (14 current primary tags — already covered)

| Tag | Covered by | Reason |
|-----|-----------|--------|
| `nbi` | `auxiliary_heating` | Too granular — one heating method |
| `ec-heating` | `auxiliary_heating` | Too granular |
| `ic-heating` | `auxiliary_heating` | Too granular |
| `lh-heating` | `auxiliary_heating` | Too granular |
| `thomson-scattering` | `particle_measurement_diagnostics` | One diagnostic |
| `interferometry` | `electromagnetic_wave_diagnostics` | One diagnostic |
| `reflectometry` | `electromagnetic_wave_diagnostics` | One diagnostic |
| `imaging` | `radiation_measurement_diagnostics` | Camera-based fits radiation |
| `fundamental` | `general` | "Universal quantities" = uncategorized |
| `coils-and-control` | `plasma_control` | Same concept |
| `edge-physics` | `edge_plasma_physics` | Same concept |
| `wall-and-structures` | `plasma_wall_interactions` + `structural_components` | Split is more precise |
| `pulse-management` | `machine_operations` | Same concept |
| `data-products` | `data_management` | Same concept |
| `utilities` | `computational_workflow` | Same concept |

### Tag → PhysicsDomain alias mapping

```python
TAG_TO_PHYSICS_DOMAIN: dict[str, str] = {
    # Exact matches (tag = enum value)
    "equilibrium": "equilibrium",
    "transport": "transport",
    "turbulence": "turbulence",
    "magnetics": "magnetic_field_diagnostics",
    "waves": "waves",
    "fueling": "fueling",
    "spectroscopy": "spectroscopy",
    "neutronics": "neutronics",
    # Renamed
    "mhd": "magnetohydrodynamics",
    "edge-physics": "edge_plasma_physics",
    "core-physics": "core_plasma_physics",
    "fast-particles": "fast_particles",
    "runaway-electrons": "runaway_electrons",
    "radiation-diagnostics": "radiation_measurement_diagnostics",
    "coils-and-control": "plasma_control",
    "pulse-management": "machine_operations",
    "wall-and-structures": "plasma_wall_interactions",
    "plasma-initiation": "plasma_initiation",
    "fundamental": "general",
    # Many-to-one (heating methods → auxiliary_heating)
    "nbi": "auxiliary_heating",
    "ec-heating": "auxiliary_heating",
    "ic-heating": "auxiliary_heating",
    "lh-heating": "auxiliary_heating",
    # Many-to-one (specific diagnostics → grouped)
    "thomson-scattering": "particle_measurement_diagnostics",
    "interferometry": "electromagnetic_wave_diagnostics",
    "reflectometry": "electromagnetic_wave_diagnostics",
    "imaging": "radiation_measurement_diagnostics",
    # Operational
    "data-products": "data_management",
    "utilities": "computational_workflow",
}
```

---

## Phase 1: Add PhysicsDomain enum and vocabularies YAML

### 1a. Create `grammar/vocabularies/physics_domains.yml`

New YAML file with the 31 unified enum values. Structure mirrors `tags.yml`:

```yaml
# IMAS Physics Domain Controlled Vocabulary
# Defines the PhysicsDomain enum — the canonical physics classification
# shared between imas-standard-names and imas-codex.
#
# Format: underscore_case identifiers (Python enum compatible)
# Each entry: description, category, ids (optional list of IMAS IDS names)

physics_domains:
  equilibrium:
    description: MHD equilibrium, flux surfaces, magnetic geometry, coordinate systems
    category: core_plasma
    ids: [equilibrium]
  transport:
    description: Transport coefficients, fluxes, neoclassical and anomalous transport
    category: core_plasma
    ids: [core_transport, edge_transport, transport_solver_numerics]
  # ... (all 31 values with descriptions, categories, IDS lists)

# Backward-compatible alias mapping from legacy primary tags
tag_aliases:
  mhd: magnetohydrodynamics
  edge-physics: edge_plasma_physics
  core-physics: core_plasma_physics
  # ... (full TAG_TO_PHYSICS_DOMAIN mapping)
```

### 1b. Create `grammar_codegen/physics_domain_spec.py`

New spec loader (mirrors `tag_spec.py`):

```python
@dataclass
class PhysicsDomainSpec:
    domains: tuple[str, ...]           # enum values
    descriptions: dict[str, str]       # domain → description
    categories: dict[str, str]         # domain → category
    tag_aliases: dict[str, str]        # old tag → domain
    
    @classmethod
    def from_file(cls, path: Path) -> PhysicsDomainSpec: ...
```

### 1c. Extend `grammar_codegen/generate.py`

Add codegen for `PhysicsDomain` into `grammar/tag_types.py` (or a new
`grammar/physics_domain_types.py` — decision: keep in tag_types since
it replaces PrimaryTag):

```python
class PhysicsDomain(str, Enum):
    """Physics domain classification for IMAS standard names."""
    EQUILIBRIUM = "equilibrium"
    TRANSPORT = "transport"
    # ... all 31 values

PHYSICS_DOMAIN_DESCRIPTIONS: dict[str, str] = { ... }
TAG_TO_PHYSICS_DOMAIN: dict[str, str] = { ... }
```

### 1d. Run `build-grammar` and verify codegen

```bash
uv run build-grammar
# Verify grammar/tag_types.py now contains PhysicsDomain enum
```

**Files created/modified:**
- CREATE `grammar/vocabularies/physics_domains.yml`
- CREATE `grammar_codegen/physics_domain_spec.py`
- MODIFY `grammar_codegen/generate.py` (add PhysicsDomain codegen)
- REGENERATE `grammar/tag_types.py` (adds PhysicsDomain, TAG_TO_PHYSICS_DOMAIN)

---

## Phase 2: Split `tags` field into `physics_domain` + `tags`

### 2a. Update `field_types.py`

```python
# Replace:
#   Tags = Annotated[list[str], Field(...)]
# With:
PhysicsDomainField = Annotated[str, Field(
    description="Physics domain classification from PhysicsDomain enum.",
)]
Tags = Annotated[list[str], Field(
    description="Secondary classification tags from controlled vocabulary.",
)]
```

### 2b. Update `models.py` — StandardNameEntryBase

```python
class StandardNameEntryBase(BaseModel):
    # ... existing fields ...
    physics_domain: PhysicsDomainField  # NEW — required, replaces tags[0]
    tags: Tags = Field(default_factory=list)  # CHANGED — now optional, secondary only
    
    @field_validator("physics_domain")
    def validate_physics_domain(cls, v: str) -> str:
        """Validate physics_domain is a valid PhysicsDomain enum value."""
        from .grammar.tag_types import PhysicsDomain
        try:
            PhysicsDomain(v)
        except ValueError:
            raise ValueError(f"Invalid physics_domain: '{v}'. Valid: {[d.value for d in PhysicsDomain]}")
        return v
    
    @field_validator("tags")
    def validate_secondary_tags(cls, v: list[str]) -> list[str]:
        """Validate tags are all secondary tags (no primary/physics_domain values)."""
        # Remove the primary tag reordering logic
        # Only validate against SECONDARY_TAGS
        ...
```

### 2c. Add backward-compatible YAML loading

The YAML store must handle both old format (`tags: [magnetics, measured]`) and
new format (`physics_domain: magnetic_field_diagnostics\ntags: [measured]`).

Add a model validator to StandardNameEntryBase:

```python
@model_validator(mode="before")
@classmethod
def migrate_tags_to_physics_domain(cls, data: dict) -> dict:
    """Backward compat: extract physics_domain from tags[0] if not set."""
    if isinstance(data, dict) and "physics_domain" not in data:
        tags = data.get("tags", [])
        if tags and tags[0] in TAG_TO_PHYSICS_DOMAIN:
            data["physics_domain"] = TAG_TO_PHYSICS_DOMAIN[tags[0]]
            data["tags"] = tags[1:]  # remaining are secondary
        elif tags and tags[0] in [d.value for d in PhysicsDomain]:
            data["physics_domain"] = tags[0]
            data["tags"] = tags[1:]
    return data
```

### 2d. Update `grammar/specification.yml`

Replace all `tags[0]` references with `physics_domain`. Update field descriptions.

### 2e. Update `grammar/field_schemas.py`

Add `physics_domain` field description. Update `tags` description to say
"secondary classification tags only".

**Files modified:**
- MODIFY `field_types.py` (add PhysicsDomainField, narrow Tags)
- MODIFY `models.py` (split field, add validators, backward compat)
- MODIFY `grammar/specification.yml` (update field docs)
- MODIFY `grammar/field_schemas.py` (add physics_domain description)

---

## Phase 3: Update storage, rendering, tools, database

### 3a. `yaml_store.py` — directory by physics_domain

```python
# Line 103-108: Change from tags[0] to physics_domain
if hasattr(model, "physics_domain") and model.physics_domain:
    path = self.root / model.physics_domain / f"{model.name}.yml"
else:
    path = self.root / f"{model.name}.yml"
```

### 3b. `unit_of_work.py` — file movement detection

```python
# Line 113-114: Change from tags[0] to physics_domain
if m.physics_domain:
    expected_subdir = m.physics_domain
    expected_path = self.repo.store.root / expected_subdir / f"{m.name}.yml"
```

### 3c. `repository.py` — filtering

Add `physics_domain` filter parameter alongside existing `tags` filter:

```python
def find(self, ..., physics_domain: str | None = None, tags: str | list[str] | None = None, ...):
    if physics_domain:
        conditions.append("s.name IN (SELECT name FROM standard_name WHERE physics_domain = ?)")
        # Or filter in-memory after loading
```

### 3d. `database/readwrite.py` — schema update

Add `physics_domain TEXT` column to `standard_name` table. Bump `CATALOG_SCHEMA_VERSION`.
Store physics_domain as a column, not in the `tag` junction table.

```sql
CREATE TABLE standard_name (
  name TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  unit TEXT,
  description TEXT NOT NULL,
  documentation TEXT,
  validity_domain TEXT,
  physics_domain TEXT,          -- NEW
  deprecates TEXT,
  superseded_by TEXT,
  is_dimensionless INTEGER NOT NULL DEFAULT 0
);
```

Update the tag insertion loop to only store secondary tags:

```python
for t in getattr(m, "tags", []) or []:
    c.execute("INSERT INTO tag(name, tag) VALUES (?,?)", (m.name, t))
# physics_domain stored in main table, not tag junction
```

### 3e. `rendering/catalog.py` — group by physics_domain

```python
def get_tags(self) -> dict[str, list[dict]]:
    # Rename to get_by_physics_domain() or keep name for compat
    for item in names:
        pd = item.get("physics_domain", "general")
        groups[pd].append(item)
```

### 3f. `rendering/html.py` — display physics_domain + tags separately

### 3g. `tools/tokens.py` — vocabulary builder

Replace `primary_tags` segment with `physics_domains` segment.
Update `entry.tags[0]` access to `entry.physics_domain`.

### 3h. `tools/schema.py` — export PhysicsDomain descriptions

Replace `PRIMARY_TAG_DESCRIPTIONS` with `PHYSICS_DOMAIN_DESCRIPTIONS`.

### 3i. `tools/validate.py` — validate physics_domain field

### 3j. `tools/fetch.py` — include physics_domain in output

### 3k. `grammar/tags.py` — update functions

- Keep `get_secondary_tags()` as-is
- Rename `get_primary_tags()` → `get_physics_domains()` (keep old as deprecated alias)
- Add `get_physics_domain_description(domain: str) -> str`
- Update `validate_tags()` to only validate secondary tags

### 3l. `grammar/__init__.py` — export PhysicsDomain

```python
from .tag_types import PhysicsDomain, TAG_TO_PHYSICS_DOMAIN
```

### 3m. Top-level `__init__.py` — export PhysicsDomain

```python
from .grammar.tag_types import PhysicsDomain
```

**Files modified:**
- MODIFY `yaml_store.py`
- MODIFY `unit_of_work.py`
- MODIFY `repository.py`
- MODIFY `database/readwrite.py`
- MODIFY `rendering/catalog.py`
- MODIFY `rendering/html.py`
- MODIFY `tools/tokens.py`
- MODIFY `tools/schema.py`
- MODIFY `tools/validate.py`
- MODIFY `tools/fetch.py`
- MODIFY `grammar/tags.py`
- MODIFY `grammar/__init__.py`
- MODIFY `imas_standard_names/__init__.py`

---

## Phase 4: Migrate example catalog entries

The 8 example catalog directories use hyphenated primary tag names as
directory names. These need renaming to underscore physics_domain values.

### Directory renames

```
resources/standard_name_examples/core-physics/     → core_plasma_physics/
resources/standard_name_examples/edge-physics/      → edge_plasma_physics/
resources/standard_name_examples/equilibrium/       → equilibrium/          (unchanged)
resources/standard_name_examples/fundamental/       → general/
resources/standard_name_examples/magnetics/         → magnetic_field_diagnostics/
resources/standard_name_examples/mhd/               → magnetohydrodynamics/
resources/standard_name_examples/transport/         → transport/            (unchanged)
resources/standard_name_examples/wall-and-structures/ → plasma_wall_interactions/
```

### YAML entry migration

Each `.yml` file needs:
1. Add `physics_domain: <value>` field
2. Remove primary tag from `tags` list (keep secondary tags only)

Example — before:
```yaml
name: flux_loop_voltage
tags:
- magnetics
- measured
- time-dependent
```

After:
```yaml
name: flux_loop_voltage
physics_domain: magnetic_field_diagnostics
tags:
- measured
- time-dependent
```

Write a migration script (one-time, don't commit):
```python
for entry_path in Path("resources/standard_name_examples").rglob("*.yml"):
    data = yaml.safe_load(entry_path.read_text())
    if "physics_domain" not in data and data.get("tags"):
        data["physics_domain"] = TAG_TO_PHYSICS_DOMAIN.get(data["tags"][0], data["tags"][0])
        data["tags"] = data["tags"][1:]
    entry_path.write_text(yaml.dump(data))
```

---

## Phase 5: Update tests

~41 test files reference tags. Key changes:

### Critical test files

| File | Changes |
|------|---------|
| `tests/test_tag_types.py` | Test `PhysicsDomain` enum values, descriptions, `TAG_TO_PHYSICS_DOMAIN` |
| `tests/test_primary_tag_change_moves_file.py` | Rename to `test_physics_domain_change_moves_file.py`. Use `physics_domain` field |
| `tests/test_yaml_store.py` | Update path formation to use `physics_domain` |
| `tests/test_unit_of_work.py` | Update `expected_subdir` to use `physics_domain` |
| `tests/test_validate_catalog.py` | Update directory creation to use `physics_domain` |
| `tests/test_validation_timing.py` | Update assertions from `tags[0]` to `physics_domain` |
| `tests/test_integrity.py` | Update tag access patterns |
| `tests/conftest.py` | Update fixtures: split `tags` into `physics_domain` + `tags` |

### Pattern replacement across all tests

```python
# Old pattern:
tags=["magnetics", "measured", "time-dependent"]
entry.tags[0]
primary_tag = entry.tags[0]

# New pattern:
physics_domain="magnetic_field_diagnostics", tags=["measured", "time-dependent"]
entry.physics_domain
physics_domain = entry.physics_domain
```

### Backward compatibility test

Add test verifying old-format YAML (tags[0] as primary) loads correctly via
the `migrate_tags_to_physics_domain` model validator.

---

## Phase 6: Release

```bash
# Verify everything passes
uv run pytest

# Build grammar to regenerate all codegen files
uv run build-grammar

# Run full test suite again
uv run pytest

# Release candidate (currently in RC mode: v0.7.0rc1)
# This is a breaking API change, so bump minor → new RC series
uv run standard-names release --bump minor -m "feat: rename primary tags to PhysicsDomain enum

BREAKING CHANGE: tags[0] replaced by physics_domain field.
Old YAML format auto-migrated on load.
PhysicsDomain enum exported for imas-codex consumption."

# This creates v0.8.0rc1 tag and pushes to upstream → triggers PyPI publish
# After CI passes and imas-codex integration verified:
uv run standard-names release --final -m "release: PhysicsDomain enum and tag rename"
# Creates v0.8.0 stable release
```

---

## Documentation Updates

| Target | Changes |
|--------|---------|
| `docs/development/specification.md` | Update tags[0] → physics_domain |
| `docs/development/style-guide.md` | Update tag usage guidance |
| `docs/development/quickstart.md` | Update entry creation examples |
| `docs/metadata-conventions.md` | Document physics_domain field and enum |
| `README.md` | Update quick-start examples |

---

## Risk Mitigation

- **Backward compat**: `model_validator(mode="before")` auto-migrates old YAML
  format. Existing catalogs continue to load without manual edits.
- **Directory rename**: Migration script handles physical file moves. Git tracks
  renames cleanly.
- **Downstream breakage**: imas-codex currently doesn't import from
  imas-standard-names for PhysicsDomain. The codex plan (separate) handles
  switching the import. Until then, both enums coexist.
- **PyPI timing**: Release RC first, verify imas-codex can `pip install` and
  import `PhysicsDomain`, then finalize.
