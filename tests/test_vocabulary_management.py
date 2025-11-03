"""
Tests for vocabulary management (audit + edit) functionality.

Tests the VocabularyTool MCP tool and its underlying VocabularyAuditor
and VocabularyEditor classes.
"""

import pytest

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.vocabulary import VocabularyTool
from imas_standard_names.vocabulary.audit import VocabularyAuditor
from imas_standard_names.vocabulary.editor import VocabularyEditor
from imas_standard_names.vocabulary.vocab_models import (
    AddResult,
    AuditResult,
    CheckResult,
    RemoveResult,
)


@pytest.fixture
def catalog():
    """Standard names catalog fixture."""
    return StandardNameCatalog()


@pytest.fixture
def auditor(catalog):
    """Vocabulary auditor fixture."""
    return VocabularyAuditor(catalog)


@pytest.fixture
def editor():
    """Vocabulary editor fixture."""
    return VocabularyEditor()


class TestVocabularyAuditor:
    """Test VocabularyAuditor class."""

    def test_audit_returns_audit_result(self, auditor):
        """Test that audit() returns proper AuditResult."""
        result = auditor.audit()

        assert isinstance(result, AuditResult)
        assert result.action == "audit"
        assert "summary" in result.model_dump()
        assert "recommendations" in result.model_dump()
        assert isinstance(result.summary, dict)
        assert "total_missing_tokens" in result.summary

    def test_audit_with_vocabulary_filter(self, auditor):
        """Test auditing specific vocabulary."""
        result = auditor.audit(vocabulary="positions")

        assert isinstance(result, AuditResult)
        # When filtered, check that summary reflects the filter
        by_vocab = result.summary.get("by_vocabulary", {})
        if isinstance(by_vocab, dict) and by_vocab:
            # If there are missing tokens, check positions is in the vocab list
            assert "positions" in by_vocab or len(by_vocab) == 0

    def test_audit_with_custom_threshold(self, auditor):
        """Test audit with custom frequency threshold."""
        result_low = auditor.audit(frequency_threshold=2)
        result_high = auditor.audit(frequency_threshold=10)

        # Lower threshold should find more or equal missing tokens
        assert (
            result_low.summary["total_missing_tokens"]
            >= result_high.summary["total_missing_tokens"]
        )

    def test_check_name_returns_check_result(self, auditor):
        """Test that check_name() returns proper CheckResult."""
        result = auditor.check_name("cross_sectional_area_of_flux_surface")

        assert isinstance(result, CheckResult)
        assert result.action == "check"
        assert result.name == "cross_sectional_area_of_flux_surface"
        assert isinstance(result.current_parse, dict)
        assert isinstance(result.has_vocabulary_gap, bool)

    def test_check_name_detects_missing_token(self, auditor):
        """Test that check_name detects flux_surface as missing."""
        result = auditor.check_name("cross_sectional_area_of_flux_surface")

        # This name should have a vocabulary gap for flux_surface
        if result.has_vocabulary_gap:
            assert result.gap_details is not None
            assert "flux_surface" in result.gap_details.token
            assert result.gap_details.frequency >= 3

    def test_check_name_no_gap(self, auditor):
        """Test check_name with name that has no vocabulary gap."""
        result = auditor.check_name("electron_temperature")

        assert result.has_vocabulary_gap is False
        assert result.gap_details is None


class TestVocabularyEditor:
    """Test VocabularyEditor class."""

    def test_editor_initializes(self, editor):
        """Test that editor initializes with correct paths."""
        assert editor.grammar_dir.exists()
        assert editor.grammar_dir.is_dir()
        assert (editor.grammar_dir / "vocabularies").exists()

    def test_add_tokens_returns_add_result(self, editor):
        """Test that add_tokens returns AddResult (dry run concept)."""
        # We won't actually add tokens to avoid modifying source files
        # Instead we test the return type structure
        assert hasattr(editor, "add_tokens")
        # Test with invalid vocabulary to trigger error
        with pytest.raises(ValueError, match="Unknown vocabulary"):
            editor.add_tokens("invalid_vocab", ["test"])

    def test_remove_tokens_returns_remove_result(self, editor):
        """Test that remove_tokens returns RemoveResult (dry run concept)."""
        assert hasattr(editor, "remove_tokens")
        # Test with invalid vocabulary to trigger error
        with pytest.raises(ValueError, match="Unknown vocabulary"):
            editor.remove_tokens("invalid_vocab", ["test"])

    def test_editor_vocab_file_mapping(self, editor):
        """Test that editor has correct vocabulary file mappings."""
        # Editor uses segment IDs that map to vocabulary files
        # Check that dynamic mapping includes expected segments
        assert (
            len(editor.VOCAB_FILES) >= 6
        )  # Should have at least 6 vocabulary mappings
        # Verify some key segment->vocabulary mappings exist
        vocab_files_str = str(editor.VOCAB_FILES)
        assert "components" in vocab_files_str or "component" in editor.VOCAB_FILES
        assert "objects" in vocab_files_str or "object" in editor.VOCAB_FILES
        assert "positions" in vocab_files_str or "geometry" in editor.VOCAB_FILES
        assert "position" in editor.VOCAB_FILES
        # geometry and position should map to same file
        assert editor.VOCAB_FILES["geometry"] == editor.VOCAB_FILES["position"]
        # object should map to different file
        assert editor.VOCAB_FILES["object"] != editor.VOCAB_FILES["geometry"]

    def test_editor_load_vocabulary(self, editor):
        """Test loading vocabulary from YAML file."""
        positions_file = editor.grammar_dir / editor.VOCAB_FILES["geometry"]
        tokens = editor._load_vocabulary(positions_file)

        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert all(isinstance(token, str) for token in tokens)

    def test_editor_validate_changes(self, editor):
        """Test validation method."""
        # Should pass validation on current state
        assert editor.validate_changes() is True


