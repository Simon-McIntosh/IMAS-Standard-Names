from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import CatalogTool


class ListTool(CatalogTool):
    """Tool for listing and filtering standard names with persistence status.

    Provides catalog querying functionality to enumerate names with optional filters
    by unit, tags, kind, status, and persistence state (persisted vs pending).
    """

    def __init__(self, catalog, edit_catalog=None):  # type: ignore[no-untyped-def]
        super().__init__(catalog)
        self.edit_catalog = edit_catalog

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "list"

    @mcp_tool(
        description=(
            "List standard names with persistence status classification and optional field filters. "
            "'scope' filters output: all (default) | persisted | pending | new | modified | renamed | deleted. "
            "Also accepts legacy aliases: saved (for persisted) | unsaved (for pending). "
            "Optional filters: unit (exact match), tags (contains any), kind (scalar/vector), status (draft/active/deprecated/superseded). "
            "Returns base structure {universal_set, persisted, pending{new,modified,rename_map,deleted}, counts} "
            "for scope=all or persisted only, pending block only, or a single list depending on scope. "
            "Persisted names exist as YAML files on disk; pending names exist only in-memory. "
            "Renamed entries returned as mapping old_name->new_name. "
            "Use this when you need to enumerate/browse all available names or filter by persistence status or fields. "
            "For finding specific names by concept use search_standard_names; for details of known names use fetch_standard_names."
        )
    )
    async def list_standard_names(
        self,
        scope: str = "all",
        unit: str | int | None = None,
        tags: str | list[str] | None = None,
        kind: str | None = None,
        status: str | None = None,
        ctx: Context | None = None,
    ):  # noqa: D401
        """Return persisted vs pending standard name identifiers with optional filters.

        Fields:
            universal_set: all in-memory names.
            persisted: names written to disk as YAML files.
            pending.new / pending.deleted: set membership differences.
            pending.modified: structurally changed entries (needs EditCatalog).
            pending.rename_map: old_name -> new_name mapping for renames.
            counts: *_count metrics plus pending_total_count.

        Optional filters applied to all name sets:
            unit: exact match on unit field (numeric 1 converted to string "1")
            tags: match if entry contains any of the specified tags
            kind: scalar or vector
            status: draft, active, deprecated, or superseded
        """
        # Normalize unit filter: convert numeric 1 to string "1"
        if unit is not None and (unit == 1 or unit == 1.0):
            unit = "1"

        # Apply filters using repository filter method
        if unit is None and tags is None and kind is None and status is None:
            universal_set = self.catalog.list_names()
        else:
            filtered_entries = self.catalog.list(
                unit=unit, tags=tags, kind=kind, status=status
            )
            universal_set = sorted([e.name for e in filtered_entries])

        # Saved names from disk (filenames without parsing) - also filtered
        all_saved = [
            f.stem
            for f in self.catalog.store.yaml_files()  # type: ignore[attr-defined]
        ]
        all_saved.sort()

        # Apply filters to saved names if any filters specified
        if unit is None and tags is None and kind is None and status is None:
            saved = all_saved
        else:
            # Filter saved names by loading and checking each entry
            saved = [name for name in all_saved if name in universal_set]

        # Initialize unsaved diff containers.
        new: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        rename_map: dict[str, str] = {}

        # Use an attached EditCatalog instance (if any) for unsaved diffs
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
            saved_set = set(saved)
            current_set = set(universal_set)
            new = sorted(current_set - saved_set)
            deleted = sorted(saved_set - current_set)
            # modified + rename_map remain empty

        counts = {
            "universal_count": len(universal_set),
            "persisted_count": len(saved),
            "new_count": len(new),
            "modified_count": len(modified),
            "renamed_count": len(rename_map),
            "deleted_count": len(deleted),
            # Backward compatibility
            "saved_count": len(saved),
        }
        counts["pending_total_count"] = (
            counts["new_count"]
            + counts["modified_count"]
            + counts["renamed_count"]
            + counts["deleted_count"]
        )
        # Backward compatibility
        counts["unsaved_total_count"] = counts["pending_total_count"]

        scope_normalized = scope.lower().strip()
        # Map legacy aliases to new names
        scope_map = {
            "saved": "persisted",
            "unsaved": "pending",
        }
        scope_normalized = scope_map.get(scope_normalized, scope_normalized)

        valid_scopes = {
            "all",
            "persisted",
            "pending",
            "new",
            "modified",
            "renamed",
            "deleted",
        }
        if scope_normalized not in valid_scopes:
            raise ValueError(
                f"Invalid scope '{scope}'; expected one of: {', '.join(sorted(valid_scopes))} "
                f"(legacy aliases: saved, unsaved)"
            )

        base_payload = {
            "universal_set": universal_set,
            "persisted": saved,
            "pending": {
                "new": new,
                "modified": modified,
                "rename_map": rename_map,
                "deleted": deleted,
            },
            "counts": counts,
            # Backward compatibility
            "saved": saved,
            "unsaved": {
                "new": new,
                "modified": modified,
                "rename_map": rename_map,
                "deleted": deleted,
            },
        }

        match scope_normalized:
            case "all":
                return base_payload
            case "persisted":
                return {"persisted": saved, "counts": counts}
            case "pending":
                return {"pending": base_payload["pending"], "counts": counts}
            case "new":
                return {"new": new, "counts": counts}
            case "modified":
                return {"modified": modified, "counts": counts}
            case "renamed":
                return {"rename_map": rename_map, "counts": counts}
            case "deleted":
                return {"deleted": deleted, "counts": counts}
