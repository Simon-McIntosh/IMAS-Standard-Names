"""CLI command to diff two standard name directories.

Produces a JSON report with added / removed / changed / unchanged sets and
optionally writes a reduced export of selected classes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import json
import hashlib
import click

from ..repositories import YamlStandardNameRepository


def _hash(entry) -> str:
    # Stable content hash excluding volatile ordering
    dumped = entry.model_dump(exclude_none=True, exclude_defaults=True)
    # Ensure deterministic key ordering
    payload = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_entries(root: Path):
    repo = YamlStandardNameRepository(root)
    return {m.name: m for m in repo.list()}


@click.command()
@click.argument("old_dir")
@click.argument("new_dir")
@click.argument("output_json")
@click.option(
    "--export-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional directory to export added+changed entries as per-file YAML",
)
@click.option(
    "--include-unchanged", is_flag=True, help="Include unchanged list in JSON output"
)
def diff_standardnames(
    old_dir: str,
    new_dir: str,
    output_json: str,
    export_dir: Path | None,
    include_unchanged: bool,
):
    """Diff two directories of per-file standard names.

    OLD_DIR is the baseline; NEW_DIR is compared against it. The JSON report
    includes lists: added, removed, changed (content hash differs), and optionally unchanged.
    """
    old_path = Path(old_dir)
    new_path = Path(new_dir)
    old_entries = _load_entries(old_path)
    new_entries = _load_entries(new_path)

    added = sorted(set(new_entries) - set(old_entries))
    removed = sorted(set(old_entries) - set(new_entries))

    changed = []
    unchanged = []
    common = set(old_entries) & set(new_entries)
    for name in sorted(common):
        if _hash(old_entries[name]) != _hash(new_entries[name]):
            changed.append(name)
        else:
            unchanged.append(name)

    report: Dict[str, Any] = {
        "old_dir": str(old_path),
        "new_dir": str(new_path),
        "added": added,
        "removed": removed,
        "changed": changed,
    }
    if include_unchanged:
        report["unchanged"] = unchanged

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if export_dir:
        export_dir.mkdir(parents=True, exist_ok=True)
        from ..repositories import YamlStandardNameRepository as _Repo
        from ..unit_of_work import UnitOfWork as _UOW

        repo_out = _Repo(export_dir)
        # Export union of added + changed entries from new set
        for name in added + changed:
            uow = _UOW(repo_out)
            uow.add(new_entries[name])
            uow.commit()

    click.echo(
        f"Diff written to {output_json} (added={len(added)}, removed={len(removed)}, changed={len(changed)})"
    )
