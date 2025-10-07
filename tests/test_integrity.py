import time
from pathlib import Path

from imas_standard_names.database.build import build_catalog
from imas_standard_names.database.integrity import verify_integrity


def _seed(root: Path):
    (root / "x.yml").write_text(
        "name: x\nkind: scalar\nstatus: active\nunit: keV\ndescription: X desc.\n"
    )
    (root / "y.yml").write_text(
        "name: y\nkind: scalar\nstatus: draft\nunit: keV\ndescription: Y desc.\n"
    )


def test_integrity_clean(tmp_path: Path):
    _seed(tmp_path)
    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    issues = verify_integrity(tmp_path, db, full=False)
    assert issues == []
    full_issues = verify_integrity(tmp_path, db, full=True)
    assert full_issues == []


def test_integrity_modified_file(tmp_path: Path):
    _seed(tmp_path)
    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    # Modify y.yml
    time.sleep(0.02)  # ensure mtime changes on fast FS
    (tmp_path / "y.yml").write_text(
        "name: y\nkind: scalar\nstatus: draft\nunit: keV\ndescription: Y desc changed.\n"
    )
    issues = verify_integrity(tmp_path, db, full=False)
    codes = {i["code"] for i in issues}
    assert "mismatch-meta" in codes or "hash-mismatch" in codes
    full_issues = verify_integrity(tmp_path, db, full=True)
    full_codes = {i["code"] for i in full_issues}
    assert "hash-mismatch" in full_codes


def test_integrity_added_file(tmp_path: Path):
    _seed(tmp_path)
    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    # Add new file after build
    (tmp_path / "z.yml").write_text(
        "name: z\nkind: scalar\nstatus: active\nunit: keV\ndescription: Z desc.\n"
    )
    issues = verify_integrity(tmp_path, db, full=False)
    # For added file we expect missing-in-db for its stem
    assert any(i["code"] == "missing-in-db" and i.get("name") == "z" for i in issues)


def test_integrity_deleted_file(tmp_path: Path):
    _seed(tmp_path)
    db = build_catalog(tmp_path, tmp_path / "artifacts" / "catalog.db")
    # Delete x.yml
    (tmp_path / "x.yml").unlink()
    issues = verify_integrity(tmp_path, db, full=False)
    assert any(i["code"] == "missing-on-disk" and i.get("name") == "x" for i in issues)
