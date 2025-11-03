from fastmcp import Context

from imas_standard_names import __version__ as package_version
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.grammar.field_schemas import (
    DOCUMENTATION_GUIDANCE,
    FIELD_GUIDANCE,
    NAMING_GUIDANCE,
    PROVENANCE_MODES_INFO,
    TYPE_SPECIFIC_REQUIREMENTS,
)
from imas_standard_names.grammar.tag_types import (
    PRIMARY_TAG_DESCRIPTIONS,
    PRIMARY_TAGS,
    SECONDARY_TAG_DESCRIPTIONS,
    SECONDARY_TAGS,
)
from imas_standard_names.models import STANDARD_NAME_MODELS, StandardNameEntryBase
from imas_standard_names.tools.base import Tool

# Constants for common response strings
_PURPOSE_CREATE_ENTRIES = (
    "Create valid entry dicts for create_standard_names(entries=[...]) tool"
)
_PURPOSE_CREATE_KIND_ENTRIES = (
    "Create {} entry dicts for create_standard_names(entries=[...])"
)
_WORKFLOW_STEPS_BASE = [
    "1. get_naming_grammar → understand naming rules and compose valid name",
    "2. get_schema → review field guidance and requirements",
    "3. Construct entry dict with all required fields for chosen kind",
    "4. create_standard_names(entries=[...]) → stage in-memory",
    "5. list_standard_names(scope='pending') → review changes",
    "6. write_standard_names() → persist to disk",
]
_WORKFLOW_STEPS_KIND = [
    "1. get_naming_grammar → understand naming rules and compose valid name",
    "2. get_schema → review field guidance",
    "3. Construct entry dict with all required fields",
    "4. create_standard_names(entries=[...]) → stage in-memory",
    "5. list_standard_names(scope='pending') → review changes",
    "6. write_standard_names() → persist to disk",
]


