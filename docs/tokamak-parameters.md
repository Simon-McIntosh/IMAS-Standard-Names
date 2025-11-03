# Tokamak Parameters Database

## Overview

The tokamak parameters database provides authoritative, curated parameters for major tokamak fusion devices worldwide. This reference data is essential for documenting typical values in IMAS standard names and ensuring consistency across the fusion community.

## Purpose and Scope

**Purpose:**
- Provide verified geometry and physics parameters for major tokamaks
- Enable accurate typical value citations in standard name documentation
- Support comparative analysis across different fusion devices
- Maintain authoritative reference data with clear provenance

**Scope:**
- Major operational tokamaks (JET, DIII-D, ASDEX-Upgrade, EAST, KSTAR, JT-60SA, TCV, WEST, MAST-U)
- ITER (under construction)
- Important decommissioned devices (Alcator C-Mod)
- Geometry: major radius, minor radius, plasma volume, elongation, triangularity, aspect ratio
- Physics: magnetic field, plasma current, densities, temperatures, confinement time, fusion performance

## Using the MCP Tool

The `get_tokamak_parameters` MCP tool provides programmatic access to the database with optional statistics aggregation.

### Single Machine

Retrieve parameters for one tokamak:

```python
# Returns full parameter set for ITER
get_tokamak_parameters(machines='ITER')
```

**Returns:**
```yaml
machine: ITER
facility: ITER Organization
location: Cadarache, France
operational_status: under_construction
geometry:
  major_radius:
    value: 6.2
    unit: m
    symbol: R_0
  ...
physics:
  toroidal_magnetic_field:
    value: 5.3
    unit: T
    symbol: B_T
  ...
catalog_version: "x.y.z"
```

### Multiple Machines with Statistics

Retrieve parameters for multiple machines with aggregated statistics:

```python
# Returns full data + min/max/mean/median statistics
get_tokamak_parameters(machines='ITER JET DIII-D')
```

**Returns:**
```yaml
machines:
  iter: { ... full ITER data ... }
  jet: { ... full JET data ... }
  diii-d: { ... full DIII-D data ... }
statistics:
  geometry:
    major_radius:
      min: 1.67
      max: 6.2
      mean: 3.61
      median: 2.96
      unit: m
      symbol: R_0
      machine_count: 3
    ...
  physics:
    toroidal_magnetic_field:
      min: 2.2
      max: 5.3
      mean: 3.65
      median: 3.45
      unit: T
      symbol: B_T
      machine_count: 3
    ...
machine_count: 3
catalog_version: "x.y.z"
```

### All Machines

Retrieve the complete database with statistics:

```python
# Returns all machines with comprehensive statistics
get_tokamak_parameters(machines='all')

# Or simply (defaults to 'all')
get_tokamak_parameters()
```

## Data Sources

### Primary Sources

1. **FusionWiki (CIEMAT)**
   - URL: https://fusionwiki.ciemat.es
   - Comprehensive, community-maintained database
   - Regular updates from facility operators
   - Primary source for geometric and operational parameters

2. **Official Facility Websites**
   - ITER Organization: https://www.iter.org
   - EUROfusion (JET): https://www.euro-fusion.org
   - General Atomics (DIII-D): https://www.ga.com
   - IPP (ASDEX-Upgrade): https://www.ipp.mpg.de
   - And others (see individual YAML files)

3. **Nuclear Fusion Journal**
   - Technical papers and review articles
   - Used for verification and detailed parameters

### Data Quality

- All parameters verified against multiple sources where possible
- Discrepancies noted in `note` fields
- Sources cited with URLs and access dates
- Regular review cycle (annually)

## Update Workflow

### Regular Maintenance

1. **Annual Review**: Check all parameters against current sources
2. **Update Tracking**: Maintain `last_updated` and `accessed` dates
3. **Version Control**: All changes tracked in git with clear commit messages

### Adding New Tokamaks

To add a new tokamak to the database:

1. **Create YAML File**
   - Filename: `machine-name.yml` (lowercase, hyphens for spaces)
   - Location: `imas_standard_names/resources/tokamak_parameters/`
   - Follow schema in `schema.yml`

