# Tokamak Parameters Database

## Overview

This directory contains curated YAML files with authoritative parameters for major tokamak fusion devices worldwide. Each file provides comprehensive geometry and physics parameters with their sources.

## Data Sources and Update Workflow

### Primary Sources

1. **FusionWiki (CIEMAT)**: https://fusionwiki.ciemat.es
   - Comprehensive database of fusion devices
   - Community-maintained, regularly updated
   - Primary source for geometric and operational parameters

2. **Official Facility Websites**
   - ITER Organization: https://www.iter.org
   - EUROfusion: https://www.euro-fusion.org
   - General Atomics (DIII-D): https://www.ga.com
   - IPP (ASDEX-Upgrade): https://www.ipp.mpg.de
   - And others listed in individual YAML files

3. **Nuclear Fusion Journal**
   - Review papers and technical reports
   - Used for verification and detailed parameters

### Update Workflow

1. **Regular Reviews**: Parameters should be reviewed annually
2. **Source Verification**: Always cite authoritative sources with URLs
3. **Date Tracking**: Update `last_updated` and `accessed` fields
4. **Validation**: Use Pydantic models to ensure schema compliance

### Adding New Tokamaks

To add a new tokamak to the database:

1. Create a new YAML file following the schema in `schema.yml`
2. Use lowercase with hyphens for filenames (e.g., `new-tokamak.yml`)
3. Gather data from authoritative sources (prioritize FusionWiki and official sites)
4. Include all required fields (see schema.yml)
5. Cite sources with URLs and access dates
6. Validate using `TokamakParametersDB.get()` method

### Schema Requirements

See `schema.yml` for complete field definitions. Key requirements:

- **Required fields**: machine, facility, location, operational_status, last_updated, sources, geometry, physics
- **Geometry required**: major_radius, minor_radius, plasma_volume
- **Physics required**: toroidal_magnetic_field, plasma_current
- **Units**: Always specify units explicitly
- **Symbols**: Use standard fusion physics notation

## Current Machines

| Machine | Status | Location | R₀ (m) | a (m) |
|---------|--------|----------|---------|-------|
| ITER | under_construction | Cadarache, France | 6.2 | 2.0 |
| JET | decommissioned | Culham, UK | 2.96 | 1.25 |
| DIII-D | operational | San Diego, USA | 1.67 | 0.67 |
| ASDEX-Upgrade | operational | Garching, Germany | 1.65 | 0.5 |
| EAST | operational | Hefei, China | 1.85 | 0.45 |
| KSTAR | operational | Daejeon, South Korea | 1.8 | 0.5 |
| JT-60SA | operational | Naka, Japan | 2.96 | 1.18 |
| C-Mod | decommissioned | Cambridge, USA | 0.67 | 0.22 |
| TCV | operational | Lausanne, Switzerland | 0.88 | 0.25 |
| WEST | operational | Cadarache, France | 2.5 | 0.5 |
| MAST-U | operational | Culham, UK | 0.85 | 0.65 |

## Usage in Standard Names Documentation

Use the MCP tool `get_tokamak_parameters` to retrieve verified parameters for standard name documentation:

- Single machine: `get_tokamak_parameters(machines='ITER')`
- Multiple machines: `get_tokamak_parameters(machines='ITER JET DIII-D')`
- All machines with statistics: `get_tokamak_parameters(machines='all')`

Always cite specific machines in "Typical values" sections of standard name entries.

## Notes on Parameter Values

- **Typical vs Maximum**: Most values represent typical high-performance operation, not absolute maximums
- **Scenario Dependence**: Some parameters (e.g., fusion power, Q) depend on specific operational scenarios
- **Design vs Achieved**: For newer machines (JT-60SA, MAST-U), some values are design targets
- **Historical Records**: JET fusion power and Q values are from the 1997 DT campaign record

## Data Quality and Verification

All parameters have been verified against multiple sources where possible. Discrepancies between sources are noted in the `note` fields. For critical applications, always consult the original sources listed in each file.