class SchemaTool(Tool):
    """Tool providing catalog entry schema and validation guidance.

    Programmatically generates schema information from Pydantic models.
    Returns JSON schemas, field descriptions, examples, and composition guidance.
    """

    def __init__(self, examples_catalog: "StandardNameCatalog | None" = None):  # noqa: F821
        super().__init__()
        self.examples_catalog = examples_catalog

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "schema"

    @mcp_tool(
        description=(
            "Get catalog entry schema for creating standard name entries. "
            "Default (no kind): Returns base schema with kind-specific differences, "
            "examples, comprehensive field guidance, and workflow. "
            "kind='scalar'|'vector'|'metadata': Returns complete schema for specific entry type only."
        )
    )
    async def get_schema(
        self,
        kind: str | None = None,
        ctx: Context | None = None,
    ):
        """Return schema guidance for constructing catalog entry dicts."""
        if kind is None:
            return self._get_base_with_diffs()
        return self._get_kind_schema(kind)

    def _get_tags_vocabulary(self) -> dict:
        """Get tags vocabulary reference data (separate from field guidance).

        Returns:
            Dictionary with complete tag vocabularies and descriptions.
        """
        return {
            "primary_tags": PRIMARY_TAG_DESCRIPTIONS,
            "secondary_tags": SECONDARY_TAG_DESCRIPTIONS,
            "all_primary_tags": list(PRIMARY_TAGS),
            "all_secondary_tags": list(SECONDARY_TAGS),
            "ordering_rule": "tags[0] must be primary tag, tags[1:] are secondary tags",
        }

    def _get_examples_from_catalog(self, kind: str | None = None) -> list[dict]:
        """Load examples from catalog, filtered by kind.

        Args:
            kind: Entry kind to filter by (scalar/vector/metadata). If None, get all.

        Returns:
            List of example entry dicts (2-3 examples for variety).
        """
        if self.examples_catalog is None:
            return []

        # Get examples filtered by kind
        examples = self.examples_catalog.list(kind=kind)

        # Return 2-3 examples for variety
        selected = examples[:3]

        # Convert to dict format
        return [entry.model_dump() for entry in selected]

    def _get_examples_for_kind(self, kind: str | None = None) -> dict:
        """Get examples, optionally filtered by kind.

        Args:
            kind: If None, return examples for all kinds. If specified, return examples for that kind.

        Returns:
            Dictionary with examples list.
        """
        examples = self._get_examples_from_catalog(kind)
        return {"examples": examples} if examples else {}

    def _build_common_response_fields(
        self,
        purpose: str,
        workflow: list[str],
        kind: str | None = None,
    ) -> dict:
        """Build fields common to both response types.

        Args:
            purpose: Purpose statement for the response.
            workflow: List of workflow steps.
            kind: Entry kind for filtering examples and field guidance.

        Returns:
            Dictionary with common response fields.
        """
        # Build enhanced field guidance with documentation guidance
        enhanced_field_guidance = dict(FIELD_GUIDANCE)
        if "documentation" in enhanced_field_guidance:
            # Merge DOCUMENTATION_GUIDANCE into the documentation field guidance
            enhanced_field_guidance["documentation"] = {
                **enhanced_field_guidance["documentation"],
                **DOCUMENTATION_GUIDANCE,
            }
        else:
            # Add DOCUMENTATION_GUIDANCE as the documentation field guidance
            enhanced_field_guidance["documentation"] = DOCUMENTATION_GUIDANCE

        result = {
            "purpose": purpose,
            **self._get_examples_for_kind(kind),
            "field_guidance": enhanced_field_guidance,
            "naming_guidance": NAMING_GUIDANCE,
            "tags_vocabulary": self._get_tags_vocabulary(),
            "workflow": workflow,
            "catalog_version": package_version,
        }

        # Add provenance modes for scalar/vector (not for metadata or overview with None)
        if kind in ("scalar", "vector") and PROVENANCE_MODES_INFO:
            result["provenance_modes"] = PROVENANCE_MODES_INFO

        return result

    def _add_provenance_if_applicable(
        self, result: dict, schema: dict, kind: str | None = None
    ) -> None:
        """Add provenance_definitions (Pydantic schemas) to result if applicable for the kind.

        Args:
            result: Result dictionary to modify in-place.
            schema: JSON schema containing potential $defs.
            kind: Entry kind. Provenance not added if kind is 'metadata'.
        """
        if kind != "metadata":
            provenance_defs = schema.get("$defs", {})
            if provenance_defs:
                result["provenance_definitions"] = provenance_defs

    def _get_kind_schema(self, kind: str) -> dict:
        """Return complete schema for specific entry kind without base/diff structure."""
        if kind not in STANDARD_NAME_MODELS:
            return {
                "error": "Invalid kind",
                "message": f"Unknown kind: {kind}. Must be 'scalar', 'vector', or 'metadata'.",
                "available_kinds": list(STANDARD_NAME_MODELS.keys()),
            }

        model = STANDARD_NAME_MODELS[kind]
        schema = model.model_json_schema()

        # Build common response fields first
        result = self._build_common_response_fields(
            purpose=_PURPOSE_CREATE_KIND_ENTRIES.format(kind),
            workflow=_WORKFLOW_STEPS_KIND,
            kind=kind,
        )

        # Add kind-specific fields
        result.update(
            {
                "kind": kind,
                "description": TYPE_SPECIFIC_REQUIREMENTS[kind]["description"],
                "required_fields": TYPE_SPECIFIC_REQUIREMENTS[kind]["required_fields"],
                "optional_fields": TYPE_SPECIFIC_REQUIREMENTS[kind].get(
                    "optional_fields", []
                ),
                "field_schemas": {
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                },
            }
        )

        # Add provenance if applicable (not for metadata)
        self._add_provenance_if_applicable(result, schema, kind)

        return result

    def _get_base_with_diffs(self) -> dict:
        """Return base schema with kind-specific differences.

        Programmatically generates everything from Pydantic models and field_schemas.py.
        Prioritizes LLM-friendly structure: properties first, definitions separate.
        """
        base_schema = StandardNameEntryBase.model_json_schema()
        scalar_schema = STANDARD_NAME_MODELS["scalar"].model_json_schema()

        # Build common response fields first
        result = self._build_common_response_fields(
            purpose=_PURPOSE_CREATE_ENTRIES,
            workflow=_WORKFLOW_STEPS_BASE,
            kind=None,
        )

        # Add overview-specific fields
        result.update(
            {
                "base_schema": {
                    "description": "Common fields shared by all entry types",
                    "properties": base_schema.get("properties", {}),
                    "base_required": base_schema.get("required", []),
                    "note": "Kind-specific requirements add/override fields shown in entry_types",
                },
                "entry_types": TYPE_SPECIFIC_REQUIREMENTS,
                "provenance_definitions": {
                    "description": "Optional provenance schemas (scalar/vector only)",
                    "schemas": scalar_schema.get("$defs", {}),
                    "modes_info": PROVENANCE_MODES_INFO,
                },
                "use_kind_parameter": "Call with kind='scalar'|'vector'|'metadata' for specific schema without diffs",
            }
        )

        return result
