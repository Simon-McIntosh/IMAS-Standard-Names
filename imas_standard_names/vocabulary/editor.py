"""Vocabulary editor for adding/removing tokens from grammar vocabularies.

Vocabulary Workflow:
    1. Edit vocabulary YAML files via add_tokens() or remove_tokens()
       - Automatic codegen runs after successful edits
    2. Check validation_status in result:
       - 'codegen_success_restart_required': Success, restart MCP server
       - 'codegen_failed': Check message for error details
       - 'no_changes': No tokens were added/removed

Supported Vocabularies (all canonical grammar segments):
    - components: Directional/coordinate components (radial, toroidal, poloidal)
    - subjects: Particle species (electron, ion, deuterium, tritium)
    - geometric_bases: Spatial quantities (position, vertex, centroid, area)
    - objects: Physical hardware (flux_loop, antenna, coil, limiter)
    - positions: Spatial locations (magnetic_axis, separatrix, midplane)
    - processes: Physical mechanisms (collisions, turbulence, transport)

Vocabulary files are stored in package source (imas_standard_names/grammar/vocabularies/)
and used to generate grammar.types enums (Component, Subject, GeometricBase, Object,
Position, Process) via codegen.

Important: After successful vocabulary changes, the MCP server must be restarted
          to load the updated grammar.types enums. Hot-reload is not supported.

Note: tags.yml is NOT managed by this tool - it's managed separately via catalog entry metadata.
"""

from __future__ import annotations

import importlib.resources as ir
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from imas_standard_names.grammar_codegen.spec import GrammarSpec
from imas_standard_names.vocabulary.vocab_models import AddResult, RemoveResult

if TYPE_CHECKING:
    pass


# Token validation pattern: lowercase letters, digits, underscores
# Must start with letter, no leading/trailing underscores, no double underscores
TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9_]*[a-z0-9]$|^[a-z]$")


def _build_vocab_file_map() -> dict[str, str]:
    """Derive vocabulary file mapping from grammar specification.

    Returns segment_id -> relative_path mapping derived from specification.yml
    (e.g., 'geometry' -> 'vocabularies/positions.yml')
    """
    spec = GrammarSpec.load()
    mapping = {}
    for segment in spec.segments:
        if segment.vocabulary_name:
            mapping[segment.identifier] = f"vocabularies/{segment.vocabulary_name}.yml"
    return mapping


def _build_vocab_name_to_segment_map() -> dict[str, list[str]]:
    """Build mapping from vocabulary names to segment IDs that use them.

    Returns vocabulary_name -> [segment_ids] mapping
    (e.g., 'components' -> ['component', 'coordinate'])
    """
    spec = GrammarSpec.load()
    mapping: dict[str, list[str]] = {}
    for segment in spec.segments:
        if segment.vocabulary_name:
            if segment.vocabulary_name not in mapping:
                mapping[segment.vocabulary_name] = []
            mapping[segment.vocabulary_name].append(segment.identifier)
    return mapping


