import json

from imas_standard_names.issues.cli import subtract_standardnames


def test_subtract_standardnames(tmp_path, extended_names_data, base_names_data):
    """Directory-based subtraction should keep only names not in subtrahend.

    Creates two directories:
      minuend_dir: extended set (includes an extra entry a_new_standard_name)
      subtrahend_dir: baseline set
    The output directory should contain only the extra entry and an index.json listing it.
    """
    # Prepare directories
    minuend_dir = tmp_path / "minuend"
    subtrahend_dir = tmp_path / "subtrahend"
    output_dir = tmp_path / "out"

    # Use schema helpers through fixtures (indirectly) by writing minimal YAML files
    from imas_standard_names import schema

    minuend_dir.mkdir()
    subtrahend_dir.mkdir()

    # Write minuend entries
    for e in extended_names_data:
        schema.save_standard_name(schema.create_standard_name(e), minuend_dir)
    # Write subtrahend entries
    for e in base_names_data:
        schema.save_standard_name(schema.create_standard_name(e), subtrahend_dir)

    # Invoke CLI command
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(
        subtract_standardnames,
        (output_dir.as_posix(), minuend_dir.as_posix(), subtrahend_dir.as_posix()),
    )
    assert result.exit_code == 0, result.output

    # Only the extra file should remain
    remaining_files = list(output_dir.glob("*.yml"))
    assert len(remaining_files) == 1
    assert remaining_files[0].stem == "a_new_standard_name"

    # index.json should list only that name
    index_path = output_dir / "index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text())
    assert data == ["a_new_standard_name"]
