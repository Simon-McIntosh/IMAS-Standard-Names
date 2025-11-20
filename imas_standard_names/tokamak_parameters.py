"""Tokamak machine parameters data models and loader."""

import statistics
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class ParameterValue(BaseModel):
    """Single parameter with value, unit, and metadata."""

    value: float
    unit: str
    symbol: str | None = None
    note: str | None = None
    location: str | None = None
    scenario: str | None = None
    uncertainty: float | None = None


class ParameterStatistics(BaseModel):
    """Statistical summary of a parameter across multiple machines."""

    min: float
    max: float
    mean: float
    median: float
    unit: str
    symbol: str | None = None
    machine_count: int


class GeometryParameters(BaseModel):
    """Geometric parameters of tokamak."""

    major_radius: ParameterValue
    minor_radius: ParameterValue
    plasma_volume: ParameterValue
    elongation: ParameterValue | None = None
    triangularity: ParameterValue | None = None
    aspect_ratio: ParameterValue | None = None


class PhysicsParameters(BaseModel):
    """Physics and operational parameters."""

    toroidal_magnetic_field: ParameterValue
    plasma_current: ParameterValue
    edge_safety_factor: ParameterValue | None = None
    electron_density: ParameterValue | None = None
    ion_temperature: ParameterValue | None = None
    electron_temperature: ParameterValue | None = None
    energy_confinement_time: ParameterValue | None = None
    fusion_power: ParameterValue | None = None
    fusion_gain: ParameterValue | None = None


class DataSource(BaseModel):
    """Reference source for data."""

    url: str
    accessed: str | None = None
    description: str


class TokamakParameters(BaseModel):
    """Complete tokamak parameter set."""

    machine: str
    facility: str
    location: str
    operational_status: Literal["operational", "under_construction", "decommissioned"]
    last_updated: str
    sources: list[DataSource]
    geometry: GeometryParameters
    physics: PhysicsParameters


class TokamakParametersDB:
    """Database loader for tokamak parameters."""

    def __init__(self, root: Path | None = None):
        if root is None:
            # Use package resources
            root = (
                resources.files("imas_standard_names")
                / "resources"
                / "tokamak_parameters"
            )
        self.root = Path(root)
        self._cache: dict[str, TokamakParameters] = {}

    def list_machines(self) -> list[str]:
        """List all available tokamaks."""
        return [
            f.stem
            for f in self.root.glob("*.yml")
            if f.stem not in ("schema", "README")
        ]

    def get(self, machine: str) -> TokamakParameters:
        """Load parameters for specified tokamak."""
        machine_key = machine.lower().replace(" ", "-")

        if machine_key in self._cache:
            return self._cache[machine_key]

        filepath = self.root / f"{machine_key}.yml"
        if not filepath.exists():
            raise ValueError(
                f"Tokamak '{machine}' not found. "
                f"Available: {', '.join(self.list_machines())}"
            )

        with open(filepath) as f:
            data = yaml.safe_load(f)

        params = TokamakParameters.model_validate(data)
        self._cache[machine_key] = params
        return params

    def get_many(self, machines: list[str]) -> dict[str, TokamakParameters]:
        """Load parameters for multiple tokamaks."""
        return {machine: self.get(machine) for machine in machines}

    def get_all(self) -> dict[str, TokamakParameters]:
        """Load all tokamak parameters."""
        return {machine: self.get(machine) for machine in self.list_machines()}

    def compute_statistics(
        self, machines: list[str]
    ) -> dict[str, dict[str, ParameterStatistics]]:
        """Compute statistics across multiple machines for each parameter."""
        params_list = [self.get(m) for m in machines]

        def collect_values(
            param_name: str, category: str
        ) -> list[tuple[float, str, str | None]]:
            """Collect (value, unit, symbol) tuples for a parameter."""
            values = []
            for p in params_list:
                cat = getattr(p, category)
                param = getattr(cat, param_name, None)
                if param is not None:
                    values.append((param.value, param.unit, param.symbol))
            return values

        def make_stats(
            values: list[tuple[float, str, str | None]],
        ) -> ParameterStatistics | None:
            """Create statistics from collected values."""
            if not values:
                return None
            nums = [v[0] for v in values]
            return ParameterStatistics(
                min=min(nums),
                max=max(nums),
                mean=statistics.mean(nums),
                median=statistics.median(nums),
                unit=values[0][1],
                symbol=values[0][2],
                machine_count=len(nums),
            )

        # Compute statistics for each parameter
        geometry_stats = {}
        physics_stats = {}

        for param in [
            "major_radius",
            "minor_radius",
            "plasma_volume",
            "elongation",
            "triangularity",
            "aspect_ratio",
        ]:
            values = collect_values(param, "geometry")
            stat = make_stats(values)
            if stat:
                geometry_stats[param] = stat

        for param in [
            "toroidal_magnetic_field",
            "plasma_current",
            "edge_safety_factor",
            "electron_density",
            "ion_temperature",
            "electron_temperature",
            "energy_confinement_time",
            "fusion_power",
            "fusion_gain",
        ]:
            values = collect_values(param, "physics")
            stat = make_stats(values)
            if stat:
                physics_stats[param] = stat

        return {
            "geometry": geometry_stats,
            "physics": physics_stats,
        }
