"""
MCP tool for listing IMAS Standard Names vocabulary tokens.

This tool provides read-only access to vocabulary tokens for all grammar segments.
Returns controlled vocabulary with metadata, validation rules, and optional usage
statistics from existing catalog entries.

For vocabulary gap analysis and modification, use manage_vocabulary tool.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastmcp import Context

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.grammar.constants import SEGMENT_RULES, SEGMENT_TOKEN_MAP
from imas_standard_names.grammar.model import parse_standard_name
from imas_standard_names.grammar.tag_types import (
    PRIMARY_TAG_DESCRIPTIONS,
    PRIMARY_TAGS,
    SECONDARY_TAG_DESCRIPTIONS,
    SECONDARY_TAGS,
)
from imas_standard_names.tools.base import CatalogTool


class VocabularyTokensTool(CatalogTool):
    """Tool for retrieving vocabulary tokens with metadata and usage statistics."""

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "vocabulary_tokens"

    @mcp_tool(
        description=(
            "Get controlled vocabulary tokens used to compose IMAS Standard Names, with usage statistics. "
            "Most segments have controlled vocabularies - use only these exact tokens when composing names. "
            "Exception: physical_base is open vocabulary (any physics quantity in snake_case). "
            "Default (no segment): Returns all vocabularies with usage stats - best for exploring what's available. "
            "Call with segment parameter (component, subject, device, object, geometry, position, process, coordinate) "
            "to get detailed token list for one segment only. "
            "Parameters: include_usage (default true, shows frequency counts), "
            "include_metadata (default false, adds templates and validation rules). "
            "Complements get_naming_grammar which provides grammar rules and composition patterns. "
            "Call get_naming_grammar first to understand naming rules, then use this tool to see valid tokens for each segment."
        )
    )
    async def get_vocabulary_tokens(
        self,
        segment: str | None = None,
        include_usage: bool = True,
        include_metadata: bool = False,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Get vocabulary tokens for grammar segments.

        Args:
            segment: Specific segment to get (component, subject, etc.) or None for all
            include_usage: Include usage statistics from catalog (default: True)
            include_metadata: Include detailed metadata (default: False)
            ctx: MCP context

        Returns:
            Dictionary with complete token lists, metadata, and optional statistics
        """
        if segment:
            return await self._get_segment_vocabulary(
                segment, include_usage, include_metadata
            )
        else:
            return await self._get_all_vocabularies(include_usage, include_metadata)

    async def _get_segment_vocabulary(
        self, segment: str, include_usage: bool, include_metadata: bool
    ) -> dict[str, Any]:
        """Get vocabulary for a specific segment."""
        # Validate segment name
        valid_segments = {rule.identifier for rule in SEGMENT_RULES}
        if segment not in valid_segments:
            return {
                "error": "InvalidSegment",
                "message": f"Unknown segment '{segment}'. Valid segments: {sorted(valid_segments)}",
                "valid_segments": sorted(valid_segments),
            }

        segment_data = self._build_segment_data(segment, include_usage)
        return {segment: segment_data}

    async def _get_all_vocabularies(
        self, include_usage: bool, include_metadata: bool
    ) -> dict[str, Any]:
        """Get vocabularies for all segments."""
        segments = {}

        for rule in SEGMENT_RULES:
            segment_id = rule.identifier
            segments[segment_id] = self._build_segment_data(segment_id, include_usage)

        # Add tag vocabularies as special segments
        segments["primary_tags"] = self._build_tag_vocabulary("primary", include_usage)
        segments["secondary_tags"] = self._build_tag_vocabulary(
            "secondary", include_usage
        )

        # Add summary statistics
        summary = self._build_vocabulary_summary(segments)

        return {
            "segments": segments,
            "summary": summary,
        }

    def _build_segment_data(
        self, segment_id: str, include_usage: bool
    ) -> dict[str, Any]:
        """Build vocabulary data for a single segment."""
        # Get segment rule metadata
        rule = next((r for r in SEGMENT_RULES if r.identifier == segment_id), None)
        if not rule:
            return {"error": f"Segment rule not found for '{segment_id}'"}

        # Get tokens from the rule
        tokens = list(rule.tokens)

        # Build base segment info - always include full token list
        segment_data = {
            "segment_id": segment_id,
            "optional": rule.optional,
            "template": rule.template,
            "exclusive_with": list(rule.exclusive_with),
            "token_count": len(tokens),
            "tokens": tokens,
            "vocabulary_type": self._get_vocabulary_type(segment_id),
            "description": self._get_segment_description(segment_id),
        }

        # Add usage statistics if requested
        if include_usage and tokens:
            usage_stats = self._compute_token_usage(segment_id, tokens)
            segment_data["usage"] = usage_stats

        # Add validation rules
        segment_data["validation"] = self._get_segment_validation_rules(segment_id)

        return segment_data

    def _build_tag_vocabulary(
        self, tag_type: str, include_usage: bool
    ) -> dict[str, Any]:
        """Build vocabulary data for tag types (primary/secondary)."""
        if tag_type == "primary":
            tokens = list(PRIMARY_TAGS)
            descriptions = PRIMARY_TAG_DESCRIPTIONS
            description = (
                "Primary tags define catalog subdirectory organization (tags[0])"
            )
        else:
            tokens = list(SECONDARY_TAGS)
            descriptions = SECONDARY_TAG_DESCRIPTIONS
            description = "Secondary tags provide additional classification (tags[1:])"

        tag_data = {
            "tag_type": tag_type,
            "token_count": len(tokens),
            "tokens": tokens,
            "descriptions": descriptions,
            "description": description,
        }

        # Add usage statistics if requested
        if include_usage:
            usage_stats = self._compute_tag_usage(tag_type, tokens)
            tag_data["usage"] = usage_stats

        return tag_data

    def _build_vocabulary_summary(self, segments: dict) -> dict[str, Any]:
        """Build summary statistics across all vocabularies."""
        total_tokens = 0
        segment_counts = {}

        for segment_id, segment_data in segments.items():
            if "token_count" in segment_data:
                count = segment_data["token_count"]
                total_tokens += count
                segment_counts[segment_id] = count

        return {
            "total_tokens": total_tokens,
            "segment_counts": segment_counts,
            "enumerated_segments": len(
                [s for s in segments if s not in ["primary_tags", "secondary_tags"]]
            ),
        }

    def _get_vocabulary_type(self, segment_id: str) -> str:
        """Determine vocabulary type for segment."""
        vocab_map = SEGMENT_TOKEN_MAP
        if segment_id in vocab_map:
            return "enumerated"
        elif segment_id == "physical_base":
            return "open"
        else:
            return "derived"

    def _get_segment_description(self, segment_id: str) -> str:
        """Get human-readable description for segment."""
        descriptions = {
            "component": "Directional component of vector quantities (radial, toroidal, poloidal)",
            "coordinate": "Coordinate specification for position (radial, toroidal, poloidal)",
            "subject": "Physical entity being measured (electron, ion, neutral, photon)",
            "geometric_base": "Base geometric quantity (position, distance, angle, area, volume)",
            "physical_base": "Base physical quantity (open vocabulary - any physics term)",
            "object": "Physical object or diagnostic device being referenced",
            "device": "Specific diagnostic device or subsystem",
            "geometry": "Geometric shape or configuration",
            "position": "Spatial location or region specification",
            "process": "Physical process or mechanism",
        }
        return descriptions.get(segment_id, f"Grammar segment: {segment_id}")

    def _get_segment_validation_rules(self, segment_id: str) -> dict[str, Any]:
        """Get validation rules for segment."""
        rule = next((r for r in SEGMENT_RULES if r.identifier == segment_id), None)
        if not rule:
            return {}

        return {
            "optional": rule.optional,
            "mutually_exclusive_with": list(rule.exclusive_with),
            "has_template": rule.template is not None,
            "requires_base": segment_id in ["component", "coordinate"],
        }

    def _compute_token_usage(
        self, segment_id: str, tokens: list[str]
    ) -> dict[str, Any]:
        """Compute usage statistics for tokens in this segment."""
        # Get all names from catalog
        all_names = list(self.catalog.list_names())

        # Count token occurrences
        token_counts = Counter()
        for name in all_names:
            try:
                # Parse the name to extract grammar segments
                parsed = parse_standard_name(name)
                segment_value = getattr(parsed, segment_id, None)
                # Convert enum to string value if needed
                if segment_value and hasattr(segment_value, "value"):
                    segment_value = segment_value.value
                if segment_value and segment_value in tokens:
                    token_counts[segment_value] += 1
            except Exception:
                continue

        # Build usage statistics
        used_tokens = len([t for t in tokens if token_counts[t] > 0])
        unused_tokens = len(tokens) - used_tokens

        # Sort by frequency descending
        sorted_counts = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_tokens": len(tokens),
            "used_tokens": used_tokens,
            "unused_tokens": unused_tokens,
            "usage_rate": round(used_tokens / len(tokens) * 100, 1) if tokens else 0,
            "token_frequencies": dict(sorted_counts),
            "most_common": sorted_counts[:10] if sorted_counts else [],
        }

    def _compute_tag_usage(self, tag_type: str, tags: list[str]) -> dict[str, Any]:
        """Compute usage statistics for tags."""
        all_names = list(self.catalog.list_names())

        tag_counts = Counter()
        for name in all_names:
            try:
                entry = self.catalog.get(name)
                if entry and entry.tags:
                    if tag_type == "primary":
                        # Primary tag is tags[0]
                        primary = entry.tags[0]
                        if primary in tags:
                            tag_counts[primary] += 1
                    elif tag_type == "secondary" and len(entry.tags) > 1:
                        # Secondary tags are tags[1:]
                        for tag in entry.tags[1:]:
                            if tag in tags:
                                tag_counts[tag] += 1
            except Exception:
                continue

        used_tags = len([t for t in tags if tag_counts[t] > 0])
        unused_tags = len(tags) - used_tags

        # Sort by frequency descending
        sorted_counts = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_tags": len(tags),
            "used_tags": used_tags,
            "unused_tags": unused_tags,
            "usage_rate": round(used_tags / len(tags) * 100, 1) if tags else 0,
            "tag_frequencies": dict(sorted_counts),
            "most_common": sorted_counts[:10] if sorted_counts else [],
        }