class VocabularyEditor:
    """Edits grammar vocabulary YAML files in the package source."""

    # Dynamically build vocabulary file mapping from grammar specification
    # instead of hardcoding segment->file relationships
    VOCAB_FILES = _build_vocab_file_map()

    # Mapping from vocabulary names to segment IDs for public API
    VOCAB_NAME_TO_SEGMENTS = _build_vocab_name_to_segment_map()

    def __init__(self) -> None:
        """Initialize the vocabulary editor.

        Uses importlib.resources to resolve the grammar directory path,
        ensuring compatibility with all Python packaging methods.
        """
        grammar_files = ir.files("imas_standard_names.grammar")
        with ir.as_file(grammar_files) as grammar_path:
            self.grammar_dir = Path(grammar_path)

    def validate_token(self, token: str, vocabulary: str) -> tuple[bool, str | None]:
        """Validate token against grammar rules.

        Checks:
        1. Format: lowercase, underscores, no leading/trailing underscores
        2. Pattern: ^[a-z][a-z0-9_]*[a-z0-9]$ or single letter
        3. No double underscores
        4. No purely numeric segments between underscores

        Args:
            token: Token to validate
            vocabulary: Vocabulary name (for context in error messages)

        Returns:
            (is_valid, error_message) tuple
        """
        # Check basic pattern
        if not TOKEN_PATTERN.match(token):
            return False, (
                f"Token '{token}' must be lowercase letters, digits, and underscores. "
                "Must start with letter and not end with underscore. "
                "Pattern: ^[a-z][a-z0-9_]*[a-z0-9]$"
            )

        # Check for double underscores
        if "__" in token:
            return False, f"Token '{token}' contains double underscores (not allowed)"

        # Check for purely numeric segments
        segments = token.split("_")
        for segment in segments:
            if segment.isdigit():
                return False, (
                    f"Token '{token}' has purely numeric segment '{segment}' "
                    "(must contain at least one letter)"
                )

        # Check for reserved/problematic patterns
        if token.startswith("_") or token.endswith("_"):
            return (
                False,
                f"Token '{token}' has leading or trailing underscore (not allowed)",
            )

        return True, None

    def add_tokens(self, vocabulary: str, tokens: list[str]) -> AddResult:
        """
        Add tokens to vocabulary with comprehensive validation.

        Args:
            vocabulary: Which vocabulary to edit (components, subjects, geometric_bases,
                       objects, positions, processes)
            tokens: List of tokens to add

        Returns:
            AddResult with lists of added and already-present tokens

        Raises:
            ValueError: If vocabulary is unknown or tokens fail validation
        """
        # Accept both vocabulary names and segment IDs
        if (
            vocabulary not in self.VOCAB_NAME_TO_SEGMENTS
            and vocabulary not in self.VOCAB_FILES
        ):
            raise ValueError(
                f"Unknown vocabulary: {vocabulary}. Must be one of: "
                f"{list(self.VOCAB_NAME_TO_SEGMENTS.keys())} or segment IDs: {list(self.VOCAB_FILES.keys())}"
            )

        # Resolve vocabulary name to a segment ID (use first one if multiple)
        segment_id = vocabulary
        if vocabulary in self.VOCAB_NAME_TO_SEGMENTS:
            segment_id = self.VOCAB_NAME_TO_SEGMENTS[vocabulary][0]

        # Validate all tokens first
        validation_errors = []
        for token in tokens:
            is_valid, error = self.validate_token(token, vocabulary)
            if not is_valid:
                validation_errors.append(error)

        if validation_errors:
            raise ValueError(
                f"Token validation failed for {vocabulary}:\n"
                + "\n".join(validation_errors)
            )

        vocab_file = self.grammar_dir / self.VOCAB_FILES[segment_id]

        # Load current vocabulary
        current_tokens = self._load_vocabulary(vocab_file)

        # Identify which tokens to add
        added = []
        already_present = []

        for token in tokens:
            if token in current_tokens:
                already_present.append(token)
            else:
                current_tokens.append(token)
                added.append(token)

        # Write back if changes were made
        if added:
            self._save_vocabulary(vocab_file, current_tokens)
            if self.validate_changes():
                codegen_result = self._run_codegen()
                codegen_status = codegen_result.get("status")

                if codegen_status == "codegen_success_restart_required":
                    status = "success"
                    requires_restart = True
                    details = codegen_result.get("message")
                else:
                    status = "failed"
                    requires_restart = False
                    details = codegen_result.get("message", "Codegen failed")
            else:
                status = "failed"
                requires_restart = False
                details = "Validation failed"
        else:
            status = "unchanged"
            requires_restart = False
            details = "All tokens already present in vocabulary"

        return AddResult(
            action="add",
            vocabulary=vocabulary,
            added=added,
            already_present=already_present,
            status=status,
            requires_restart=requires_restart,
            details=details,
        )

    def remove_tokens(self, vocabulary: str, tokens: list[str]) -> RemoveResult:
        """
        Remove tokens from vocabulary with validation.

        Args:
            vocabulary: Which vocabulary to edit (components, subjects, geometric_bases,
                       objects, positions, processes)
            tokens: List of tokens to remove

        Returns:
            RemoveResult with lists of removed and not-found tokens

        Raises:
            ValueError: If vocabulary is unknown
        """
        # Accept both vocabulary names and segment IDs
        if (
            vocabulary not in self.VOCAB_NAME_TO_SEGMENTS
            and vocabulary not in self.VOCAB_FILES
        ):
            raise ValueError(
                f"Unknown vocabulary: {vocabulary}. Must be one of: "
                f"{list(self.VOCAB_NAME_TO_SEGMENTS.keys())} or segment IDs: {list(self.VOCAB_FILES.keys())}"
            )

        # Resolve vocabulary name to a segment ID (use first one if multiple)
        segment_id = vocabulary
        if vocabulary in self.VOCAB_NAME_TO_SEGMENTS:
            segment_id = self.VOCAB_NAME_TO_SEGMENTS[vocabulary][0]

        vocab_file = self.grammar_dir / self.VOCAB_FILES[segment_id]

        # Load current vocabulary
        current_tokens = self._load_vocabulary(vocab_file)

        # Identify which tokens to remove
        removed = []
        not_found = []

        for token in tokens:
            if token in current_tokens:
                current_tokens.remove(token)
                removed.append(token)
            else:
                not_found.append(token)

        # Write back if changes were made
        if removed:
            self._save_vocabulary(vocab_file, current_tokens)
            if self.validate_changes():
                codegen_result = self._run_codegen()
                codegen_status = codegen_result.get("status")

                if codegen_status == "codegen_success_restart_required":
                    status = "success"
                    requires_restart = True
                    details = codegen_result.get("message")
                else:
                    status = "failed"
                    requires_restart = False
                    details = codegen_result.get("message", "Codegen failed")
            else:
                status = "failed"
                requires_restart = False
                details = "Validation failed"
        else:
            status = "unchanged"
            requires_restart = False
            details = "No tokens found to remove"

        return RemoveResult(
            action="remove",
            vocabulary=vocabulary,
            removed=removed,
            not_found=not_found,
            status=status,
            requires_restart=requires_restart,
            details=details,
        )

    def _load_vocabulary(self, vocab_file: Path) -> list[str]:
        """Load vocabulary tokens from YAML file."""
        if not vocab_file.exists():
            raise FileNotFoundError(f"Vocabulary file not found: {vocab_file}")

        with open(vocab_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list):
            raise ValueError(
                f"Expected vocabulary file to contain a list, got: {type(data)}"
            )

        return data

    def _save_vocabulary(self, vocab_file: Path, tokens: list[str]) -> None:
        """Save vocabulary tokens to YAML file."""
        # Read the original file to preserve comments and structure
        with open(vocab_file, encoding="utf-8") as f:
            original_content = f.read()

        # Extract header comments (everything before first list item)
        lines = original_content.split("\n")
        header_lines = []
        for line in lines:
            if line.strip().startswith("-"):
                break
            header_lines.append(line)

        # Build new content with header and sorted tokens
        new_content_lines = header_lines[:]

        # Add tokens (sorted for consistency)
        for token in sorted(tokens):
            new_content_lines.append(f"- {token}")

        new_content = "\n".join(new_content_lines) + "\n"

        # Write back
        with open(vocab_file, "w", encoding="utf-8") as f:
            f.write(new_content)

    def validate_changes(self) -> bool:
        """
        Validate that changes don't break grammar.

        Checks that files are valid YAML.
        """
        for vocab_file_path in set(self.VOCAB_FILES.values()):
            vocab_file = self.grammar_dir / vocab_file_path
            try:
                self._load_vocabulary(vocab_file)
            except Exception as e:
                raise ValueError(f"Validation failed for {vocab_file}: {e}") from e

        return True

    def _run_codegen(self) -> dict[str, str]:
        """Run grammar codegen to regenerate types.py and constants.py.

        Returns:
            Dict with status and message. Status values:
            - 'codegen_success_restart_required': Codegen succeeded, server restart needed
            - 'codegen_failed': Codegen failed, check error message
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "imas_standard_names.grammar_codegen.generate"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            return {
                "status": "codegen_success_restart_required",
                "message": (
                    "Vocabulary updated and codegen completed successfully. "
                    "IMPORTANT: Restart the MCP server to load the updated grammar types."
                ),
                "codegen_output": result.stdout,
            }
        except subprocess.CalledProcessError as e:
            return {
                "status": "codegen_failed",
                "message": f"Codegen failed: {e.stderr}",
                "error": str(e),
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "codegen_failed",
                "message": "Codegen timed out after 30 seconds",
            }
        except Exception as e:
            return {
                "status": "codegen_failed",
                "message": f"Unexpected error running codegen: {e}",
            }
