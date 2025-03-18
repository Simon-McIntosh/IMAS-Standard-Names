import click

from imas_standard_names.standard_name import (
    GenericNames,
    StandardInput,
    StandardNameFile,
)


def format_error(error):
    """Return formatted error message."""
    return f"{type(error).__name__}: {error}"


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
        standardnames.update(standard_name, overwrite)

    except (NameError, KeyError, Exception) as error:
        click.echo(format_error(error))
    else:
        click.echo(
            f"The proposed Standard Name is valid.\n"
            f"\n{standard_name.as_document().as_yaml()}\n"
            f"This proposal is ready for submission to "
            "the Standard Names repository."
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
