"""
Check tool for fast standard name validation.

This tool provides batch validation of standard names with minimal overhead.
It checks:
- Grammar validity (using parse without DB access)
- Existence in the catalog
- Basic metadata (status, kind, unit)

Similar to imas-dd-debug check_imas_paths but for standard names.
"""

from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any

from fastmcp import Context
from pydantic import ValidationError

import imas_standard_names.grammar.model as grammar_model
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.grammar import model_types as grammar_types
from imas_standard_names.tools.base import CatalogTool


class CheckTool(CatalogTool):
    """Tool for fast batch validation of standard names."""

    # Vocabulary mapping for error reporting
    VOCABULARY_MAP = {
        "component": grammar_types.Component,
        "coordinate": grammar_types.Component,  # Uses same vocabulary
        "subject": grammar_types.Subject,
        "object": grammar_types.Object,
        "geometry": grammar_types.Position,
        "position": grammar_types.Position,  # Uses same vocabulary
        "process": grammar_types.Process,
    }

    @staticmethod
    def _extract_missing_vocab_info(error_msg: str) -> tuple[str, str] | None:
        """Extract segment name and invalid value from Pydantic validation error.

        Args:
            error_msg: The validation error message from Pydantic

        Returns:
            Tuple of (segment_name, invalid_value) or None if not a vocab error
        """
        # Pattern: "Extra inputs are not permitted [type=extra_forbidden, input_value='X', input_type=str]"
        # Or newer pattern from field validation in error context
        match = re.search(r"input_value='([^']+)'", error_msg)
        if not match:
            return None

        invalid_value = match.group(1)

        # Try to extract the segment name from the error structure
        # Pattern like "1 validation error for StandardName\nsource\n  Extra inputs..."
        segment_match = re.search(r"for StandardName\n(\w+)\n", error_msg)
        if segment_match:
            segment_name = segment_match.group(1)
            return (segment_name, invalid_value)

        return None

    @staticmethod
    def _find_similar_vocabulary(
        invalid_value: str, vocabulary_enum: type, max_suggestions: int = 3
    ) -> list[str]:
        """Find similar vocabulary terms using difflib.

        Args:
            invalid_value: The value that was not found in vocabulary
            vocabulary_enum: The enum class containing valid vocabulary
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of similar vocabulary terms
        """
        valid_values = [v.value for v in vocabulary_enum]
        # Use difflib's get_close_matches with cutoff of 0.6 for reasonable similarity
        matches = get_close_matches(
            invalid_value, valid_values, n=max_suggestions, cutoff=0.6
        )
        return matches

    def _format_vocabulary_error(self, error_msg: str) -> str:
        """Format a vocabulary validation error with helpful suggestions.

        Args:
            error_msg: The raw validation error message

        Returns:
            Formatted error message with suggestions
        """
        vocab_info = self._extract_missing_vocab_info(error_msg)
        if not vocab_info:
            return error_msg

        segment_name, invalid_value = vocab_info
        vocabulary_enum = self.VOCABULARY_MAP.get(segment_name)

        if not vocabulary_enum:
            return error_msg

        # Find similar terms
        suggestions = self._find_similar_vocabulary(invalid_value, vocabulary_enum)

        # Build helpful error message
        error_parts = [
            f"MissingVocabulary: '{invalid_value}' is not in the '{segment_name}' vocabulary."
        ]

        if suggestions:
            error_parts.append(
                f"Did you mean: {', '.join(repr(s) for s in suggestions)}?"
            )
        else:
            # Show a few valid options if no close matches
            valid_values = [v.value for v in vocabulary_enum][:5]
            error_parts.append(
                f"Valid {segment_name} values include: {', '.join(repr(v) for v in valid_values)}..."
            )

        return " ".join(error_parts)

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "standard-name-check"

    @mcp_tool(
        description=(
            "Fast batch validation of IMAS standard names. "
            "Accepts space-delimited string or list of names. "
            "Returns existence status, grammar validity, and basic metadata. "
            "Use this when you already know the exact name(s) and just need to validate they exist or check basic info (faster than fetch). "
            "For discovery use search_standard_names; for detailed metadata use fetch_standard_names."
        )
    )
    async def check_standard_names(
        self,
        names: str | list[str],
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Fast batch validation of standard names.

        Args:
            names: Space-delimited string or list of standard names to check.

        Returns:
            Dictionary with summary statistics and per-name results including
            existence status, grammar validity, and basic metadata.
        """
        # Parse input - handle both string and list
        name_list = names.split() if isinstance(names, str) else names

        results = []
        for name in name_list:
            # Grammar validation (fast - no DB access)
            grammar_valid = True
            grammar_errors: list[str] = []
            try:
                grammar_model.parse_standard_name(name)
            except ValidationError as e:
                # Pydantic validation error - likely vocabulary issue
                grammar_valid = False
                raw_error = str(e)
                formatted_error = self._format_vocabulary_error(raw_error)
                grammar_errors = [formatted_error]
            except Exception as e:
                # Other parsing errors
                grammar_valid = False
                grammar_errors = [str(e)]

            # Existence check (fast - indexed query)
            exists = self.catalog.exists(name)

            # Get minimal metadata if exists
            if exists:
                entry = self.catalog.get(name)
                if entry:  # pragma: no branch - defensive
                    result = {
                        "name": name,
                        "exists": True,
                        "status": entry.status,
                        "kind": entry.kind,
                        "unit": str(entry.unit),
                        "grammar_valid": grammar_valid,
                        "grammar_errors": [],
                    }
                else:  # pragma: no cover - defensive
                    result = {
                        "name": name,
                        "exists": False,
                        "status": None,
                        "kind": None,
                        "unit": None,
                        "grammar_valid": grammar_valid,
                        "grammar_errors": grammar_errors,
                    }
            else:
                result = {
                    "name": name,
                    "exists": False,
                    "status": None,
                    "kind": None,
                    "unit": None,
                    "grammar_valid": grammar_valid,
                    "grammar_errors": grammar_errors,
                }

            results.append(result)

        # Build summary statistics
        summary = {
            "total": len(results),
            "found": sum(1 for r in results if r["exists"]),
            "not_found": sum(1 for r in results if not r["exists"]),
            "invalid": sum(1 for r in results if not r["grammar_valid"]),
        }

        return {"summary": summary, "results": results}
