# IMAS Metadata Conventions

## Overview

Standard names identify **what** is being measured or calculated—the physical or geometric quantity itself. Information about **how** the quantity was obtained (measurement method), **where** it came from (device/diagnostic), or **how** it was processed belongs in **metadata fields defined by IMAS fusion conventions**, not in the standard name.

This document describes metadata usage patterns for IMAS data, complementing the standard names catalog.

## Core Principle

> **Standard names are persistent identifiers for physical and geometric quantities, independent of measurement method, device, or processing.**

Following CF metadata convention principles, this separation enables:

- **Data comparison** across different facilities and diagnostics
- **Method independence** - same quantity measured different ways has the same name
- **Long-term stability** - names don't change when diagnostics are upgraded
- **Clear semantics** - name describes the quantity, metadata describes the context

## Device Signals vs Physics Quantities

### When Device Goes IN the Name

Use `<device>_<signal>` pattern when the quantity **is a property or signal OF the device itself**:

**Device signals (quantity IS device property):**

- `flux_loop_voltage` — induced voltage in the flux loop conductor (device signal)
- `passive_loop_current` — eddy current flowing in the passive conductor (device signal)
- `poloidal_magnetic_field_probe_voltage` — voltage output from the probe (device signal)
- `interferometer_beam_phase` — phase of the interferometer beam (device signal)
- `soft_xray_detector_etendue` — geometric property of the detector aperture (device property)

The device is not just measuring something external—it IS the physical system being described. These use the `<device>_<signal>` grammar pattern where device and signal are concatenated directly.

### When Device Goes IN Metadata

Use generic standard name when the quantity **is a physics property measured BY the device**:

**Physics quantities (documented in metadata):**

- `electron_density` - plasma property (metadata: `measurement_method`, `device_id`)
- `poloidal_magnetic_flux` - field quantity (metadata: `measurement_method`, `device_id`)
- `plasma_current` - global quantity (metadata: `measurement_method`)
- `magnetic_field` - field measurement (metadata: `device_id` for probe location)

The device observes or measures this quantity, but the quantity has physical meaning independent of the device.

## Metadata Fields

### Measurement Method

**Field**: `measurement_method`  
**Purpose**: Diagnostic technique or physical principle used to obtain the quantity  
**Examples**:

- `interferometry` - for electron density measurements
- `thomson_scattering` - for electron temperature measurements
- `langmuir_probe` - for edge plasma measurements
- `spectroscopy` - for impurity measurements
- `magnetic_flux_loop` - for magnetic field measurements
- `bolometry` - for radiated power measurements

**When to use**: When the acquisition method is scientifically relevant or affects data interpretation.

### Reconstruction Method

**Field**: `reconstruction_method`  
**Purpose**: Analysis or inversion technique applied to derive the quantity  
**Examples**:

- `equilibrium_reconstruction` - for magnetic equilibrium quantities
- `tomographic_inversion` - for 2D emission profiles
- `profile_fitting` - for fitted parameter profiles
- `kinetic_reconstruction` - for kinetic profiles from multiple diagnostics

**When to use**: When the quantity is derived through complex analysis rather than direct measurement.

### Device/Diagnostic Identifier

**Field**: `device_id` or `diagnostic_id`  
**Purpose**: Specific instrument or diagnostic system identifier  
**Examples**:

- `flux_loop_array_A` - specific flux loop array
- `thomson_scattering_core` - core Thomson scattering system
- `interferometer_line_3` - specific interferometer chord
- `langmuir_probe_divertor_12` - specific probe location

**When to use**: When tracking which specific instrument provided the data is important for calibration, validation, or cross-checking.

### Data Processing

**Field**: `data_processing`  
**Purpose**: Post-processing steps applied to the data  
**Examples**:

- `low_pass_filtered` - temporal filtering applied
- `baseline_subtracted` - background subtraction
- `calibrated` - calibration applied
- `smoothed` - spatial or temporal smoothing
- `despiked` - outlier removal

**When to use**: When processing steps significantly affect data characteristics or interpretation.

### Coordinate System / Conventions

**Field**: `coordinate_system` or `conventions`  
**Purpose**: Reference frame, sign conventions, or coordinate system details  
**Examples**:

- `COCOS=3` - COordinate COnventions for magnetic field/flux signs
- `right_handed_cylindrical` - coordinate system handedness
- `straight_field_line_coordinates` - flux coordinate system type
- `machine_coordinates` - vs. flux coordinates

**When to use**: When coordinate conventions affect numerical values or interpretations.

### Uncertainty / Quality

**Field**: `uncertainty`, `quality_flag`  
**Purpose**: Measurement uncertainty, error bars, or quality indicators  
**Examples**:

- `uncertainty: 0.05` - fractional uncertainty
- `quality_flag: validated` - data quality status
- `confidence_level: 0.95` - statistical confidence

**When to use**: Essential for all quantitative measurements.

## Examples: Standard Name + Metadata

### Example 1: Electron Density

**Standard Name**: `electron_density`  
**Metadata**:

```yaml
measurement_method: interferometry
device_id: interferometer_line_2
uncertainty: 5e17 # m^-3
data_processing: phase_unwrapped
```

