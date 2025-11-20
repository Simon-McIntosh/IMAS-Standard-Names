"""Schema command for Standard Names models.

Provides a `schema` Click command to print the JSON/YAML schema for the
`StandardName` model. Useful for LLM tools and schema-driven integrations.
"""

from __future__ import annotations

import json

import click
import yaml

from imas_standard_names.grammar.model import StandardName


@click.command("schema")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Output format for the schema",
)
@click.option(
    "--pretty/--no-pretty",
    default=True,
    show_default=True,
    help="Pretty-print JSON output",
)
def schema_cmd(fmt: str, pretty: bool) -> None:
    """Print the `StandardName` model schema in JSON or YAML."""
    schema = StandardName.model_json_schema()

    if fmt.lower() == "yaml":
        click.echo(
            yaml.safe_dump(
                schema, sort_keys=False, allow_unicode=True, default_flow_style=False
            )
        )
        return

    indent = 2 if pretty else None
    click.echo(json.dumps(schema, indent=indent))


__all__ = ["schema_cmd"]
