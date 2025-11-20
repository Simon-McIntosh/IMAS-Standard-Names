"""MCP tool for comprehensive catalog validation.

Validates all standard names in the catalog against:
- Grammar rules and vocabulary
- Schema compliance
- Provenance integrity
- Tag validity
- Unit formatting
- Cross-references
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastmcp import Context
from pydantic import ValidationError

import imas_standard_names.grammar.model as grammar_model
from imas_standard_names.decorators.mcp import mcp_tool
from imas_standard_names.models import (
    StandardNameMetadataEntry,
    StandardNameScalarEntry,
    StandardNameVectorEntry,
)
from imas_standard_names.tools.base import CatalogTool
from imas_standard_names.validation.description import validate_description


class ValidateCatalogTool(CatalogTool):
    """Tool for comprehensive catalog validation."""

    @property
    def tool_name(self) -> str:
        """Return the name of this tool."""
        return "validate_catalog"

    @mcp_tool(
        description=(
            "Validate all standard names in the catalog. "
            "Checks grammar, schema, provenance, tags, units, and cross-references. "
            "Returns structured report of issues found. "
            "Use scope='persisted' (default) for saved entries, 'pending' for in-memory, or 'all'. "
            "Use include_warnings=True to include non-critical issues. "
            "Use checks=['grammar', 'provenance'] to run specific validation categories."
        )
    )
    async def validate_catalog(
        self,
        scope: str = "persisted",
        include_warnings: bool = True,
        checks: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Validate catalog entries comprehensively.

        Args:
            scope: Which entries to validate - 'persisted', 'pending', or 'all'
            include_warnings: Include non-critical warnings in output
            checks: Specific checks to run, or None for all checks
            ctx: MCP context (unused)

        Returns:
            Validation report with summary, issues by category, and detailed findings
        """
        # Normalize scope
        scope = scope.lower()
        if scope not in ("persisted", "pending", "all"):
            return {
                "error": "InvalidScope",
                "message": f"scope must be 'persisted', 'pending', or 'all', got: {scope}",
            }

        # Get names to validate based on scope
        if scope == "persisted":
            names_to_check = list(self.catalog.list_names())
        elif scope == "pending":
            # For now, pending validation would need unit of work integration
            # Simplified: just return empty for pending
            return {
                "summary": {
                    "total_entries": 0,
                    "valid_entries": 0,
                    "invalid_entries": 0,
                    "scope": "pending",
                    "checks_enabled": checks or "all",
                },
                "issues_by_category": {},
                "invalid_entries": [],
                "warnings": [],
            }
        else:  # all
            names_to_check = list(self.catalog.list_names())

        # Determine which checks to run
        all_checks = {
            "grammar",
            "schema",
            "provenance",
            "tags",
            "units",
            "references",
            "descriptions",
            "documentation",
        }
        if checks is None:
            enabled_checks = all_checks
        else:
            enabled_checks = set(checks) & all_checks
            if not enabled_checks:
                return {
                    "error": "InvalidChecks",
                    "message": f"No valid checks specified. Valid: {sorted(all_checks)}",
                }

        # Run validation
        issues: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        for name in names_to_check:
            entry = self.catalog.get(name)
            if not entry:
                continue

            # Debug: Check entry type for metadata entries
            if name in ["plasma_boundary", "scrape_off_layer"]:
                print(
                    f"DEBUG {name}: type={type(entry).__name__}, kind={getattr(entry, 'kind', 'NONE')}, has_unit={hasattr(entry, 'unit')}, unit_value={getattr(entry, 'unit', 'NOATTR')}"
                )

            # Grammar validation
            if "grammar" in enabled_checks:
                grammar_issues = self._validate_grammar(name, entry)
                issues.extend(grammar_issues)

            # Schema validation
            if "schema" in enabled_checks:
                schema_issues = self._validate_schema(name, entry)
                issues.extend(schema_issues)

            # Provenance validation
            if "provenance" in enabled_checks:
                prov_issues = self._validate_provenance(name, entry)
                issues.extend(prov_issues)

            # Tag validation
            if "tags" in enabled_checks:
                tag_issues, tag_warnings = self._validate_tags(name, entry)
                issues.extend(tag_issues)
                if include_warnings:
                    warnings.extend(tag_warnings)

            # Unit validation
            if "units" in enabled_checks:
                unit_issues = self._validate_units(name, entry)
                issues.extend(unit_issues)

            # Reference validation
            if "references" in enabled_checks:
                ref_issues = self._validate_references(name, entry)
                issues.extend(ref_issues)

            # Description validation
            if "descriptions" in enabled_checks:
                desc_warnings = self._validate_description(name, entry)
                if include_warnings:
                    warnings.extend(desc_warnings)

            # Documentation validation
            if "documentation" in enabled_checks:
                doc_issues = self._validate_documentation_field(name, entry)
                issues.extend(doc_issues)

        # Build summary
        total_entries = len(names_to_check)
        invalid_count = len({issue["name"] for issue in issues})
        valid_count = total_entries - invalid_count

        # Categorize issues
        issues_by_category = {
            "grammar_errors": len([i for i in issues if i["category"] == "grammar"]),
            "schema_errors": len([i for i in issues if i["category"] == "schema"]),
            "provenance_errors": len(
                [i for i in issues if i["category"] == "provenance"]
            ),
            "tag_errors": len([i for i in issues if i["category"] == "tags"]),
            "unit_errors": len([i for i in issues if i["category"] == "units"]),
            "reference_errors": len(
                [i for i in issues if i["category"] == "references"]
            ),
            "description_warnings": len(
                [w for w in warnings if w["category"] == "descriptions"]
            ),
            "documentation_errors": len(
                [i for i in issues if i["category"] == "documentation"]
            ),
        }

        return {
            "summary": {
                "total_entries": total_entries,
                "valid_entries": valid_count,
                "invalid_entries": invalid_count,
                "scope": scope,
                "checks_enabled": sorted(enabled_checks),
            },
            "issues_by_category": issues_by_category,
            "invalid_entries": issues,
            "warnings": warnings if include_warnings else [],
        }

    def _validate_grammar(self, name: str, entry: Any) -> list[dict[str, Any]]:
        """Validate grammar compliance."""
        issues = []
        try:
            grammar_model.parse_standard_name(name)
        except ValidationError as e:
            # Extract user-friendly error message
            error_msg = str(e)
            if "Generic physical_base" in error_msg:
                # Extract the specific error for generic bases
                lines = error_msg.split("\n")
                for line in lines:
                    if "Generic physical_base" in line:
                        error_msg = line.strip()
                        break

            issues.append(
                {
                    "name": name,
                    "category": "grammar",
                    "severity": "error",
                    "message": f"Grammar validation failed: {error_msg[:200]}",
                    "suggestion": "Review grammar rules and naming conventions",
                }
            )
        except Exception as e:
            issues.append(
                {
                    "name": name,
                    "category": "grammar",
                    "severity": "error",
                    "message": f"Failed to parse: {str(e)[:150]}",
                    "suggestion": "Check for invalid characters or malformed name",
                }
            )

        return issues

    def _validate_schema(self, name: str, entry: Any) -> list[dict[str, Any]]:
        """Validate schema compliance with kind-specific required fields."""
        issues = []

        # Get entry kind
        kind = getattr(entry, "kind", None)
        if not kind:
            issues.append(
                {
                    "name": name,
                    "category": "schema",
                    "severity": "error",
                    "message": "Missing required field: kind",
                    "suggestion": "Add kind field (scalar, vector, or metadata)",
                }
            )
            return issues

        # Check documentation field (required for all kinds)
        if (
            not hasattr(entry, "documentation")
            or not getattr(entry, "documentation", "").strip()
        ):
            issues.append(
                {
                    "name": name,
                    "category": "schema",
                    "severity": "error",
                    "message": "Missing required field: documentation",
                    "suggestion": "Add comprehensive documentation field",
                }
            )

        # Define required fields by kind using models
        # kind_models = {
        #     "scalar": StandardNameScalarEntry,
        #     "vector": StandardNameVectorEntry,
        #     "metadata": StandardNameMetadataEntry,
        # }

        # Common required fields for all kinds
        common_required = ["name", "description", "documentation", "tags"]

        # Kind-specific required fields
        kind_specific_required = {
            "scalar": ["unit"],  # scalar requires unit
            "vector": ["unit"],  # vector requires unit
            "metadata": [],  # metadata does NOT require unit
        }

        # Check common required fields
        for field in common_required:
            if not hasattr(entry, field):
                issues.append(
                    {
                        "name": name,
                        "category": "schema",
                        "severity": "error",
                        "message": f"Missing required field: {field}",
                        "suggestion": f"Add {field} to the entry",
                    }
                )
            elif field in ("name", "description", "documentation"):
                # Check for empty strings in critical text fields
                value = getattr(entry, field, "")
                if not value or (isinstance(value, str) and not value.strip()):
                    issues.append(
                        {
                            "name": name,
                            "category": "schema",
                            "severity": "error",
                            "message": f"Field {field} cannot be empty",
                            "suggestion": f"Provide content for {field}",
                        }
                    )

        # Check kind-specific required fields
        for field in kind_specific_required.get(kind, []):
            if not hasattr(entry, field):
                issues.append(
                    {
                        "name": name,
                        "category": "schema",
                        "severity": "error",
                        "message": f"Missing required field for {kind} entry: {field}",
                        "suggestion": f"Add {field} to the entry (use '1' for dimensionless quantities)"
                        if field == "unit"
                        else f"Add {field} to the entry",
                    }
                )
            elif field == "unit":
                # Special handling for unit field
                unit_value = getattr(entry, field, None)
                if unit_value is None or unit_value == "":
                    issues.append(
                        {
                            "name": name,
                            "category": "schema",
                            "severity": "error",
                            "message": f"Field {field} is required for {kind} entries",
                            "suggestion": "Add unit field (use '1' for dimensionless quantities)",
                        }
                    )

        # Re-validate through Pydantic model to catch field validators
        try:
            ModelClass = None
            if kind == "scalar":
                ModelClass = StandardNameScalarEntry
            elif kind == "vector":
                ModelClass = StandardNameVectorEntry
            elif kind == "metadata":
                ModelClass = StandardNameMetadataEntry

            if ModelClass:
                # Convert entry to dict and re-validate
                # Use exclude_none=True to remove None values that shouldn't be serialized
                # This is critical for metadata entries which don't have unit/provenance
                entry_dict = (
                    entry.model_dump(exclude_none=True, mode="json")
                    if hasattr(entry, "model_dump")
                    else {}
                )

                # For metadata entries, also remove unit and provenance fields if they exist
                # These fields shouldn't be present in metadata entries (extra="forbid")
                # The issue is that row_to_model() sets unit="" for all entries
                if kind == "metadata":
                    entry_dict.pop("unit", None)
                    entry_dict.pop("provenance", None)

                # Debug: print what we're validating
                if kind == "metadata" and name in [
                    "plasma_boundary",
                    "scrape_off_layer",
                ]:
                    print(f"DEBUG {name}: {json.dumps(entry_dict, indent=2)}")

                # Re-validate through Pydantic model - this will trigger field validators
                ModelClass(**entry_dict)

        except Exception as e:
            # Extract the actual validation error message
            error_msg = str(e)
            # For Pydantic ValidationError, extract the useful parts
            if "validation error" in error_msg.lower():
                # Parse out the field and message
                lines = error_msg.split("\n")
                field_name = None
                validation_msg = None
                for i, line in enumerate(lines):
                    if "Value error," in line:
                        validation_msg = line.split("Value error,", 1)[1].strip()
                        # Look back for field name
                        if i > 0:
                            field_name = lines[i - 1].strip()
                        break

                if validation_msg:
                    issues.append(
                        {
                            "name": name,
                            "category": "schema",
                            "severity": "error",
                            "message": f"{field_name}: {validation_msg}"
                            if field_name
                            else validation_msg,
                            "suggestion": "Review field formatting and validation requirements",
                        }
                    )
                else:
                    # Fallback to showing the full error
                    issues.append(
                        {
                            "name": name,
                            "category": "schema",
                            "severity": "error",
                            "message": error_msg[:300],
                            "suggestion": "Review entry schema and field requirements",
                        }
                    )
            else:
                issues.append(
                    {
                        "name": name,
                        "category": "schema",
                        "severity": "error",
                        "message": f"Validation failed: {error_msg[:200]}",
                        "suggestion": "Review entry schema and field requirements",
                    }
                )

        return issues

    def _validate_documentation_field(
        self, name: str, entry: Any
    ) -> list[dict[str, Any]]:
        """Validate documentation field presence and quality."""
        issues = []

        # Check if documentation field exists
        if not hasattr(entry, "documentation"):
            issues.append(
                {
                    "name": name,
                    "category": "documentation",
                    "severity": "error",
                    "message": "Missing required field: documentation",
                    "suggestion": "Add comprehensive documentation field with definition, usage context, and relevant links",
                }
            )
            return issues

        # Get documentation value
        doc = getattr(entry, "documentation", None)

        # Check if documentation is empty or whitespace-only
        if not doc or not str(doc).strip():
            issues.append(
                {
                    "name": name,
                    "category": "documentation",
                    "severity": "error",
                    "message": "Documentation field is empty",
                    "suggestion": "Add comprehensive documentation with definition, usage context, and relevant links",
                }
            )
            return issues

        # Check minimum length (at least 20 characters for meaningful documentation)
        doc_str = str(doc).strip()
        if len(doc_str) < 20:
            issues.append(
                {
                    "name": name,
                    "category": "documentation",
                    "severity": "error",
                    "message": f"Documentation is too brief ({len(doc_str)} chars, minimum 20)",
                    "suggestion": "Expand documentation with more detail about definition, usage, and context",
                }
            )

        return issues

    def _validate_provenance(self, name: str, entry: Any) -> list[dict[str, Any]]:
        """Validate provenance references."""
        issues = []

        # Check expression provenance dependencies
        if hasattr(entry, "provenance") and entry.provenance:
            prov = entry.provenance
            # Check dependencies in expression provenance
            if hasattr(prov, "dependencies") and prov.dependencies:
                for dep_name in prov.dependencies:
                    if not self.catalog.exists(dep_name):
                        issues.append(
                            {
                                "name": name,
                                "category": "provenance",
                                "severity": "error",
                                "message": f"expression dependency references non-existent name: '{dep_name}'",
                                "suggestion": "Fix reference or create the referenced entry",
                            }
                        )

            # Check base references for operator/reduction provenance
            if hasattr(prov, "base") and prov.base:
                if not self.catalog.exists(prov.base):
                    issues.append(
                        {
                            "name": name,
                            "category": "provenance",
                            "severity": "error",
                            "message": f"provenance base references non-existent name: '{prov.base}'",
                            "suggestion": "Fix reference or create the base entry",
                        }
                    )

        # Check superseded_by reference (entry-level field)
        if hasattr(entry, "superseded_by") and entry.superseded_by:
            if not self.catalog.exists(entry.superseded_by):
                issues.append(
                    {
                        "name": name,
                        "category": "provenance",
                        "severity": "error",
                        "message": f"superseded_by references non-existent name: '{entry.superseded_by}'",
                        "suggestion": "Fix reference or create the replacement entry",
                    }
                )

        # Check deprecates reference (entry-level field)
        if hasattr(entry, "deprecates") and entry.deprecates:
            if not self.catalog.exists(entry.deprecates):
                issues.append(
                    {
                        "name": name,
                        "category": "provenance",
                        "severity": "error",
                        "message": f"deprecates references non-existent name: '{entry.deprecates}'",
                        "suggestion": "Fix reference or remove deprecates field",
                    }
                )

        return issues

    def _validate_tags(
        self, name: str, entry: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Validate tags. Returns (errors, warnings)."""
        issues = []
        warnings = []

        if not hasattr(entry, "tags") or not entry.tags:
            warnings.append(
                {
                    "name": name,
                    "category": "tags",
                    "severity": "warning",
                    "message": "No tags specified",
                    "suggestion": "Add relevant tags to improve discoverability",
                }
            )
            return issues, warnings

        # Check for empty tags - be explicit about checking the raw list
        # since Pydantic may filter some values during validation
        for i, tag in enumerate(entry.tags):
            if tag is None or (isinstance(tag, str) and len(tag.strip()) == 0):
                issues.append(
                    {
                        "name": name,
                        "category": "tags",
                        "severity": "error",
                        "message": f"Contains empty or whitespace-only tag at position {i}",
                        "suggestion": "Remove empty tags",
                    }
                )

        return issues, warnings

    def _validate_units(self, name: str, entry: Any) -> list[dict[str, Any]]:
        """Validate unit formatting."""
        issues = []

        if not hasattr(entry, "unit"):
            return issues

        unit_str = str(entry.unit)

        # Check for invalid unit patterns (basic checks)
        if not unit_str or unit_str.strip() == "":
            # Dimensionless is OK
            return issues

        # Check for malformed exponents
        if "^" in unit_str:
            # Check that exponents are numeric
            parts = unit_str.split("^")
            for part in parts[1:]:
                # Get the exponent part (before next . or * or /)
                exp = ""
                for char in part:
                    if char.isdigit() or char == "-":
                        exp += char
                    else:
                        break
                if exp and not exp.lstrip("-").isdigit():
                    issues.append(
                        {
                            "name": name,
                            "category": "units",
                            "severity": "error",
                            "message": f"Invalid exponent in unit: {unit_str}",
                            "suggestion": "Use numeric exponents (e.g., m^2, not m^two)",
                        }
                    )
                    break

        return issues

    def _validate_description(self, name: str, entry: Any) -> list[dict[str, Any]]:
        """Validate description against tags for metadata leakage."""
        warnings = []

        if not hasattr(entry, "description") or not entry.description:
            return warnings

        # Serialize entry to dict for validation function
        entry_dict = entry.model_dump() if hasattr(entry, "model_dump") else {}

        # Run description validation
        issues = validate_description(entry_dict)

        # Convert issues to warning format
        for issue in issues:
            warnings.append(
                {
                    "name": name,
                    "category": "descriptions",
                    "severity": issue.get("severity", "warning"),
                    "message": issue["message"],
                    "suggestion": issue.get(
                        "suggestion", "Review description and tags for redundancy"
                    ),
                }
            )

        return warnings

    def _validate_references(self, name: str, entry: Any) -> list[dict[str, Any]]:
        """Validate cross-references in links field and inline documentation links."""
        issues = []
        warnings = []

        # Check links field references
        if hasattr(entry, "links") and entry.links:
            for link in entry.links:
                if isinstance(link, dict):
                    # Structured link with type and name
                    link_type = link.get("type", "")
                    link_name = link.get("name", "")

                    if link_type == "standard_name" and link_name:
                        if not self.catalog.exists(link_name):
                            issues.append(
                                {
                                    "name": name,
                                    "category": "references",
                                    "severity": "error",
                                    "message": f"links field references non-existent standard name: '{link_name}'",
                                    "suggestion": "Fix reference or create the referenced entry",
                                }
                            )
                elif isinstance(link, str):
                    # Legacy format: "name:standard_name_token"
                    if link.startswith("name:"):
                        link_name = link[5:]  # Remove "name:" prefix
                        if not self.catalog.exists(link_name):
                            issues.append(
                                {
                                    "name": name,
                                    "category": "references",
                                    "severity": "error",
                                    "message": f"links field references non-existent standard name: '{link_name}'",
                                    "suggestion": "Fix reference or create the referenced entry",
                                }
                            )

        # Check inline links in documentation field
        if hasattr(entry, "documentation") and entry.documentation:
            # Pattern to match markdown links: [text](#anchor) or [text](url)
            markdown_link_pattern = r"\[([^\]]+)\]\(#?([^\)]+)\)"

            for match in re.finditer(markdown_link_pattern, entry.documentation):
                link_text = match.group(1)
                link_target = match.group(2)

                # Check if it's an anchor link (internal standard name reference)
                # Anchor links should match standard name tokens
                if not link_target.startswith("http://") and not link_target.startswith(
                    "https://"
                ):
                    # This is an internal reference - validate it exists
                    if not self.catalog.exists(link_target):
                        # Check if it's just a URL without protocol
                        if "." in link_target and "/" in link_target:
                            # Likely an external URL - warn but don't error
                            warnings.append(
                                {
                                    "name": name,
                                    "category": "references",
                                    "severity": "warning",
                                    "message": f"documentation contains link that looks like URL but missing protocol: [{link_text}]({link_target})",
                                    "suggestion": "Add http:// or https:// prefix for external URLs",
                                }
                            )
                        else:
                            # Internal reference that doesn't exist
                            warnings.append(
                                {
                                    "name": name,
                                    "category": "references",
                                    "severity": "warning",
                                    "message": f"documentation contains inline link to non-existent standard name: [{link_text}](#{link_target})",
                                    "suggestion": f"Create entry '{link_target}' or remove the link",
                                }
                            )

        # Return both errors and warnings combined
        return issues + warnings