**Why not**: ~~`electron_density_from_interferometry`~~ ❌  
The measurement method is metadata, not part of the quantity identity.

### Example 2: Electron Temperature

**Standard Name**: `electron_temperature`  
**Metadata**:

```yaml
measurement_method: thomson_scattering
device_id: thomson_core
uncertainty: 0.1 # keV
spatial_resolution: 0.02 # m
```

**Why not**: ~~`measured_electron_temperature`~~ ❌  
All quantities are either measured or calculated; "measured" is redundant.

### Example 3: Magnetic Field

**Standard Name**: `toroidal_component_of_magnetic_field`  
**Metadata**:

```yaml
measurement_method: magnetic_field_probe
device_id: bpol_probe_array_midplane
coordinate_system: COCOS=3
uncertainty: 0.01 # T
```

**Why not**: ~~`toroidal_magnetic_field_from_probe`~~ ❌  
The device/source is metadata, not part of the quantity identity.

### Example 4: Flux Loop Voltage (Device Signal)

**Standard Name**: `flux_loop_voltage`  
**Metadata**:

```yaml
device_id: flux_loop_12
measurement_method: inductive_pickup
related_quantity: time_derivative_of_poloidal_magnetic_flux
sampling_rate: 1e6 # Hz
```

**Why this pattern**: The voltage is a property OF the flux loop device itself (induced by changing magnetic flux), not an independent physics quantity being measured by the device. This uses the `<device>_<signal>` pattern.

### Example 5: Plasma Current

**Standard Name**: `plasma_current`  
**Metadata**:

```yaml
reconstruction_method: equilibrium_reconstruction
input_diagnostics: [magnetic_flux_loops, magnetic_field_probes]
code: EFIT
uncertainty: 0.05 # MA
```

**Standard Name** (alternative): `plasma_current`  
**Metadata**:

```yaml
measurement_method: rogowski_coil
device_id: rogowski_vessel_primary
uncertainty: 0.02 # MA
```

**Note**: Same standard name, different metadata for different measurement approaches.

## Anti-Patterns to Avoid

### ❌ Don't: Encode Method in Name

```yaml
# WRONG
name: electron_density_from_interferometry
name: electron_temperature_from_thomson_scattering
name: reconstructed_plasma_current

# CORRECT
name: electron_density
metadata:
  measurement_method: interferometry

name: electron_temperature
metadata:
  measurement_method: thomson_scattering

name: plasma_current
metadata:
  reconstruction_method: equilibrium_reconstruction
```

### ❌ Don't: Use Generic Names for Device Signals

When a quantity IS a device signal (not a physics quantity measured by the device), use the device signal pattern:

```yaml
# WRONG - using generic name for device signal
name: voltage
metadata:
  device_id: flux_loop_12

# CORRECT - device signal pattern
name: flux_loop_voltage
description: Voltage measured by flux loop diagnostic.

# WRONG - encoding device in physics quantity name
name: magnetic_field_from_probe

# CORRECT - physics quantity with device in metadata  
name: magnetic_field
metadata:
  device_id: magnetic_probe_array_A

# CORRECT - physics quantity with device in metadata
name: ion_saturation_current_density
metadata:
  device_id: langmuir_probe_divertor_12
```

### ❌ Don't: Encode Processing in Name

```yaml
# WRONG
name: filtered_electron_temperature
name: smoothed_density_profile
name: calibrated_voltage

# CORRECT
name: electron_temperature
metadata:
  data_processing: low_pass_filtered

name: electron_density
metadata:
  data_processing: smoothed

name: voltage
metadata:
  data_processing: calibrated
```

## Decision Tree: Name vs. Metadata

When adding information to describe data, ask:

1. **Does this identify WHAT quantity is being described?**

   - YES → Part of standard name
   - NO → Continue to step 2

2. **Does this describe HOW the quantity was obtained?**

   - YES → Use `measurement_method` or `reconstruction_method` metadata
   - NO → Continue to step 3

3. **Does this identify WHERE/WHICH device obtained it?**

   - YES → Use `device_id` or `diagnostic_id` metadata
   - NO → Continue to step 4

4. **Does this describe processing or quality?**
   - YES → Use `data_processing` or `quality_flag` metadata
   - NO → Consider if information is necessary

## Relationship to IMAS Data Dictionary (DD)

The IMAS DD contains both:

- **Standard names** (persistent quantity identifiers)
- **Metadata fields** (context, provenance, quality)

Standard names should be used as the primary identifiers for quantities across the DD, with metadata fields providing the additional context needed for interpretation and validation.

## Benefits of This Approach

1. **Interoperability**: Same name for same quantity across facilities
2. **Flexibility**: Methods can change without name changes
3. **Clarity**: Clear distinction between quantity and acquisition
4. **Comparison**: Easy to compare different measurements of same quantity
5. **Longevity**: Names remain stable as technology evolves
6. **Simplicity**: Names are shorter and more focused

## Related Documentation

- [Standard Names Guidelines](guidelines.md)
- [Grammar Reference](grammar-reference.md)
- [CF Metadata Conventions](http://cfconventions.org/) (inspiration)
