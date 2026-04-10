import importlib.resources as ir
import json
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

import pytest
from click.testing import CliRunner

from imas_standard_names import models
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.unit_of_work import UnitOfWork


# Shared baseline data ---------------------------------------------------------
@pytest.fixture(scope="session")
def base_names_data():
    """Load example scalars from catalog."""
    files_obj = ir.files("imas_standard_names") / "resources" / "standard_name_examples"
    with ir.as_file(files_obj) as examples_path:
        catalog = StandardNameCatalog(root=examples_path, permissive=True)
        scalars = catalog.list(kind="scalar")[:3]
        return [entry.model_dump() for entry in scalars]


@pytest.fixture
def github_input():
    """GitHub issue form submission data with all required fields."""
    return {
        "name": "test_new_quantity",
        "units": "eV",
        "documentation": "Test quantity for validation.\n\nThis is a multi-line documentation string for testing purposes.",
        "physics_domain": "core_plasma_physics",
        "options": [],
    }


# Helper context managers / fixtures -------------------------------------------
@contextmanager
def click_runner(path: str | Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=path) as temp_dir:
        yield runner, temp_dir


def _write_entry(entry: dict, directory: Path):
    repo = StandardNameCatalog(directory)
    uow = UnitOfWork(repo)
    obj = models.create_standard_name_entry(entry)
    uow.add(obj)
    uow.commit()


@contextmanager
def write_standardnames_dir(entries: Iterable[dict], temp_dir):
    directory = Path(temp_dir) / "standard_names"
    directory.mkdir(parents=True, exist_ok=True)
    for e in entries:
        _write_entry(e, directory)
    yield directory.as_posix()


@contextmanager
def write_submission(github_input: dict[str, str], temp_dir):
    submission_file = Path(temp_dir) / "submission.json"
    with open(submission_file, "w") as f:
        f.write(json.dumps(github_input))
    yield submission_file.as_posix()


@pytest.fixture
def cli_env(tmp_path, base_names_data, github_input):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames_dir(base_names_data, temp_dir) as standardnames_dir,
        write_submission(github_input, temp_dir) as submission_file,
    ):
        yield runner, (standardnames_dir, submission_file)


@pytest.fixture
def standardnames_dir_only(tmp_path, base_names_data):
    with (
        click_runner(tmp_path) as (runner, temp_dir),
        write_standardnames_dir(base_names_data, temp_dir) as standardnames_dir,
    ):
        yield runner, standardnames_dir


@pytest.fixture
def extended_names_data(base_names_data):
    return base_names_data + [
        {
            "name": "a_new_standard_name",
            "kind": "scalar",
            "status": "draft",
            "unit": "1",
            "description": "desc",
        }
    ]
