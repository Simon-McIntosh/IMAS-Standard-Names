"""Tests for vocabulary token validation rules."""

import pytest

from imas_standard_names.vocabulary.editor import VocabularyEditor


class TestTokenValidation:
    """Test token validation rules."""

    @pytest.fixture
    def editor(self):
        """Create editor instance."""
        return VocabularyEditor()

    def test_valid_simple_tokens(self, editor):
        """Test valid simple tokens."""
        valid_tokens = [
            "a",
            "z",
            "electron",
            "ion",
            "radial",
            "toroidal",
            "flux_loop",
            "magnetic_axis",
            "ion_cyclotron_heating_antenna",
        ]
        for token in valid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert is_valid, f"Token '{token}' should be valid but got: {error}"
            assert error is None

    def test_valid_tokens_with_numbers(self, editor):
        """Test valid tokens containing numbers."""
        valid_tokens = [
            "h1",
            "h2o",
            "test1",
            "token2test",
            "version3final",
        ]
        for token in valid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert is_valid, f"Token '{token}' should be valid but got: {error}"

    def test_invalid_uppercase(self, editor):
        """Test rejection of uppercase letters."""
        invalid_tokens = [
            "Electron",
            "ELECTRON",
            "eLectron",
            "electron_Temperature",
        ]
        for token in invalid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert not is_valid, f"Token '{token}' should be invalid"
            assert "lowercase" in error.lower()

    def test_invalid_leading_underscore(self, editor):
        """Test rejection of leading underscore."""
        invalid_tokens = ["_electron", "_test", "_x"]
        for token in invalid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert not is_valid, f"Token '{token}' should be invalid"
            assert "leading" in error.lower() or "pattern" in error.lower()

    def test_invalid_trailing_underscore(self, editor):
        """Test rejection of trailing underscore."""
        invalid_tokens = ["electron_", "test_", "x_"]
        for token in invalid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert not is_valid, f"Token '{token}' should be invalid"
            assert "underscore" in error.lower() or "pattern" in error.lower()

    def test_invalid_double_underscore(self, editor):
        """Test rejection of double underscores."""
        invalid_tokens = ["electron__temperature", "test__token", "x__y"]
        for token in invalid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert not is_valid, f"Token '{token}' should be invalid"
            assert "double underscore" in error.lower()

    def test_invalid_purely_numeric_segment(self, editor):
        """Test rejection of purely numeric segments."""
        invalid_tokens = ["test_123_token", "x_42_y", "version_3_final"]
        for token in invalid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert not is_valid, f"Token '{token}' should be invalid"
            assert "numeric segment" in error.lower()

    def test_invalid_special_characters(self, editor):
        """Test rejection of special characters."""
        invalid_tokens = [
            "electron-temperature",
            "test.token",
            "x@y",
            "token!",
            "test token",
            "x&y",
        ]
        for token in invalid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert not is_valid, f"Token '{token}' should be invalid"

    def test_invalid_starting_with_number(self, editor):
        """Test rejection of tokens starting with number."""
        invalid_tokens = ["1electron", "2test", "3x"]
        for token in invalid_tokens:
            is_valid, error = editor.validate_token(token, "components")
            assert not is_valid, f"Token '{token}' should be invalid"
            assert "pattern" in error.lower() or "start with letter" in error.lower()

    def test_add_tokens_with_invalid_format(self, editor):
        """Test that add_tokens rejects invalid tokens."""
        with pytest.raises(ValueError, match="Token validation failed"):
            editor.add_tokens("components", ["Invalid_Token"])

        with pytest.raises(ValueError, match="Token validation failed"):
            editor.add_tokens("components", ["token__double"])

        with pytest.raises(ValueError, match="Token validation failed"):
            editor.add_tokens("components", ["_leading"])

    def test_add_tokens_mixed_valid_invalid(self, editor):
        """Test that add_tokens rejects batch if any token is invalid."""
        # Should fail entire batch if one token is invalid
        with pytest.raises(ValueError, match="Token validation failed"):
            editor.add_tokens(
                "components", ["valid_token", "Invalid_Token", "another_valid"]
            )

    def test_validation_error_messages_informative(self, editor):
        """Test that validation errors provide helpful messages."""
        # Uppercase
        is_valid, error = editor.validate_token("BadToken", "components")
        assert not is_valid
        assert "lowercase" in error.lower()
        assert "BadToken" in error

        # Double underscore
        is_valid, error = editor.validate_token("bad__token", "components")
        assert not is_valid
        assert "double underscore" in error.lower()
        assert "bad__token" in error

        # Trailing underscore
        is_valid, error = editor.validate_token("token_", "components")
        assert not is_valid
        assert "underscore" in error.lower() or "pattern" in error.lower()

    def test_edge_cases(self, editor):
        """Test edge cases for token validation."""
        # Single letter - valid
        is_valid, error = editor.validate_token("a", "components")
        assert is_valid

        # Empty string - invalid
        is_valid, error = editor.validate_token("", "components")
        assert not is_valid

        # Very long token - valid if format is correct
        long_token = "very_long_token_name_with_many_underscores_and_letters"
        is_valid, error = editor.validate_token(long_token, "components")
        assert is_valid

        # Token with consecutive valid characters
        is_valid, error = editor.validate_token("abc123def456", "components")
        assert is_valid


class TestVocabularySpecificRules:
    """Test vocabulary-specific validation rules (future expansion)."""

    @pytest.fixture
    def editor(self):
        """Create editor instance."""
        return VocabularyEditor()

    def test_all_vocabularies_accept_valid_tokens(self, editor):
        """Test that all vocabularies accept properly formatted tokens."""
        valid_token = "test_token"
        vocabularies = [
            "components",
            "subjects",
            "geometric_bases",
            "objects",
            "positions",
            "processes",
        ]

        for vocab in vocabularies:
            is_valid, error = editor.validate_token(valid_token, vocab)
            assert is_valid, f"Valid token should be accepted by {vocab}: {error}"
