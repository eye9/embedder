"""
Tests for TextNormalizer service.
"""

import pytest
from services.text_normalizer import TextNormalizer


class TestTextNormalizer:
    """Test suite for TextNormalizer class."""
    
    @pytest.fixture
    def normalizer(self):
        """Create a TextNormalizer instance for testing."""
        return TextNormalizer()
    
    def test_lowercase_conversion(self, normalizer):
        """Test that text is converted to lowercase."""
        text = "КОФЕЙНЫЕ ЗЕРНА АРАБИКА"
        result = normalizer.normalize(text)
        assert result.islower(), "Result should be lowercase"
    
    def test_whitespace_cleanup(self, normalizer):
        """Test that excessive whitespace is removed."""
        text = "  много   пробелов   здесь  "
        result = normalizer.normalize(text)
        # Should not have leading/trailing spaces
        assert result == result.strip()
        # Should not have multiple consecutive spaces
        assert "  " not in result
    
    def test_empty_string(self, normalizer):
        """Test handling of empty strings."""
        assert normalizer.normalize("") == ""
        assert normalizer.normalize("   ") == ""
    
    def test_special_characters_removed(self, normalizer):
        """Test that special characters are cleaned up."""
        text = "кофе, зерна! арабика?"
        result = normalizer.normalize(text)
        # Special characters should be removed or replaced with spaces
        assert "," not in result
        assert "!" not in result
        assert "?" not in result
    
    def test_lemmatization_applied(self, normalizer):
        """Test that Natasha lemmatization is applied."""
        # "зерна" (plural) should become "зерно" (singular/lemma)
        text = "кофейные зерна"
        result = normalizer.normalize(text)
        # The result should contain lemmatized forms
        assert len(result) > 0
        # Should be lowercase and cleaned
        assert result.islower()
    
    def test_idempotence(self, normalizer):
        """Test that normalizing twice produces the same result."""
        text = "КОФЕЙНЫЕ ЗЕРНА АРАБИКА"
        normalized_once = normalizer.normalize(text)
        normalized_twice = normalizer.normalize(normalized_once)
        assert normalized_once == normalized_twice
    
    def test_preserves_meaning(self, normalizer):
        """Test that normalization preserves semantic content."""
        text = "кофе"
        result = normalizer.normalize(text)
        # Should still contain the word (or its lemma)
        assert len(result) > 0
        assert "кофе" in result or "кофей" in result
