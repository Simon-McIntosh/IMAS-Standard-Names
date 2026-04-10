"""Generate a versioned JSON schema for StandardNameEntry."""

import json
from pathlib import Path

import click
from pydantic import TypeAdapter

import imas_standard_names
from imas_standard_names.models import StandardNameEntry

_ENTRY_ADAPTER = TypeAdapter(StandardNameEntry)

_SCHEMA_PATH = Path(__file__).resolve().parent / "entry_schema.json"


def generate_entry_schema() -> dict:
    """Export the Pydantic JSON schema for ``StandardNameEntry``.

    The returned dictionary is a standard JSON Schema object augmented with
    a ``$schema_version`` field tied to the installed package version.

    Returns:
        A JSON-serializable dictionary containing the full JSON schema
        for the ``StandardNameEntry`` discriminated union.
    """
    schema = _ENTRY_ADAPTER.json_schema()
    schema["$schema_version"] = imas_standard_names.__version__
    return schema


def write_entry_schema(path: Path | None = None) -> Path:
    """Write the JSON schema to disk.

    Args:
        path: Destination file path.  Defaults to the package-internal
            ``entry_schema.json`` alongside this module.

    Returns:
        The resolved path of the written file.
    """
    target = path or _SCHEMA_PATH
    schema = generate_entry_schema()
    target.write_text(json.dumps(schema, indent=2) + "\n")
    return target


@click.command("generate-schema")
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Output file path (default: package-internal entry_schema.json).",
)
def main(output: str | None = None) -> None:
    """Generate the StandardNameEntry JSON schema."""
    target = Path(output) if output else None
    written = write_entry_schema(target)
    click.echo(f"Schema written to {written}")
