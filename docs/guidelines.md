# Guidelines for Construction of IMAS Standard Names

## Characters

Standard names consist of lower-case letters, digits and underscores, and begin with
a letter. Do not use upper case.

## Spelling

Authors should use US spelling, e.g. analyze, center.

## Qualifications

Qualify standard names by adding phrases in certain standard
forms and order. These qualifications do not change the units of the quantity.

[[component](#component)] standard_name [at [position](#position)] [due to
[process](#process)]

### Component

Use one of the words `radial`, `vertical`, `toroidal` or `poloidal` to specify the direction of the spatial component of a vector in the cylindrical or
toroidal/poloidal coordinate system.

Use the words `parallel` or `diamagnetic` to specify the direction of a vector relative to the local magnetic field.

#### Examples of Component Usage

- `radial_electric_field`: Represents the electric field in the radial direction.
- `toroidal_magnetic_field`: Represents the magnetic field in the toroidal direction.
- `parallel_heat_flux`: Represents the heat flux parallel to the local magnetic field.
- `diamagnetic_current_density`: Represents the current density in the diamagnetic direction.

### Position

Use a phrase `at_<position>` to specify the value of a quantity at a
predefined position. Some examples are `at_boundary`, `at_magnetic_axis` and
`at_current_center`.

#### Examples of Position Usage

- `temperature_at_boundary`: Represents the temperature at the boundary of the system.
- `pressure_at_magnetic_axis`: Represents the pressure at the magnetic axis.
- `density_at_current_center`: Represents the density at the current center.

### Process

When you specify a physical process with the phrase `due_to_<process>`, the quantity represents a single term in a sum of terms which together
compose the general quantity that you name by omitting the phrase. Some examples are
`due_to_conduction`, `due_to_convection`.

#### Examples of Process Usage

- `heat_flux_due_to_conduction`: Represents the heat flux caused by conduction.
- `momentum_transfer_due_to_convection`: Represents the momentum transfer caused by convection.
- `energy_loss_due_to_radiation`: Represents the energy loss caused by radiation.
- `particle_flux_due_to_diffusion`: Represents the particle flux caused by diffusion.
- `current_density_due_to_induction`: Represents the current density caused by induction.

## Transformations

Use transformations to derive standard names from other standard names (represented here by X,
Y and Z) by following these rules. You can apply successive transformations.
Transformations can alter the units as shown.

{{ read_csv('transformations.csv') }}

### Examples of Transformations

- `gradient_of_temperature`: Represents the spatial gradient of temperature.
- `time_derivative_of_pressure`: Represents the time derivative of pressure.
- `integral_of_density_over_volume`: Represents the integral of density over a specified volume.
- `average_of_velocity_over_time`: Represents the time-averaged velocity.
- `logarithm_of_electron_density`: Represents the natural logarithm of electron density.
- `square_of_magnetic_field`: Represents the square of the magnetic field.
- `normalized_temperature`: Represents the temperature normalized by a reference value.
- `difference_between_ion_density_and_electron_density`: Represents the difference between ion density and electron density.
- `ratio_of_thermal_pressure_to_magnetic_pressure`: Represents the ratio of thermal pressure to magnetic pressure (commonly referred to as beta).
- `derivative_of_current_density_with_respect_to_radius`: Represents the radial derivative of current density.

## Generic names

The following names have consistent meanings and units as elements in
other standard names, although they themselves are too general to serve as
standard names. We record them here for reference. _These are not
standard names_.

{{ read_csv('generic_names.csv') }}

[^1]:
    Express temperature of plasma species (e.g. `electron_temperature`) in
    `eV`, and other temperatures (e.g. `wall_temperature`) in `K`.
