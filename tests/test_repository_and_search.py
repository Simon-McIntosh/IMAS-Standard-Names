from pathlib import Path

from imas_standard_names.models import create_standard_name_entry
from imas_standard_names.repository import StandardNameCatalog


def test_repository_load_and_search(tmp_path: Path, example_scalars, write_yaml):
    # Use examples from catalog instead of hardcoded data
    for entry in example_scalars[:2]:
        write_yaml(tmp_path, entry)

    repo = StandardNameCatalog(tmp_path)
    # Use first example name for assertions
    first_name = example_scalars[0].name
    assert repo.get(first_name) is not None
    # Search using part of the name
    search_term = first_name.split("_")[0]
    results = repo.search(search_term)
    assert first_name in results
