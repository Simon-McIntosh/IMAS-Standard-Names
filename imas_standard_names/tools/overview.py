from collections import Counter
from datetime import datetime, timezone  # noqa: F401  (will remove if unused)

from fastmcp import Context

from imas_standard_names import __version__ as package_version
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.schema import (
    Frame,
    StandardNameDerivedVector,
    StandardNameVector,
)
from imas_standard_names.tools.base import BaseTool


class OverviewTool(BaseTool):
    """Tool providing a high-level overview (aggregate statistics) of the
    Standard Names catalog for quick inspection and monitoring.

    Returned structure is stable JSON for programmatic consumption.
    Every aggregation key conveys that values are counts (number of entries).
    Coordinate frames and kinds include zero-count members for full visibility.
    Units aggregation includes dimensionless as the symbolic key 'dimensionless'.
    """

    def __init__(self, repository=None):  # type: ignore[no-untyped-def]
        super().__init__(repository)
        # Optional: an attached EditCatalog instance for staged diffs
        self.edit_catalog = None

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "get_overview"

    @mcp_tool(
        description=(
            "Return aggregate catalog overview: total_standard_names, "
            "standard_names_by_kind, standard_names_by_status, "
            "vector_standard_names_by_frame, standard_names_by_unit, "
            "standard_names_by_tag, version. Zero-count kinds/"
            "frames included; dimensionless unit appears as 'dimensionless'."
        )
    )
    async def get_standard_names_overview(self, ctx: Context | None = None):
        models = self.repository.list()
        total = len(models)

        # Counts by kind and status
        kind_counts = Counter(m.kind for m in models)
        status_counts = Counter(m.status for m in models)

        # Ensure all defined kinds appear (explicit enumeration for clarity)
        all_kinds = ["scalar", "derived_scalar", "vector", "derived_vector"]
        standard_names_by_kind = {k: kind_counts.get(k, 0) for k in all_kinds}

        # Status states (defined in schema.Status literal)
        all_status = ["draft", "active", "deprecated", "superseded"]
        standard_names_by_status = {s: status_counts.get(s, 0) for s in all_status}

        # Frames (vectors + derived vectors). Include all enum values with zeroes.
        frame_counts = Counter(
            str(m.frame)
            for m in models
            if isinstance(m, StandardNameVector | StandardNameDerivedVector)
        )
        vector_standard_names_by_frame = {
            f.value: frame_counts.get(f.value, 0) for f in Frame
        }

        # Units aggregation – gather every encountered unit; represent dimensionless
        # empty-string units under 'dimensionless'.
        unit_counter = Counter(
            "dimensionless" if m.unit == "" else m.unit for m in models
        )
        standard_names_by_unit = dict(sorted(unit_counter.items()))

        # Tag aggregation (flatten all tags; ignore empty tag lists)
        tag_counter = Counter(tag for m in models for tag in (m.tags or []))
        standard_names_by_tag = dict(sorted(tag_counter.items()))

        return {
            "total_standard_names": total,
            "standard_names_by_kind": standard_names_by_kind,
            "standard_names_by_status": standard_names_by_status,
            "vector_standard_names_by_frame": vector_standard_names_by_frame,
            "standard_names_by_unit": standard_names_by_unit,
            "standard_names_by_tag": standard_names_by_tag,
            "version": package_version,
        }

    # No legacy alias methods

    @mcp_tool(
        description=(
            "List standard names with commit/staging classification. Optional 'scope' "
            "argument filters output: all (default) | committed | staged | new | modified | renamed | deleted. "
            "Returns base structure {universal_set, committed, staged{new,modified,rename_map,deleted}, counts} "
            "for scope=all or committed only, staged block only, or a single list depending on scope. "
            "Committed derived from YAML filenames; staged diff via active EditCatalog when available, else set diff. "
            "Renamed entries returned as mapping old_name->new_name."
        )
    )
    async def list_standard_names(self, scope: str = "all", ctx: Context | None = None):  # noqa: D401
        """Return committed vs staged standard name identifiers.

        Fields:
            universal_set: all in-memory names.
            committed: names persisted on disk.
            staged.new / staged.deleted: set membership differences.
            staged.modified: structurally changed entries (needs EditCatalog).
            staged.rename_map: old_name -> new_name mapping for renames.
            counts: *_count metrics plus staged_total_count.
        """
        # Committed names from disk (filenames without parsing).
        committed = [
            f.stem
            for f in self.repository.store.yaml_files()  # type: ignore[attr-defined]
        ]
        committed.sort()

        # Universal (current) names.
        universal_set = self.repository.list_names()

        # Initialize staged diff containers.
        new: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        rename_map: dict[str, str] = {}

        # Use an attached EditCatalog instance (if any) for staged diffs
        edit_repo = getattr(self, "edit_catalog", None)
        if edit_repo is not None and hasattr(edit_repo, "diff"):
            try:
                diff = edit_repo.diff()
                new = [e["name"] for e in diff.get("added", [])]
                deleted = [e["name"] for e in diff.get("removed", [])]
                modified = [e["name"] for e in diff.get("updated", [])]
                rename_map = {
                    r.get("from"): r.get("to")  # type: ignore[dict-item]
                    for r in diff.get("renamed", [])
                    if r.get("from") and r.get("to")
                }
            except Exception:  # pragma: no cover
                edit_repo = None

        if edit_repo is None:
            committed_set = set(committed)
            current_set = set(universal_set)
            new = sorted(current_set - committed_set)
            deleted = sorted(committed_set - current_set)
            # modified + rename_map remain empty

        counts = {
            "universal_count": len(universal_set),
            "committed_count": len(committed),
            "new_count": len(new),
            "modified_count": len(modified),
            "renamed_count": len(rename_map),
            "deleted_count": len(deleted),
        }
        counts["staged_total_count"] = (
            counts["new_count"]
            + counts["modified_count"]
            + counts["renamed_count"]
            + counts["deleted_count"]
        )

        scope_normalized = scope.lower().strip()
        valid_scopes = {
            "all",
            "committed",
            "staged",
            "new",
            "modified",
            "renamed",
            "deleted",
        }
        if scope_normalized not in valid_scopes:
            raise ValueError(
                f"Invalid scope '{scope}'; expected one of: {', '.join(sorted(valid_scopes))}"
            )

        base_payload = {
            "universal_set": universal_set,
            "committed": committed,
            "staged": {
                "new": new,
                "modified": modified,
                "rename_map": rename_map,
                "deleted": deleted,
            },
            "counts": counts,
        }

        match scope_normalized:
            case "all":
                return base_payload
            case "committed":
                return {"committed": committed, "counts": counts}
            case "staged":
                return {"staged": base_payload["staged"], "counts": counts}
            case "new":
                return {"new": new, "counts": counts}
            case "modified":
                return {"modified": modified, "counts": counts}
            case "renamed":
                return {"rename_map": rename_map, "counts": counts}
            case "deleted":
                return {"deleted": deleted, "counts": counts}
            case _:
                return base_payload
