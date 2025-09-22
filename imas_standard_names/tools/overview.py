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
    Updated to explicit naming: every aggregation key conveys that values are
    counts (number of entries). Coordinate frames and kinds include zero-count
    members for full visibility. Units aggregation includes dimensionless as
    the symbolic key 'dimensionless'.
    """

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
    async def get_overview(self, ctx: Context | None = None):
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
