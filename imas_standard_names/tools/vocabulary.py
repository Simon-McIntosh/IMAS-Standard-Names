"""
Vocabulary gap detection and management tool for IMAS Standard Names.

This tool provides interface for vocabulary gap detection and modification:
- Audit: Detect missing tokens by analyzing naming patterns
- Check: Analyze specific names for vocabulary gaps
- Add: Add new tokens to vocabulary files (auto-runs codegen)
- Remove: Remove tokens from vocabulary files (auto-runs codegen)

For browsing available vocabulary tokens, use list_vocabulary tool.

Vocabulary Workflow:
    1. Use 'audit' or 'check' to identify missing tokens
    2. Use 'add' to update vocabulary YAML files
       - Codegen runs automatically after successful edits
    3. Check validation_status in result for 'codegen_success_restart_required'
    4. Restart MCP server to load updated grammar.types enums

Important: The MCP server must be restarted after vocabulary changes for the
          parser to recognize new tokens. Hot-reload is not supported.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context
from pydantic import TypeAdapter

from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.tools.base import CatalogTool
from imas_standard_names.vocabulary.audit import VocabularyAuditor
from imas_standard_names.vocabulary.editor import VocabularyEditor
from imas_standard_names.vocabulary.vocab_models import VocabularyInput


class VocabularyTool(CatalogTool):
    """Tool for vocabulary gap detection and management.

    Important: After adding/removing tokens, you must:
    1. Run codegen to regenerate grammar.types enums
    2. Restart the MCP server to load new enum values
    """

    def __init__(self, catalog):
        super().__init__(catalog)
        self._auditor = VocabularyAuditor(catalog)
        self._editor = VocabularyEditor()
        # Eagerly load spaCy at startup to avoid first-call latency
        self._auditor.preload_spacy()

    @property
    def tool_name(self) -> str:  # pragma: no cover - trivial
        return "vocabulary"

    @mcp_tool(
        description=(
            "Vocabulary gap detection and management for IMAS Standard Names. "
            "Supports four actions via discriminated union: "
            "(1) audit: detect missing tokens by analyzing naming patterns (frequency_threshold=3); "
            "(2) check: analyze a single name for potential missing tokens; "
            "(3) add: add tokens to vocabulary YAML files (auto-runs codegen); "
            "(4) remove: remove tokens from vocabulary files (auto-runs codegen). "
            "Use 'action' field to select operation. "
            "Add/remove operations automatically run codegen and return 'codegen_success_restart_required' status. "
            "After successful changes, restart the MCP server to load new grammar.types enums. "
            "For browsing available vocabulary tokens, use get_vocabulary_tokens tool."
        )
    )
    async def manage_vocabulary(
        self, payload: dict[str, Any], ctx: Context | None = None
    ) -> dict[str, Any]:
        """Vocabulary gap detection and management (audit, check, add, remove).

        Args:
            payload: Discriminated union with 'action' field:
                - action='audit': {action, vocabulary?, frequency_threshold?}
                - action='check': {action, name}
                - action='add': {action, vocabulary, tokens}
                - action='remove': {action, vocabulary, tokens}

        Returns:
            Structured result dict with operation-specific fields or
            error envelope with schema and examples.
        """
        try:
            # Parse discriminated union
            adapter: TypeAdapter = TypeAdapter(VocabularyInput)
            parsed_input = adapter.validate_python(payload)

            # Route to appropriate handler
            if parsed_input.action == "audit":
                result = self._auditor.audit(
                    vocabulary=parsed_input.vocabulary,
                    frequency_threshold=parsed_input.frequency_threshold,
                    max_results=parsed_input.max_results,
                )
            elif parsed_input.action == "check":
                result = self._auditor.check_name(name=parsed_input.name)
            elif parsed_input.action == "add":
                result = self._editor.add_tokens(
                    vocabulary=parsed_input.vocabulary,
                    tokens=parsed_input.tokens,
                )
            elif parsed_input.action == "remove":
                result = self._editor.remove_tokens(
                    vocabulary=parsed_input.vocabulary,
                    tokens=parsed_input.tokens,
                )
            else:
                return {
                    "error": "InvalidAction",
                    "message": f"Unknown action: {parsed_input.action}",
                    "valid_actions": ["audit", "check", "add", "remove"],
                }

            return result.model_dump()

        except Exception as e:
            return {
                "error": type(e).__name__,
                "message": str(e),
                "schema": self._get_input_schema(),
                "examples": self._get_input_examples(),
            }

    def _get_input_schema(self) -> dict[str, Any]:
        """Return JSON schema for VocabularyInput discriminated union."""
        return {
            "discriminator": "action",
            "variants": {
                "audit": {
                    "action": "audit (required, literal)",
                    "vocabulary": "components | subjects | geometric_bases | objects | positions | processes (optional)",
                    "frequency_threshold": "int >= 2 (optional, default=3)",
                    "max_results": "int >= 1 (optional, default=20)",
                },
                "check": {
                    "action": "check (required, literal)",
                    "name": "str (required, standard name to analyze)",
                },
                "add": {
                    "action": "add (required, literal)",
                    "vocabulary": "components | subjects | geometric_bases | objects | positions | processes (required)",
                    "tokens": "list[str] (required, min 1 token)",
                },
                "remove": {
                    "action": "remove (required, literal)",
                    "vocabulary": "components | subjects | geometric_bases | objects | positions | processes (required)",
                    "tokens": "list[str] (required, min 1 token)",
                },
            },
        }

    def _get_input_examples(self) -> list[dict[str, Any]]:
        """Return example inputs for each action."""
        return [
            {
                "description": "Audit all vocabularies for missing tokens",
                "input": {"action": "audit"},
            },
            {
                "description": "Audit positions vocabulary with custom threshold",
                "input": {
                    "action": "audit",
                    "vocabulary": "positions",
                    "frequency_threshold": 5,
                },
            },
            {
                "description": "Check single name for missing tokens",
                "input": {
                    "action": "check",
                    "name": "cross_sectional_area_of_flux_surface",
                },
            },
            {
                "description": "Add tokens to positions vocabulary",
                "input": {
                    "action": "add",
                    "vocabulary": "positions",
                    "tokens": ["flux_surface", "separatrix"],
                },
            },
            {
                "description": "Remove tokens from objects vocabulary",
                "input": {
                    "action": "remove",
                    "vocabulary": "objects",
                    "tokens": ["deprecated_diagnostic"],
                },
            },
        ]
