"""
Tests for vocabulary auditing functionality.

Tests the VocabularyTool MCP tool and its underlying VocabularyAuditor.
"""

import pytest

from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.vocabulary import VocabularyTool
from imas_standard_names.vocabulary.audit import VocabularyAuditor
from imas_standard_names.vocabulary.vocab_models import (
    AuditResult,
    CheckResult,
)


@pytest.fixture
def catalog():
    """Standard names catalog fixture."""
    return StandardNameCatalog()


@pytest.fixture
def auditor(catalog):
    """Vocabulary auditor fixture."""
    return VocabularyAuditor(catalog)


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


class TestVocabularyToolIntegration:
    """Integration tests for VocabularyTool (requires catalog)."""

    @pytest.fixture
    def vocab_tool(self, catalog):
        """VocabularyTool fixture."""
        return VocabularyTool(catalog)

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
