import time
from pathlib import Path

from imas_standard_names.database.build import build_catalog
from imas_standard_names.database.integrity import verify_integrity


def test_integrity_clean(tmp_path: Path, example_scalars, write_yaml):
    # Use examples from catalog
    for example in example_scalars[:2]:
        write_yaml(tmp_path, example)

    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    issues = verify_integrity(tmp_path, db, full=False)
    assert issues == []
    full_issues = verify_integrity(tmp_path, db, full=True)
    assert full_issues == []


def test_integrity_modified_file(tmp_path: Path, example_scalars, write_yaml):
    # Use examples from catalog
    for example in example_scalars[:2]:
        write_yaml(tmp_path, example)

    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    time.sleep(0.02)  # ensure mtime changes on fast FS
    modified = example_scalars[1].model_copy(
        update={"description": "Modified description."}
    )
    write_yaml(tmp_path, modified)

    issues = verify_integrity(tmp_path, db, full=False)
    codes = {i["code"] for i in issues}
    assert "mismatch-meta" in codes or "hash-mismatch" in codes
    full_issues = verify_integrity(tmp_path, db, full=True)
    full_codes = {i["code"] for i in full_issues}
    assert "hash-mismatch" in full_codes


def test_integrity_added_file(tmp_path: Path, example_scalars, write_yaml):
    # Use examples from catalog
    for example in example_scalars[:2]:
        write_yaml(tmp_path, example)

    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    # Add third example after build
    write_yaml(tmp_path, example_scalars[2])
    third_name = example_scalars[2].name

    issues = verify_integrity(tmp_path, db, full=False)
    # For added file we expect missing-in-db for its stem
    assert any(
        i["code"] == "missing-in-db" and i.get("name") == third_name for i in issues
    )


def test_integrity_deleted_file(tmp_path: Path, example_scalars, write_yaml):
    # Use examples from catalog
    for example in example_scalars[:2]:
        write_yaml(tmp_path, example)

    first_name = example_scalars[0].name
    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    # Delete first example (write_yaml writes to a "general" subdirectory)
    (tmp_path / "general" / f"{first_name}.yml").unlink()
    issues = verify_integrity(tmp_path, db, full=False)
    assert any(
        i["code"] == "missing-on-disk" and i.get("name") == first_name for i in issues
    )
