"""Generic (reserved) name management.

This module provides the GenericNames helper used to detect and block proposals
that collide with reserved generic terms (e.g. 'current', 'area').

CSV format requirements:
    Unit,Generic Name
    m^2,area
    A,current

Only the 'Generic Name' column is required for collision checks; 'Unit' is
retained for human readability and potential future validation heuristics.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from functools import cached_property

import pandas

__all__ = ["GenericNames"]


@dataclass
class GenericNames:
    """Load and query reserved generic names from a CSV file."""

    input_: InitVar[str]
    data: pandas.DataFrame = field(init=False, repr=False)

    def __post_init__(self, input_: str):  # type: ignore[override]
        with open(input_, newline="") as f:
            self.data = pandas.read_csv(f)
        if "Generic Name" not in self.data.columns:
            raise ValueError("CSV must contain a 'Generic Name' column")

    @cached_property
    def names(self) -> list[str]:
        return self.data["Generic Name"].tolist()

    def __contains__(self, name: str) -> bool:  # pragma: no cover - trivial
        return name in self.names

    def check(self, standard_name: str) -> None:
        if standard_name in self:
            raise KeyError(
                f"The proposed standard name **{standard_name}** is a generic name."
            )
