from pathlib import Path
from imas_standard_names.schema import (
    load_standard_name_file,
    save_standard_name,
    create_standard_name,
)


def test_save_and_load_roundtrip(tmp_path, scalar_data):
    entry = create_standard_name(scalar_data)
    path = save_standard_name(entry, tmp_path)
    loaded = load_standard_name_file(path)
    assert loaded == entry


def test_catalog_duplicate_detection(tmp_path, scalar_data):
    entry = create_standard_name(scalar_data)
    save_standard_name(entry, tmp_path)
    # Write duplicate file intentionally
    dup_path = tmp_path / f"{entry.name}.yaml"
    dup_path.write_text(Path(tmp_path / f"{entry.name}.yml").read_text())
    from imas_standard_names.schema import load_catalog

    try:
        load_catalog(tmp_path)
    except ValueError as e:
        assert "Duplicate standard name" in str(e)
    else:  # pragma: no cover - safety
        assert False, "Expected duplicate detection"
