from io import StringIO

import click
import json
from strictyaml.ruamel import YAML

from imas_standard_names.standard_name import (
    GenericNames,
    StandardInput,
    StandardNameFile,
)

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.preserve_quotes = True
yaml.width = 80  # Line width


def format_error(error, submission_file=None):
    """Return formatted error message."""
    error_message = f"**{type(error).__name__}**: {error}"
    if submission_file:
        with open(submission_file, "r") as f:
            submission = json.load(f)
        yaml_str = StringIO()
        yaml.dump(submission, yaml_str)
        error_message = (
            ":boom: The proposed Standard Name is not valid.\n"
            f"\n{error_message}\n"
            "\n:pencil: Please correct the error by editing the Issue Body at the top of the page.\n"
            f"\n{yaml_str.getvalue()}\n"
        )
    return error_message


@click.command()
@click.argument("standardnames_file")
@click.argument("genericnames_file")
@click.argument("submission_file")
@click.option("--unit-format", default="~F", help="Pint unit string formatter")
@click.option("--issue-link", default="")
@click.option(
    "--overwrite", default=False, is_flag=True, help="Overwrite existing entry"
)
def update_standardnames(
    standardnames_file: str,
    genericnames_file: str,
    submission_file: str,
    unit_format: str,
    issue_link: str,
    overwrite: bool,
):
    """Add a standard name to the project's standard name file."""
    standardnames = StandardNameFile(standardnames_file, unit_format=unit_format)
    genericnames = GenericNames(genericnames_file)
    try:
        standard_name = StandardInput(
            submission_file, unit_format=unit_format, issue_link=issue_link
        ).standard_name
        genericnames.check(standard_name.name)
        standardnames.update(standard_name, overwrite=overwrite)

    except (NameError, KeyError, Exception) as error:
        click.echo(format_error(error, submission_file))
    else:
        click.echo(
            ":sparkles: This proposal is ready for submission to "
            "the Standard Names repository.\n"
            f"\n{standardnames[standard_name.name].as_yaml()}\n"
            ":label: Label issue with `approve` to commit."
        )


@click.command()
@click.argument("standardnames_file")
@click.argument("standard_name", nargs=-1)  # handle whitespace in standard name
def has_standardname(standardnames_file: str, standard_name: str):
    """Check if a standard name exists in the project's standard name file."""
    standardnames = StandardNameFile(standardnames_file)
    standard_name = " ".join(standard_name)
    click.echo(f"{standard_name in standardnames.data}")


@click.command()
@click.argument("genericnames_file")
@click.argument("standard_name", nargs=-1)
def is_genericname(genericnames_file: str, standard_name: str):
    """Check if a standard name is already present in the generic names file."""
    standard_name = " ".join(standard_name)
    click.echo(f"{standard_name in GenericNames(genericnames_file)}")


@click.command()
@click.argument("standardnames_file")
@click.argument("standard_name", nargs=-1)
@click.option("--unit-format", default="~F", help="Pint unit string formatter")
def get_standardname(standardnames_file: str, standard_name: str, unit_format: str):
    """Return the standard name entry from the project's standard name file."""
    standardnames = StandardNameFile(standardnames_file, unit_format=unit_format)
    standard_name = " ".join(standard_name)
    try:
        submission = standardnames[standard_name].as_document()[standard_name].as_yaml()
    except (KeyError, Exception) as error:
        click.echo(format_error(error))
    else:
        click.echo(submission)
