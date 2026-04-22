"""Pydantic v2 loaders for the vNext vocabulary files (plan 38 W1c).

Each loader reads the corresponding YAML under
``imas_standard_names/grammar/vocabularies/`` and validates it with
strict Pydantic models (``extra='forbid'``).

Public API::

    axes   = load_coordinate_axes()    # CoordinateAxesRegistry
    loci   = load_locus_registry()     # LocusRegistry
    ops    = load_operators()          # OperatorRegistry
    bases  = load_physical_bases()     # PhysicalBasesRegistry
    geo    = load_geometry_carriers()  # GeometryCarriersRegistry
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_VOCAB_DIR = Path(__file__).parent / "vocabularies"


def _load_yaml(filename: str) -> dict:
    """Load a YAML file from the vocabularies directory."""
    path = _VOCAB_DIR / filename
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# ---------------------------------------------------------------------------
# coordinate_axes.yml
# ---------------------------------------------------------------------------


class CoordinateAxisDef(BaseModel, extra="forbid"):
    """A single coordinate axis entry."""

    aliases: list[str] = []


class CoordinateAxesRegistry(BaseModel, extra="forbid"):
    """Top-level structure of ``coordinate_axes.yml``."""

    axes: dict[str, CoordinateAxisDef]


def load_coordinate_axes() -> CoordinateAxesRegistry:
    """Load and validate ``coordinate_axes.yml``."""
    data = _load_yaml("coordinate_axes.yml")
    # YAML may contain entries as None (bare key) — normalise to empty dict
    raw_axes = data.get("axes") or {}
    normalised = {k: (v or {}) for k, v in raw_axes.items()}
    return CoordinateAxesRegistry(axes=normalised)


# ---------------------------------------------------------------------------
# locus_registry.yml
# ---------------------------------------------------------------------------

LocusType = Literal["entity", "position", "geometry"]
LocusRelation = Literal["of", "at", "over"]


class LocusEntry(BaseModel, extra="forbid"):
    """A single locus entry (entity, position, or geometry)."""

    type: LocusType
    allowed_relations: list[LocusRelation]


class LocusRegistry(BaseModel, extra="forbid"):
    """Top-level structure of ``locus_registry.yml``."""

    loci: dict[str, LocusEntry]


def load_locus_registry() -> LocusRegistry:
    """Load and validate ``locus_registry.yml``."""
    data = _load_yaml("locus_registry.yml")
    return LocusRegistry(**data)


# ---------------------------------------------------------------------------
# operators.yml
# ---------------------------------------------------------------------------

OperatorKind = Literal["unary_prefix", "unary_postfix", "binary"]


class OperatorDef(BaseModel, extra="forbid"):
    """A single operator entry."""

    kind: OperatorKind
    precedence: int
    returns: str | None = None
    arg_types: list[str] | None = None
    separator: str | None = None
    indexed: bool = False
    index_params: list[str] | None = None


class OperatorRegistry(BaseModel, extra="forbid"):
    """Top-level structure of ``operators.yml``."""

    operators: dict[str, OperatorDef]


def load_operators() -> OperatorRegistry:
    """Load and validate ``operators.yml``."""
    data = _load_yaml("operators.yml")
    return OperatorRegistry(**data)


# ---------------------------------------------------------------------------
# physical_bases.yml
# ---------------------------------------------------------------------------


class PhysicalBaseDef(BaseModel, extra="forbid"):
    """A single physical base entry (schema TBD by W2a)."""


class PhysicalBasesRegistry(BaseModel, extra="forbid"):
    """Top-level structure of ``physical_bases.yml``."""

    bases: dict[str, PhysicalBaseDef] = {}


def load_physical_bases() -> PhysicalBasesRegistry:
    """Load and validate ``physical_bases.yml``."""
    data = _load_yaml("physical_bases.yml")
    return PhysicalBasesRegistry(**data)


# ---------------------------------------------------------------------------
# geometry_carriers.yml
# ---------------------------------------------------------------------------


class GeometryCarrierDef(BaseModel, extra="forbid"):
    """A single geometry carrier entry (schema TBD by W2a)."""


class GeometryCarriersRegistry(BaseModel, extra="forbid"):
    """Top-level structure of ``geometry_carriers.yml``."""

    carriers: dict[str, GeometryCarrierDef] = {}


def load_geometry_carriers() -> GeometryCarriersRegistry:
    """Load and validate ``geometry_carriers.yml``."""
    data = _load_yaml("geometry_carriers.yml")
    return GeometryCarriersRegistry(**data)


# ---------------------------------------------------------------------------
# Cross-registry validation
# ---------------------------------------------------------------------------


class _AllRegistries(BaseModel):
    """Container used only for cross-registry duplicate-key checks."""

    axes: CoordinateAxesRegistry
    loci: LocusRegistry
    operators: OperatorRegistry
    bases: PhysicalBasesRegistry
    carriers: GeometryCarriersRegistry

    @model_validator(mode="after")
    def _no_duplicate_names_across_registries(self) -> _AllRegistries:
        """Assert no token appears in more than one vNext registry."""
        pools: list[tuple[str, set[str]]] = [
            ("coordinate_axes", set(self.axes.axes)),
            ("locus_registry", set(self.loci.loci)),
            ("operators", set(self.operators.operators)),
            ("physical_bases", set(self.bases.bases)),
            ("geometry_carriers", set(self.carriers.carriers)),
        ]
        seen: dict[str, str] = {}  # token -> first registry
        duplicates: list[str] = []
        for registry_name, tokens in pools:
            for token in tokens:
                if token in seen:
                    duplicates.append(
                        f"'{token}' in both '{seen[token]}' and '{registry_name}'"
                    )
                else:
                    seen[token] = registry_name
        if duplicates:
            raise ValueError(
                "Duplicate tokens found across vNext registries:\n  "
                + "\n  ".join(duplicates)
            )
        return self


def validate_no_cross_registry_duplicates() -> None:
    """Load all five registries and assert no duplicate token names.

    Raises ``ValueError`` if any token appears in more than one registry.
    """
    _AllRegistries(
        axes=load_coordinate_axes(),
        loci=load_locus_registry(),
        operators=load_operators(),
        bases=load_physical_bases(),
        carriers=load_geometry_carriers(),
    )
