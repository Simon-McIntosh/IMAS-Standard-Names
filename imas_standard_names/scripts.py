from io import StringIO

import click
import json
from pathlib import Path
from strictyaml.ruamel import YAML

from imas_standard_names.image_processor import ImageProcessor
from imas_standard_names.repository import update_static_urls
from imas_standard_names.standard_name import (
    GenericNames,
    StandardInput,
    StandardName,
    StandardNameFile,
)

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.preserve_quotes = True
yaml.width = 80  # Line width


def format_error(error, submission_file=None):
    """Return formatted error message."""
    error_message = (
        ":boom: The proposed Standard Name is not valid.\n"
        f"\n{type(error).__name__}: {error}\n"
    )
    if submission_file:
        with open(submission_file, "r") as f:
            submission = json.load(f)
        yaml_str = StringIO()
        yaml.dump(submission, yaml_str)
        # error_message += f"\nHere is a copy of the submission for reference:\n\n{yaml_str.getvalue()}\n"
    error_message += (
        "\n"
        "> [!NOTE]\n"
        "> Click the three dots (⋯) in the upper right corner of the issue and "
        'select "Edit" to make changes to your proposal. Any changes you make '
        "will automatically recheck the submission."
        "\n"
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
        # Process image URLs in documentation string
        image_processor = ImageProcessor(
            standard_name.name,
            standard_name.documentation,
            image_dir=Path("docs/img") / standard_name.name,
            parents=1,
        )
        image_processor.download_images(remove_existing=True)
        relative_standard_name = StandardName(
            **standard_name.as_dict()
            | {"documentation": image_processor.documentation_with_relative_paths()}
        )
        # Update standardnames.yml
        standardnames.update(relative_standard_name, overwrite=overwrite)

    except (NameError, KeyError, Exception) as error:
        click.echo(format_error(error, submission_file))
    else:
        click.echo(
            ":sparkles: This proposal is ready for submission to "
            "the Standard Names repository.\n"
            # f"\n{standard_name.as_html()}\n".replace("img/", "docs/img/")
        )


@click.command()
@click.argument("standardnames_file")
@click.argument("minuend_standardnames_file")
@click.argument("subtrahend_standardnames_file")
def subtract_standardnames(
    standardnames_file,
    minuend_standardnames_file: str,
    subtrahend_standardnames_file: str,
):
    """Subtract one standard names file from another."""
    minuend = StandardNameFile(minuend_standardnames_file)
    subtrahend = StandardNameFile(subtrahend_standardnames_file)
    result = minuend - subtrahend
    with open(standardnames_file, "w") as f:
        f.write(result.data.as_yaml())


@click.command()
@click.argument("standardnames_file")
@click.argument("standard_name", nargs=-1)  # handle whitespace in standard name
def has_standardname(standardnames_file: str, standard_name: str):
    """Check if a standard name exists in the project's standard name file."""
    path = Path(standardnames_file)
    if not path.exists() or path.stat().st_size == 0:
        click.echo("False")  # standardnames file does not exist or is empty
        return
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


@click.command()
@click.argument("remote")
@click.option("--filename", default="README.md", help="File to update")
def update_links(remote: str, filename: str):
    """Update the README.md file with the remote's URL."""
    update_static_urls(filename, remote=remote)
