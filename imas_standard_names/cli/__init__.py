"""CLI command group for IMAS Standard Names.

This module exposes the root Click command group `standard_names` which
aggregates subcommands implemented in sibling modules (e.g. `build`, `search`).

Example usage:

        standard-names build path/to/yaml
        standard-names search electron_temperature
"""

from __future__ import annotations

import click

from .build import build_cmd
from .search import search_cmd


@click.group()
def standard_names():  # pragma: no cover - thin group wrapper
    """Standard Names management commands."""


# Register subcommands
standard_names.add_command(build_cmd)
standard_names.add_command(search_cmd)

__all__ = ["standard_names"]