2. **Required Fields**
   ```yaml
   machine: Machine Name
   facility: Operating Organization
   location: City, Country
   operational_status: operational | under_construction | decommissioned
   last_updated: "YYYY-MM-DD"
   sources:
     - url: https://...
       accessed: "YYYY-MM-DD"
       description: "Source description"
   
   geometry:
     major_radius: { value, unit, symbol }
     minor_radius: { value, unit, symbol }
     plasma_volume: { value, unit, symbol }
     # Optional: elongation, triangularity, aspect_ratio
   
   physics:
     toroidal_magnetic_field: { value, unit, symbol }
     plasma_current: { value, unit, symbol }
     # Optional: edge_safety_factor, densities, temperatures, etc.
   ```

3. **Validation**
   - Run tests: `uv run pytest tests/test_tokamak_parameters.py`
   - Verify loading: `TokamakParametersDB().get('machine-name')`

4. **Documentation**
   - Add to table in `README.md`
   - Update this documentation if adding new parameters

### Updating Existing Parameters

1. Check authoritative sources for updates
2. Update values in YAML file
3. Update `last_updated` field
4. Update source `accessed` dates
5. Add notes for significant changes
6. Run tests to verify schema compliance

## Using in Standard Names Documentation

### Citation Guidelines

**Always cite specific machines** when providing typical values in standard name documentation:

**Good:**
```markdown
Typical values:
- ITER: 6.2 m (design)
- JET: 2.96 m
- DIII-D: 1.67 m
```

**Better (with MCP tool):**
```markdown
Typical values:
Use get_tokamak_parameters(machines='ITER JET DIII-D') to retrieve:
- ITER: 6.2 m (design, baseline scenario)
- JET: 2.96 m
- DIII-D: 1.67 m
```

**Best (with statistics for ranges):**
```markdown
Typical values:
Major tokamaks range from 0.67 m (C-Mod, compact) to 6.2 m (ITER, design).
Use get_tokamak_parameters(machines='all') for complete parameter ranges.
```

### Workflow for Documentation

1. **Identify Parameter**: Determine which tokamak parameter is relevant
2. **Query Tool**: Use `get_tokamak_parameters` to retrieve verified values
3. **Select Machines**: Choose representative machines (large/small, operational/design)
4. **Include Context**: Note operational scenarios, design vs. achieved values
5. **Cite Sources**: Reference specific machines, not generic "typical tokamaks"

### Examples

**For major radius documentation:**
```markdown
The major radius of major tokamaks varies widely:
- Large machines: ITER (6.2 m), JET (2.96 m), JT-60SA (2.96 m)
- Medium machines: DIII-D (1.67 m), ASDEX-Upgrade (1.65 m)
- Compact machines: C-Mod (0.67 m), TCV (0.88 m)
- Spherical tokamaks: MAST-U (0.85 m, A=1.3)

Use get_tokamak_parameters(machines='all') for complete parameter statistics.
```

**For plasma current documentation:**
```markdown
Plasma current capabilities:
- ITER: 15 MA (design, baseline scenario)
- JET: 4.8 MA (typical maximum)
- DIII-D: 2.0 MA (typical maximum)
- C-Mod: 1.7 MA (highest current density achieved)

Current density scaling depends strongly on device size and aspect ratio.
```

## Parameter Definitions

### Geometry Parameters

- **major_radius** (R₀): Distance from tokamak center to plasma center
- **minor_radius** (a): Plasma radius (horizontal unless noted)
- **plasma_volume** (V_p): Total plasma volume
- **elongation** (κ): Ratio of plasma height to width
- **triangularity** (δ): Measure of plasma D-shape
- **aspect_ratio** (A): R₀/a

### Physics Parameters