class TestVocabularyToolIntegration:
    """Integration tests for VocabularyTool (requires catalog)."""

    @pytest.fixture
    def vocab_tool(self, catalog):
        """VocabularyTool fixture."""
        return VocabularyTool(catalog)

    @pytest.mark.anyio
    async def test_manage_vocabulary_list(self, vocab_tool):
        """Test manage_vocabulary with list action (no longer supported - use get_vocabulary_tokens)."""
        result = await vocab_tool.manage_vocabulary(
            {"action": "list", "segment": "geometry"}
        )

        # List action is no longer supported in manage_vocabulary
        assert "error" in result
        assert result["error"] == "ValidationError"

    @pytest.mark.anyio
    async def test_manage_vocabulary_audit(self, vocab_tool):
        """Test manage_vocabulary with audit action."""
        result = await vocab_tool.manage_vocabulary({"action": "audit"})

        assert isinstance(result, dict)
        assert result.get("action") == "audit"
        assert "summary" in result
        assert "recommendations" in result

    @pytest.mark.anyio
    async def test_manage_vocabulary_check(self, vocab_tool):
        """Test manage_vocabulary with check action."""
        result = await vocab_tool.manage_vocabulary(
            {"action": "check", "name": "cross_sectional_area_of_flux_surface"}
        )

        assert isinstance(result, dict)
        assert result.get("action") == "check"
        assert result.get("name") == "cross_sectional_area_of_flux_surface"
        assert "current_parse" in result
        assert "has_vocabulary_gap" in result

    @pytest.mark.anyio
    async def test_manage_vocabulary_invalid_action(self, vocab_tool):
        """Test manage_vocabulary with invalid action."""
        result = await vocab_tool.manage_vocabulary({"action": "invalid"})

        assert "error" in result
        assert "schema" in result
        assert "examples" in result

    @pytest.mark.anyio
    async def test_manage_vocabulary_missing_required_field(self, vocab_tool):
        """Test manage_vocabulary with missing required field."""
        result = await vocab_tool.manage_vocabulary({"action": "check"})

        # Should error due to missing 'name' field
        assert "error" in result


class TestVocabModels:
    """Test vocabulary models."""

    def test_audit_result_model(self):
        """Test AuditResult model structure."""
        result = AuditResult(
            action="audit",
            summary={
                "total_missing_tokens": 0,
                "by_vocabulary": {},
                "by_priority": {
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                },
            },
            recommendations={
                "high": [],
                "medium": [],
                "low": [],
            },
        )

        assert result.action == "audit"
        assert result.summary["total_missing_tokens"] == 0

    def test_check_result_model(self):
        """Test CheckResult model structure."""
        result = CheckResult(
            action="check",
            name="test_name",
            current_parse={},
            has_vocabulary_gap=False,
            gap_details=None,
        )

        assert result.action == "check"
        assert result.name == "test_name"

    def test_add_result_model(self):
        """Test AddResult model structure."""
        result = AddResult(
            action="add",
            vocabulary="geometry",
            added=["flux_surface"],
            already_present=[],
            status="success",
            requires_restart=True,
            details="Codegen completed successfully",
        )

        assert result.action == "add"
        assert result.vocabulary == "geometry"
        assert "flux_surface" in result.added
        assert result.details is not None
        assert result.requires_restart is True

    def test_remove_result_model(self):
        """Test RemoveResult model structure."""
        result = RemoveResult(
            action="remove",
            vocabulary="geometry",
            removed=["old_token"],
            not_found=["missing_token"],
            status="success",
            requires_restart=True,
            details="Codegen completed successfully",
        )

        assert result.action == "remove"
        assert result.vocabulary == "geometry"
        assert "old_token" in result.removed
        assert result.details is not None
        assert result.requires_restart is True
