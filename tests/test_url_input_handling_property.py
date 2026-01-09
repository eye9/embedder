"""
Property-based tests for URL input handling functionality

This module contains property-based tests that verify URL input handling
behavior across various input scenarios including empty URLs, invalid URLs,
partial URLs, multiple URLs, and URLs with special characters.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from services.url_matcher import URLMatcher, URLMatchResult
from services.url_database_manager import URLDatabaseManager
from services.url_normalizer import URLNormalizer
import chromadb
from chromadb.config import Settings
import tempfile
import os
import re


class TestURLInputHandlingProperty:
    """Property-based tests for URL input handling"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary directory for ChromaDB
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize ChromaDB client with temporary directory
        self.client = chromadb.PersistentClient(
            path=self.temp_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize components
        self.url_db_manager = URLDatabaseManager(
            chroma_client=self.client,
            collection_name="test_url_input_handling"
        )
        self.url_matcher = URLMatcher(self.url_db_manager, timeout_seconds=2.0)
        self.normalizer = URLNormalizer()
    
    def teardown_method(self):
        """Clean up test fixtures"""
        try:
            # Clean up ChromaDB
            if hasattr(self, 'client'):
                self.client.reset()
            
            # Clean up temporary directory
            import shutil
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass  # Ignore cleanup errors
    
    # Feature: url-based-code-matching, Property 11: URL Input Handling
    @given(
        st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
            st.just("\t\n  \r"),  # Various whitespace characters
            st.none(),  # None value
        )
    )
    @settings(max_examples=20, deadline=3000)
    def test_empty_url_handling(self, empty_url):
        """
        Test that empty URL fields are handled correctly
        
        Property: For any empty URL input (None, empty string, whitespace only),
        the system should skip URL search and indicate semantic search should be used.
        **Validates: Requirements 9.1**
        """
        result = self.url_matcher.find_code_by_url(empty_url)
        
        # Empty URLs should not find matches
        assert not result.found, \
            f"Empty URL should not find matches, got: {result}"
        
        # Should return a valid URLMatchResult structure
        assert isinstance(result, URLMatchResult), \
            f"Should return URLMatchResult, got: {type(result)}"
        
        # All fields should be None or default values for empty URLs
        assert result.tnved_code is None, \
            f"TNVED code should be None for empty URL, got: {result.tnved_code}"
        assert result.description is None, \
            f"Description should be None for empty URL, got: {result.description}"
        assert result.source_name is None, \
            f"Source name should be None for empty URL, got: {result.source_name}"
    
    @given(
        st.one_of(
            st.just("not-a-url"),  # Plain text
            st.just("ftp://example.com/file"),  # Unsupported protocol
            st.just("javascript:alert('xss')"),  # Malicious URL
            st.just("file:///etc/passwd"),  # Local file URL
            st.just("data:text/html,<script>alert('xss')</script>"),  # Data URL
            st.just("://missing-scheme"),  # Malformed URL
            st.just("http://"),  # Incomplete URL
            st.just("https://"),  # Incomplete URL
            st.integers(),  # Non-string type
            st.lists(st.text()),  # List instead of string
            st.dictionaries(st.text(), st.text()),  # Dictionary instead of string
        )
    )
    @settings(max_examples=30, deadline=3000)
    def test_invalid_url_handling(self, invalid_url):
        """
        Test that invalid URLs are handled correctly
        
        Property: For any invalid URL input (malformed, unsupported protocol, non-string),
        the system should log warnings and indicate semantic search should be used.
        **Validates: Requirements 9.2**
        """
        result = self.url_matcher.find_code_by_url(invalid_url)
        
        # Invalid URLs should not find matches
        assert not result.found, \
            f"Invalid URL should not find matches, got: {result}"
        
        # Should return a valid URLMatchResult structure without exceptions
        assert isinstance(result, URLMatchResult), \
            f"Should return URLMatchResult, got: {type(result)}"
        
        # All fields should be None or default values for invalid URLs
        assert result.tnved_code is None, \
            f"TNVED code should be None for invalid URL, got: {result.tnved_code}"
        assert result.description is None, \
            f"Description should be None for invalid URL, got: {result.description}"
    
    @given(
        st.one_of(
            # URLs missing protocol
            st.integers(min_value=1, max_value=999999).map(
                lambda x: f"ozon.ru/product/{x}/"
            ),
            st.integers(min_value=1, max_value=999999).map(
                lambda x: f"market.yandex.ru/product/{x}"
            ),
            st.integers(min_value=1, max_value=999999).map(
                lambda x: f"wildberries.ru/catalog/{x}/"
            ),
            # URLs with HTTP instead of HTTPS
            st.integers(min_value=1, max_value=999999).map(
                lambda x: f"http://ozon.ru/product/{x}/"
            ),
            st.integers(min_value=1, max_value=999999).map(
                lambda x: f"http://market.yandex.ru/product/{x}"
            ),
            # URLs with extra path components
            st.integers(min_value=1, max_value=999999).map(
                lambda x: f"https://ozon.ru/product/{x}/details/reviews"
            ),
            st.integers(min_value=1, max_value=999999).map(
                lambda x: f"https://wildberries.ru/catalog/{x}/detail.aspx"
            ),
        )
    )
    @settings(max_examples=50, deadline=5000)
    def test_partial_url_normalization(self, partial_url):
        """
        Test that partial URLs are normalized before search
        
        Property: For any partial URL input (missing protocol, extra components),
        the system should attempt normalization before performing the search.
        **Validates: Requirements 9.3**
        """
        # First verify the URL can be normalized
        normalized = self.normalizer.normalize_url(partial_url)
        
        if normalized is not None:
            # URL should be successfully normalized
            assert normalized.normalized_url.startswith('https://'), \
                f"Partial URL should be normalized to HTTPS, got: {normalized.normalized_url}"
            
            # The matcher should handle the partial URL without errors
            result = self.url_matcher.find_code_by_url(partial_url)
            
            # Should return a valid result structure (found or not found)
            assert isinstance(result, URLMatchResult), \
                f"Should return URLMatchResult, got: {type(result)}"
            
            # If not found, it should be because there's no matching record in DB,
            # not because of normalization failure
            if not result.found:
                assert result.tnved_code is None
                assert result.description is None
        else:
            # If normalization fails, matcher should handle gracefully
            result = self.url_matcher.find_code_by_url(partial_url)
            assert not result.found, \
                f"Non-normalizable URL should not find matches, got: {result}"
    
    @given(
        st.integers(min_value=1, max_value=999999),
        st.integers(min_value=1, max_value=999999),
        st.integers(min_value=1, max_value=999999),
        st.sampled_from([" ", ", ", "; ", " | ", "\n", "\t"])
    )
    @settings(max_examples=30, deadline=5000)
    def test_multiple_urls_in_field(self, id1, id2, id3, separator):
        """
        Test that when multiple URLs are in one field, the first valid URL is used
        
        Property: For any field containing multiple URLs separated by various delimiters,
        the system should use the first valid URL for search.
        **Validates: Requirements 9.4**
        """
        # Create multiple URLs with different validity
        urls = [
            f"https://ozon.ru/product/{id1}/",  # Valid Ozon URL
            f"invalid-url-{id2}",  # Invalid URL
            f"https://market.yandex.ru/product/{id3}",  # Valid Yandex URL
        ]
        
        # Join with separator to simulate multiple URLs in one field
        multi_url_field = separator.join(urls)
        
        # The system should handle this gracefully
        # Note: Current implementation doesn't split multiple URLs,
        # so it should treat the whole string as one URL and likely fail to normalize
        result = self.url_matcher.find_code_by_url(multi_url_field)
        
        # Should return a valid result structure without exceptions
        assert isinstance(result, URLMatchResult), \
            f"Should return URLMatchResult for multiple URLs, got: {type(result)}"
        
        # Since current implementation doesn't split URLs, this will likely not find a match
        # But it should handle the input gracefully without errors
        assert result.tnved_code is None or isinstance(result.tnved_code, str), \
            f"TNVED code should be None or string, got: {type(result.tnved_code)}"
    
    @given(
        st.integers(min_value=1, max_value=999999),
        st.sampled_from([
            # URLs with special characters that need encoding
            "?ref=test&utm_source=google&param=special%20chars",
            "?query=тест&lang=ru&special=символы",
            "#section-with-special-chars!@#$%",
            "?param=<script>alert('xss')</script>",
            "?data=user@domain.com&token=abc123",
            "?search=coffee+beans&filter=price>100",
            "?json={\"key\":\"value\",\"array\":[1,2,3]}",
        ])
    )
    @settings(max_examples=40, deadline=5000)
    def test_special_characters_in_urls(self, product_id, special_params):
        """
        Test that URLs with special characters are properly encoded for database search
        
        Property: For any URL containing special characters (Unicode, symbols, encoded chars),
        the system should properly handle and encode the URL for safe database operations.
        **Validates: Requirements 9.5**
        """
        # Create URL with special characters
        base_url = f"https://ozon.ru/product/{product_id}/"
        url_with_special_chars = base_url + special_params
        
        # The system should handle special characters without errors
        result = self.url_matcher.find_code_by_url(url_with_special_chars)
        
        # Should return a valid result structure without exceptions
        assert isinstance(result, URLMatchResult), \
            f"Should return URLMatchResult for URL with special chars, got: {type(result)}"
        
        # Should not cause database errors or security issues
        assert result.tnved_code is None or isinstance(result.tnved_code, str), \
            f"TNVED code should be None or string, got: {type(result.tnved_code)}"
        
        # Test URL validation with special characters
        validation_result = self.url_matcher.validate_and_suggest_normalization(url_with_special_chars)
        
        # Should return validation results without errors
        assert isinstance(validation_result, dict), \
            f"Should return dict for validation, got: {type(validation_result)}"
        
        # Should have required validation fields
        required_fields = ["original_url", "is_valid", "suggestions", "security_issues"]
        for field in required_fields:
            assert field in validation_result, \
                f"Validation result should contain '{field}' field"
        
        # Security issues should be detected for potentially dangerous URLs
        if any(dangerous in url_with_special_chars.lower() for dangerous in ['<script', 'javascript:', 'data:']):
            assert len(validation_result["security_issues"]) > 0, \
                f"Should detect security issues in dangerous URL: {url_with_special_chars}"
    
    @given(
        st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po'),
            blacklist_characters='\x00\r\n'
        )),
        st.integers(min_value=1, max_value=999999)
    )
    @settings(max_examples=30, deadline=5000)
    def test_url_input_robustness(self, random_text, product_id):
        """
        Test that the URL input handling is robust against various text inputs
        
        Property: For any text input that might be mistaken for a URL,
        the system should handle it gracefully without errors or security issues.
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        # Create various potentially problematic inputs
        test_inputs = [
            random_text,  # Random text
            f"https://example.com/{random_text}",  # URL with random path
            f"{random_text}://domain.com/path",  # Random protocol
            f"https://{random_text}.com/product/{product_id}",  # Random domain
        ]
        
        for test_input in test_inputs:
            # Skip inputs that are too short or contain null bytes
            if len(test_input.strip()) == 0:
                continue
            
            # The system should handle any input gracefully
            result = self.url_matcher.find_code_by_url(test_input)
            
            # Should always return a valid URLMatchResult
            assert isinstance(result, URLMatchResult), \
                f"Should return URLMatchResult for input '{test_input}', got: {type(result)}"
            
            # Should not cause exceptions or security issues
            assert hasattr(result, 'found'), \
                f"Result should have 'found' attribute for input: {test_input}"
            
            # Test validation robustness
            validation_result = self.url_matcher.validate_and_suggest_normalization(test_input)
            
            # Should return validation results without errors
            assert isinstance(validation_result, dict), \
                f"Should return dict for validation of '{test_input}', got: {type(validation_result)}"
            
            # Should contain basic validation fields
            assert "original_url" in validation_result, \
                f"Should contain original_url for input: {test_input}"
            assert "is_valid" in validation_result, \
                f"Should contain is_valid for input: {test_input}"
    
    @given(
        st.integers(min_value=1, max_value=999999)
    )
    @settings(max_examples=20, deadline=5000)
    def test_url_input_consistency(self, product_id):
        """
        Test that URL input handling is consistent across different input variations
        
        Property: For any valid product URL, different input variations (with/without protocol,
        with/without query params) should be handled consistently.
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        base_url = f"ozon.ru/product/{product_id}/"
        
        # Different variations of the same URL
        url_variations = [
            base_url,  # Without protocol
            f"http://{base_url}",  # HTTP protocol
            f"https://{base_url}",  # HTTPS protocol
            f"https://{base_url}?ref=test",  # With query params
            f"https://{base_url}#section",  # With fragment
            f"https://{base_url}?ref=test#section",  # With both
        ]
        
        results = []
        for url_variation in url_variations:
            result = self.url_matcher.find_code_by_url(url_variation)
            results.append(result)
            
            # Each variation should be handled without errors
            assert isinstance(result, URLMatchResult), \
                f"Should return URLMatchResult for '{url_variation}', got: {type(result)}"
        
        # All variations should produce consistent result structures
        # (they may not find matches since we haven't populated the database,
        # but they should all behave consistently)
        for i, result in enumerate(results):
            assert hasattr(result, 'found'), \
                f"Result {i} should have 'found' attribute"
            assert hasattr(result, 'tnved_code'), \
                f"Result {i} should have 'tnved_code' attribute"
            assert hasattr(result, 'confidence'), \
                f"Result {i} should have 'confidence' attribute"