- **toroidal_magnetic_field** (B_T): Magnetic field at major radius
- **plasma_current** (I_p): Total toroidal plasma current
- **edge_safety_factor** (q₉₅): Safety factor at 95% flux surface
- **electron_density** (n_e): Electron density (typically volume averaged)
- **ion_temperature** (T_i): Ion temperature (typically volume averaged)
- **electron_temperature** (T_e): Electron temperature (typically volume averaged)
- **energy_confinement_time** (τ_E): Global energy confinement time
- **fusion_power** (P_fusion): Fusion power (DT devices only)
- **fusion_gain** (Q): Ratio of fusion power to heating power

## Notes on Parameter Values

### Typical vs. Maximum

Most values represent **typical high-performance operation**, not absolute maximums. This provides more useful reference values for standard name documentation.

### Scenario Dependence

Some parameters depend on operational scenario:
- Fusion power and Q: Specific scenario (e.g., ITER baseline Q=10)
- Confinement time: H-mode vs. L-mode
- Temperatures/densities: Vary across operational space

### Design vs. Achieved

- **ITER**: Design values for baseline scenario (not yet operational)
- **JT-60SA**: Mix of design targets and early operation results
- **MAST-U**: Recently upgraded, some design values
- **Operational devices**: Typical achieved values

### Historical Records

- **JET**: Fusion power (16.1 MW) and Q (0.67) from 1997 DT campaign
- **C-Mod**: Noted for record high field (7.9 T) and density (>10²¹ m⁻³)

## Available Machines

| Machine | Status | Location | Type | R₀ (m) | a (m) | B_T (T) | I_p (MA) |
|---------|--------|----------|------|--------|-------|---------|----------|
| ITER | under_construction | Cadarache, France | Conventional | 6.2 | 2.0 | 5.3 | 15 |
| JET | decommissioned | Culham, UK | Conventional | 2.96 | 1.25 | 3.45 | 4.8 |
| JT-60SA | operational | Naka, Japan | Conventional | 2.96 | 1.18 | 2.25 | 5.5 |
| DIII-D | operational | San Diego, USA | Conventional | 1.67 | 0.67 | 2.2 | 2.0 |
| ASDEX-Upgrade | operational | Garching, Germany | Conventional | 1.65 | 0.5 | 3.1 | 1.4 |
| EAST | operational | Hefei, China | Conventional | 1.85 | 0.45 | 3.5 | 1.0 |
| KSTAR | operational | Daejeon, South Korea | Conventional | 1.8 | 0.5 | 3.5 | 2.0 |
| WEST | operational | Cadarache, France | Conventional | 2.5 | 0.5 | 3.7 | 1.0 |
| TCV | operational | Lausanne, Switzerland | Conventional | 0.88 | 0.25 | 1.43 | 1.0 |
| C-Mod | decommissioned | Cambridge, USA | Compact | 0.67 | 0.22 | 7.9 | 1.7 |
| MAST-U | operational | Culham, UK | Spherical | 0.85 | 0.65 | 0.95 | 1.9 |

## Technical Implementation

### File Structure

```
imas_standard_names/
├── resources/
│   └── tokamak_parameters/
│       ├── schema.yml          # Validation schema
│       ├── iter.yml            # Individual machine files
│       ├── jet.yml
│       ├── ...
│       └── README.md           # Source documentation
├── tokamak_parameters.py       # Pydantic models and loader
└── tools/
    └── tokamak_parameters.py   # MCP tool implementation
```

### Pydantic Models

- **ParameterValue**: Single parameter with value, unit, symbol, metadata
- **ParameterStatistics**: Statistical summary across machines
- **GeometryParameters**: Geometric parameter group
- **PhysicsParameters**: Physics parameter group
- **TokamakParameters**: Complete machine parameter set
- **TokamakParametersDB**: Database loader with caching

### Database Features

- **Caching**: Parameters cached in memory after first load
- **Case-insensitive**: Machine names normalized (lowercase, hyphens)
- **Validation**: Pydantic models ensure schema compliance
- **Statistics**: Automatic computation of min/max/mean/median
- **Error handling**: Clear error messages with available machines

## See Also

- Grammar specification: `grammar/specification.yml`
- Standard names catalog: `resources/standard_names/`
- MCP tool registration: `tools/__init__.py`

