"""Unit handling for IMAS MCP Server.

Canonical unit formatting lives in :func:`imas_standard_names.canonical_unit`
(pint parse + sorted ASCII short symbols). This module only owns the pint
registry seeded with the Data-Dictionary non-SI unit aliases.
"""

import importlib.resources

import pint

# Initialize unit registry
unit_registry = pint.UnitRegistry()

# Load non-SI Data Dictionary unit aliases
with importlib.resources.as_file(
    importlib.resources.files("imas_standard_names.units").joinpath(
        "data_dictionary_unit_aliases.txt"
    )
) as resource_path:
    unit_registry.load_definitions(str(resource_path))
