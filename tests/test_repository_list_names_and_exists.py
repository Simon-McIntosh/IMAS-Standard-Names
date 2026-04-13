from pathlib import Path

from imas_standard_names.repository import StandardNameCatalog


def test_list_names_and_exists(tmp_path: Path, example_scalars, write_yaml):
    # Use examples from catalog
    for example in example_scalars[:3]:
        write_yaml(tmp_path, example)

    repo = StandardNameCatalog(tmp_path)

    # exists() checks
    assert repo.exists(example_scalars[0].name) is True
    assert repo.exists(example_scalars[1].name) is True
    assert repo.exists("does_not_exist") is False

    # list_names should return sorted list of names (alphabetical)
    names = repo.list_names()
    assert names == sorted(names)
    expected_names = {ex.name for ex in example_scalars[:3]}
    assert set(names) >= expected_names

    # list() still returns hydrated models matching names
    hydrated = repo.list()
    hydrated_names = {m.name for m in hydrated}
    assert expected_names.issubset(hydrated_names)
