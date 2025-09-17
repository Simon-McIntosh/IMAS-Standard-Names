import json
from pathlib import Path
from click.testing import CliRunner

from imas_standard_names.cli.diff_catalog import diff_standardnames
from imas_standard_names import schema
from imas_standard_names.repositories import YamlStandardNameRepository
from imas_standard_names.unit_of_work import UnitOfWork


def _write(repo_dir: Path, entries):
    repo = YamlStandardNameRepository(repo_dir)
    for data in entries:
        uow = UnitOfWork(repo)
        uow.add(schema.create_standard_name(data))
        uow.commit()


def test_diff_added_removed_changed(tmp_path):
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()

    base = [
        {
            "name": "a",
            "kind": "scalar",
            "status": "draft",
            "unit": "",
            "description": "A",
        },
        {
            "name": "b",
            "kind": "scalar",
            "status": "draft",
            "unit": "",
            "description": "B",
        },
    ]
    updated = [
        {
            "name": "a",
            "kind": "scalar",
            "status": "draft",
            "unit": "",
            "description": "A (updated)",
        },
        {
            "name": "c",
            "kind": "scalar",
            "status": "draft",
            "unit": "",
            "description": "C",
        },
    ]

    _write(old_dir, base)
    _write(new_dir, updated)

    out_json = tmp_path / "diff.json"
    runner = CliRunner()
    result = runner.invoke(
        diff_standardnames,
        (old_dir.as_posix(), new_dir.as_posix(), out_json.as_posix()),
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out_json.read_text())
    assert data["added"] == ["c"]
    assert data["removed"] == ["b"]
    assert data["changed"] == ["a"]


def test_diff_export_dir(tmp_path):
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()

    _write(
        old_dir,
        [
            {
                "name": "x",
                "kind": "scalar",
                "status": "draft",
                "unit": "",
                "description": "X",
            },
        ],
    )
    _write(
        new_dir,
        [
            {
                "name": "x",
                "kind": "scalar",
                "status": "draft",
                "unit": "",
                "description": "X changed",
            },
            {
                "name": "y",
                "kind": "scalar",
                "status": "draft",
                "unit": "",
                "description": "Y",
            },
        ],
    )

    out_json = tmp_path / "diff.json"
    export_dir = tmp_path / "export"
    runner = CliRunner()
    result = runner.invoke(
        diff_standardnames,
        (
            old_dir.as_posix(),
            new_dir.as_posix(),
            out_json.as_posix(),
            "--export-dir",
            export_dir.as_posix(),
        ),
    )
    assert result.exit_code == 0, result.output
    # Should contain x and y (changed + added)
    exported = {p.stem for p in export_dir.glob("*.yml")}
    assert exported == {"x", "y"}
