from imas_standard_names.issues.cli import subtract_standardnames
from pathlib import Path
import json
from imas_standard_names import schema


def _write_entries(path: Path, entries):
    path.mkdir(parents=True, exist_ok=True)
    for e in entries:
        obj = schema.create_standard_name(e)
        schema.save_standard_name(obj, path)


def test_subtract_standardnames(tmp_path, base_names_data, extended_names_data):
    from click.testing import CliRunner

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        minuend_dir = Path(tmp_path / "minuend")
        subtrahend_dir = Path(tmp_path / "subtrahend")
        out_dir = Path(tmp_path / "result")
        _write_entries(minuend_dir, extended_names_data)
        _write_entries(subtrahend_dir, base_names_data)
        result = runner.invoke(
            subtract_standardnames,
            (out_dir.as_posix(), minuend_dir.as_posix(), subtrahend_dir.as_posix()),
        )
        assert result.exit_code == 0
        # Only the extra entry should remain
        index_file = out_dir / "index.json"
        assert index_file.exists()
        names = json.loads(index_file.read_text())
        assert names == ["a_new_standard_name"]
        # Ensure corresponding YAML exists
        assert (out_dir / "a_new_standard_name.yml").exists()
