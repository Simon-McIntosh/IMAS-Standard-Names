"""Generic (reserved) name management.

This module provides the GenericNames helper used to detect and block proposals
that collide with reserved generic terms (e.g. 'current', 'area', 'voltage').

Generic physical bases are maintained in the grammar vocabulary system at:
    imas_standard_names/grammar/vocabularies/generic_physical_bases.yml

The list is code-generated into GENERIC_PHYSICAL_BASES constant during build.
"""

from dataclasses import dataclass

from imas_standard_names.grammar.constants import GENERIC_PHYSICAL_BASES

__all__ = ["GenericNames"]


@dataclass
class GenericNames:
    """Query reserved generic names from grammar vocabulary."""

    @property
    def names(self) -> tuple[str, ...]:
        """Return tuple of generic physical base names from grammar vocabulary."""
        return GENERIC_PHYSICAL_BASES

    def __contains__(self, name: str) -> bool:
        """Check if name is a generic physical base."""
        return name in GENERIC_PHYSICAL_BASES

    def check(self, standard_name: str) -> None:
        """Raise KeyError if standard_name is a generic physical base.

        Args:
            standard_name: The proposed standard name to check.

        Raises:
            KeyError: If standard_name matches a generic physical base.
        """
        if standard_name in self:
            raise KeyError(
                f"The proposed standard name **{standard_name}** is a generic name."
            )
