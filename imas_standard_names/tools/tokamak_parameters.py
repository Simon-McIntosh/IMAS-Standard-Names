"""MCP tool for querying tokamak machine parameters."""

from fastmcp import Context

from imas_standard_names import __version__ as package_version
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tokamak_parameters import TokamakParametersDB
from imas_standard_names.tools.base import Tool


class TokamakParametersTool(Tool):
    """Tool providing authoritative tokamak machine parameters."""

    def __init__(self):
        super().__init__()
        self.db = TokamakParametersDB()

    @property
    def tool_name(self) -> str:
        return "tokamak_parameters"

    @mcp_tool(
        description=(
            "Get authoritative tokamak machine parameters with optional statistics. "
            "machines: single name (e.g., 'ITER'), space-separated list (e.g., 'ITER JET DIII-D'), or 'all'. "
            "Returns comprehensive geometry and physics parameters with sources. "
            "When multiple machines selected, includes min/max/mean/median statistics across machines."
        )
    )
    async def get_tokamak_parameters(
        self,
        machines: str = "all",
        ctx: Context | None = None,
    ):
        """Retrieve verified tokamak parameters with optional statistics aggregation.

        Args:
            machines: Single machine name, space-separated list, or 'all' for all machines
            ctx: MCP context

        Returns:
            For single machine: Full parameter set
            For multiple machines: Dict with 'machines' (full data) and 'statistics' (aggregated)
        """
        try:
            # Parse machines parameter
            if machines.lower() == "all":
                machine_list = self.db.list_machines()
            else:
                machine_list = [m.strip() for m in machines.split()]

            # Single machine: return full data only
            if len(machine_list) == 1:
                params = self.db.get(machine_list[0])
                result = params.model_dump()
                result["catalog_version"] = package_version
                return result

            # Multiple machines: return full data + statistics
            params_dict = self.db.get_many(machine_list)
            statistics = self.db.compute_statistics(machine_list)

            return {
                "machines": {k: v.model_dump() for k, v in params_dict.items()},
                "statistics": {
                    "geometry": {
                        k: v.model_dump() for k, v in statistics["geometry"].items()
                    },
                    "physics": {
                        k: v.model_dump() for k, v in statistics["physics"].items()
                    },
                },
                "machine_count": len(machine_list),
                "catalog_version": package_version,
            }

        except ValueError as e:
            available = self.db.list_machines()
            return {
                "error": "MachineNotFound",
                "message": str(e),
                "available_machines": available,
                "usage": "Provide single machine, space-separated list, or 'all'",
            }
