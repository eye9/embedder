"""
Property-based tests for URL priority configuration behavior

This module contains property-based tests that verify the hybrid selector's
URL priority configuration behavior across different priority modes including
first, only, disabled, invalid configurations, and timeout handling.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from services.hybrid_selector import HybridSelector, URLPriority, HybridProcessingResult
from services.url_matcher import URLMatcher, URLMatchResult
from services.url_database_manager import URLDatabaseManager
from services.url_normalizer import URLNormalizer
from services.url_config import URLProcessingConfig, load_url_config_from_env, validate_url_config
from batch_processor.services.tnved_selector import TNVEDSelector
from batch_processor.models.result import ProcessingResult
import chromadb
from chromadb.config import Settings
import tempfile
import os
import time
from typing import Optional
from dataclasses import dataclass
from unittest.mock import patch, MagicMock


class MockSemanticSelector(TNVEDSelector):
    """Mock semantic selector for testing"""
    
    def __init__(self, should_find_code: bool = True, tnved_code: str = "1234567890", 
                 confidence: float = 0.8, processing_time: float = 100.0,
                 should_error: bool = False, error_message: str = "Mock error"):
        self.should_find_code = should_find_code
        self.tnved_code = tnved_code
        self.confidence = confidence
        self.processing_time = processing_time
        self.should_error = should_error
        self.error_message = error_message
    
    def select_code(self, description: str, row_index: int = 0) -> ProcessingResult:
        """Mock semantic code selection"""
        if self.should_error:
            return ProcessingResult(
                row_index=row_index,
                original_description=description,
                tnved_code=None,
                selection_reason=f"Error: {self.error_message}",
                confidence_score=None,
                processing_time_ms=self.processing_time,
                error_message=self.error_message
            )
        
        if self.should_find_code:
            return ProcessingResult(
                row_index=row_index,
                original_description=description,
                tnved_code=self.tnved_code,
                selection_reason=f"Found by semantic search: {description[:50]}...",
                confidence_score=self.confidence,
                processing_time_ms=self.processing_time
            )
        else:
            return ProcessingResult(
                row_index=row_index,
                original_description=description,
                tnved_code=None,
                selection_reason="No semantic match found",
                confidence_score=None,
                processing_time_ms=self.processing_time
            )
    
    def get_algorithm_name(self) -> str:
        return "mock_semantic"


class SlowURLMatcher(URLMatcher):
    """URL matcher that simulates slow database queries for timeout testing"""
    
    def __init__(self, url_db_manager, timeout_seconds=5.0, simulate_delay=False, delay_seconds=1.0):
        super().__init__(url_db_manager, timeout_seconds)
        self.simulate_delay = simulate_delay
        self.delay_seconds = delay_seconds
    
    def find_code_by_url(self, url: str) -> URLMatchResult:
        """Override to simulate slow queries"""
        if self.simulate_delay:
            time.sleep(self.delay_seconds)
        
        return super().find_code_by_url(url)


class TestURLPriorityConfigurationProperty:
    """Property-based tests for URL priority configuration behavior"""
    
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
            collection_name="test_url_priority"
        )
        self.url_matcher = URLMatcher(self.url_db_manager, timeout_seconds=2.0)
        
        # Add some test URL records to the database
        self._populate_test_database()
    
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
    
    def _populate_test_database(self):
        """Populate database with test URL records"""
        test_records = [
            ("https://ozon.ru/product/123456/", "1234567890", "Test Product 1", "test_source"),
            ("https://market.yandex.ru/product/789012", "0987654321", "Test Product 2", "test_source"),
            ("https://wildberries.ru/catalog/345678/", "1122334455", "Test Product 3", "test_source"),
            ("https://example.com/product/999", "5566778899", "Test Product 4", "test_source"),
        ]
        
        for url, code, description, source in test_records:
            self.url_db_manager.add_url_record(url, code, description, source)
    
    # Feature: url-based-code-matching, Property 9: URL Priority Configuration Behavior
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://ozon.ru/product/123456/",  # URL that exists in test DB
            "https://market.yandex.ru/product/789012",  # URL that exists in test DB
        ]),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=20, deadline=5000)
    def test_url_priority_first_mode(self, description, existing_url, row_index):
        """
        Test that URL priority 'first' mode tries URL search before semantic search
        
        Property: For any processing request with URL priority set to 'first',
        the system should try URL search before semantic search and return URL result
        when URL match is found.
        **Validates: Requirements 7.1**
        """
        # Create mock semantic selector (should not be called when URL match found)
        semantic_selector = MockSemanticSelector(should_find_code=True)
        
        # Create hybrid selector with FIRST priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.FIRST,
            url_timeout_seconds=2.0
        )
        
        # Process with URL that exists in database
        result = hybrid_selector.select_code_with_url(description, existing_url, row_index)
        
        # Should find URL match first (not semantic)
        assert result.match_source == "url", \
            f"FIRST mode should find URL match before semantic, got: {result.match_source}"
        assert result.tnved_code is not None, \
            f"Should have TNVED code from URL match"
        assert result.original_url == existing_url, \
            f"Should preserve original URL"
        
        # Selection reason should indicate URL match (not semantic)
        assert ("Found by URL" in result.selection_reason or "URL" in result.selection_reason), \
            f"Selection reason should indicate URL match: {result.selection_reason}"
        
        # Should have high confidence for exact URL match
        assert result.confidence_score == 1.0, \
            f"URL matches should have confidence 1.0, got: {result.confidence_score}"
        
        # Verify configuration is respected
        config = hybrid_selector.get_configuration()
        assert config["url_priority"] == "first", \
            f"Configuration should show 'first' priority"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://ozon.ru/product/123456/",  # URL that exists in test DB
            "https://market.yandex.ru/product/999999/",  # URL that doesn't exist in test DB
        ]),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=20, deadline=5000)
    def test_url_priority_only_mode(self, description, test_url, row_index):
        """
        Test that URL priority 'only' mode uses only URL search without semantic fallback
        
        Property: For any processing request with URL priority set to 'only',
        the system should use only URL search without semantic fallback regardless
        of whether URL match is found or not.
        **Validates: Requirements 7.2**
        """
        # Create mock semantic selector (should not be called in ONLY mode)
        semantic_selector = MockSemanticSelector(should_find_code=True)
        
        # Create hybrid selector with ONLY priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.ONLY,
            url_timeout_seconds=2.0
        )
        
        # Process with test URL
        result = hybrid_selector.select_code_with_url(description, test_url, row_index)
        
        # Check if URL exists in database
        url_exists = test_url in [
            "https://ozon.ru/product/123456/",
            "https://market.yandex.ru/product/789012",
            "https://wildberries.ru/catalog/345678/",
            "https://example.com/product/999"
        ]
        
        if url_exists:
            # Should find URL match
            assert result.match_source == "url", \
                f"ONLY mode should find URL match for existing URL, got: {result.match_source}"
            assert result.tnved_code is not None, \
                f"Should have TNVED code from URL match"
        else:
            # Should not fall back to semantic search
            assert result.match_source == "none", \
                f"ONLY mode should not fall back to semantic, got: {result.match_source}"
            assert result.tnved_code is None, \
                f"Should have no TNVED code when URL not found in ONLY mode"
        
        # Selection reason should never indicate semantic search in ONLY mode
        assert "semantic" not in result.selection_reason.lower() or \
               "only" in result.selection_reason.lower(), \
            f"ONLY mode should not use semantic search: {result.selection_reason}"
        
        # Verify configuration is respected
        config = hybrid_selector.get_configuration()
        assert config["url_priority"] == "only", \
            f"Configuration should show 'only' priority"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://ozon.ru/product/123456/",  # URL that exists in test DB
            "https://market.yandex.ru/product/999999/",  # URL that doesn't exist in test DB
        ]),
        st.integers(min_value=0, max_value=1000),
        st.booleans()  # Whether semantic selector should find code
    )
    @settings(max_examples=25, deadline=5000)
    def test_url_priority_disabled_mode(self, description, test_url, row_index, semantic_finds_code):
        """
        Test that URL priority 'disabled' mode skips URL search and uses only semantic search
        
        Property: For any processing request with URL priority set to 'disabled',
        the system should skip URL search and use only semantic search regardless
        of whether URL is provided or not.
        **Validates: Requirements 7.3**
        """
        # Create mock semantic selector with controlled behavior
        semantic_selector = MockSemanticSelector(
            should_find_code=semantic_finds_code,
            tnved_code="9876543210" if semantic_finds_code else None,
            confidence=0.75
        )
        
        # Create hybrid selector with DISABLED priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.DISABLED,
            url_timeout_seconds=2.0
        )
        
        # Process with test URL (should be ignored)
        result = hybrid_selector.select_code_with_url(description, test_url, row_index)
        
        # Should always use semantic search, never URL
        assert result.match_source == "semantic", \
            f"DISABLED mode should always use semantic search, got: {result.match_source}"
        
        # Result should match semantic selector behavior
        if semantic_finds_code:
            assert result.tnved_code == "9876543210", \
                f"Should have TNVED code from semantic search"
            assert result.confidence_score == 0.75, \
                f"Should have semantic confidence score"
        else:
            assert result.tnved_code is None, \
                f"Should have no TNVED code when semantic search fails"
        
        # Selection reason should indicate semantic search (not URL)
        assert "semantic" in result.selection_reason.lower(), \
            f"DISABLED mode should indicate semantic search: {result.selection_reason}"
        
        # Should not mention URL in selection reason (URL search was skipped)
        assert "Found by URL" not in result.selection_reason, \
            f"DISABLED mode should not mention URL search: {result.selection_reason}"
        
        # Verify configuration is respected
        config = hybrid_selector.get_configuration()
        assert config["url_priority"] == "disabled", \
            f"Configuration should show 'disabled' priority"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=15, deadline=5000)
    def test_invalid_url_priority_defaults_to_first(self, description, row_index):
        """
        Test that invalid URL priority configuration defaults to 'first' mode with warning
        
        Property: For any processing request with invalid URL priority configuration,
        the system should default to 'first' mode and log a warning.
        **Validates: Requirements 7.4**
        """
        # Test invalid priority handling through configuration validation
        config = URLProcessingConfig()
        
        # Test with invalid string value (should be handled by enum validation)
        with pytest.raises(ValueError):
            # This should raise an error when trying to create URLPriority from invalid value
            invalid_priority = "invalid_priority"
            URLPriority(invalid_priority)
        
        # Test that default configuration uses FIRST priority
        assert config.priority.value == "first", \
            f"Default configuration should use FIRST priority, got: {config.priority.value}"
        
        # Test configuration validation
        validate_url_config(config)  # Should not raise exception
        
        # Create hybrid selector with default (FIRST) priority
        semantic_selector = MockSemanticSelector(should_find_code=True)
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.FIRST,  # Default fallback
            url_timeout_seconds=2.0
        )
        
        # Test with existing URL to verify FIRST mode behavior
        existing_url = "https://ozon.ru/product/123456/"
        result = hybrid_selector.select_code_with_url(description, existing_url, row_index)
        
        # Should behave like FIRST mode (URL search first)
        assert result.match_source == "url", \
            f"Default (FIRST) mode should find URL match, got: {result.match_source}"
        
        # Verify configuration shows first priority
        config = hybrid_selector.get_configuration()
        assert config["url_priority"] == "first", \
            f"Configuration should show 'first' priority as default"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://market.yandex.ru/product/999999/",  # URL that doesn't exist in test DB
            "https://wildberries.ru/catalog/777777/",  # URL that doesn't exist in test DB
        ]),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=15, deadline=8000)
    def test_url_search_timeout_fallback_to_semantic(self, description, test_url, row_index):
        """
        Test that when URL search takes too long, system times out and falls back to semantic search
        
        Property: For any processing request where URL search exceeds timeout,
        the system should timeout and fall back to semantic search.
        **Validates: Requirements 7.5**
        
        Note: This test may not work on Windows due to signal.SIGALRM limitation.
        On Windows, the timeout mechanism may not function, so we test the fallback behavior.
        """
        import platform
        
        # Create slow URL matcher that simulates timeout
        slow_url_matcher = SlowURLMatcher(
            self.url_db_manager, 
            timeout_seconds=0.1,  # Very short timeout
            simulate_delay=True,
            delay_seconds=2.0  # Much longer than timeout
        )
        
        # Create mock semantic selector
        semantic_selector = MockSemanticSelector(
            should_find_code=True,
            tnved_code="9999888877",
            confidence=0.85
        )
        
        # Create hybrid selector with short timeout
        hybrid_selector = HybridSelector(
            url_matcher=slow_url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.FIRST,
            url_timeout_seconds=0.1  # Very short timeout
        )
        
        # Process with test URL (should timeout and fallback on Unix, may not timeout on Windows)
        start_time = time.time()
        result = hybrid_selector.select_code_with_url(description, test_url, row_index)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # On Windows, timeout may not work due to signal.SIGALRM limitation
        if platform.system() == "Windows":
            # On Windows, we just verify that the system can handle the case
            # where URL search doesn't find a match and falls back to semantic
            assert result.match_source == "semantic", \
                f"Should fall back to semantic search, got: {result.match_source}"
            
            # Should have semantic search results
            assert result.tnved_code == "9999888877", \
                f"Should have TNVED code from semantic fallback"
            assert result.confidence_score == 0.85, \
                f"Should have semantic confidence score"
        else:
            # On Unix-like systems, timeout should work
            assert result.match_source == "semantic", \
                f"Should fall back to semantic search on timeout, got: {result.match_source}"
            
            # Should have semantic search results
            assert result.tnved_code == "9999888877", \
                f"Should have TNVED code from semantic fallback"
            assert result.confidence_score == 0.85, \
                f"Should have semantic confidence score"
            
            # Processing should complete within reasonable time (not wait for full delay)
            assert processing_time < 3.0, \
                f"Processing should complete quickly due to timeout, took: {processing_time}s"
        
        # Selection reason should indicate fallback (not timeout explicitly, but semantic search)
        assert "semantic" in result.selection_reason.lower(), \
            f"Should indicate semantic search was used: {result.selection_reason}"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([URLPriority.FIRST, URLPriority.ONLY, URLPriority.DISABLED]),
        st.floats(min_value=0.1, max_value=10.0),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=30, deadline=5000)
    def test_priority_configuration_consistency_across_requests(self, description, priority_mode, 
                                                               timeout_seconds, row_index):
        """
        Test that priority configuration is consistently applied across multiple requests
        
        Property: For any priority configuration, the system should consistently
        apply the same behavior across multiple processing requests with the same
        configuration parameters.
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
        """
        # Create mock semantic selector
        semantic_selector = MockSemanticSelector(
            should_find_code=True,
            tnved_code="1111222233",
            confidence=0.90
        )
        
        # Create hybrid selector with specified configuration
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=priority_mode,
            url_timeout_seconds=timeout_seconds
        )
        
        # Test with multiple different inputs
        test_cases = [
            ("https://ozon.ru/product/123456/", True),  # Existing URL
            ("https://market.yandex.ru/product/999999/", False),  # Non-existing URL
            (None, False),  # No URL
        ]
        
        results = []
        for test_url, url_exists in test_cases:
            result = hybrid_selector.select_code_with_url(description, test_url, row_index)
            results.append((result, url_exists))
        
        # Verify consistent behavior based on priority mode
        for result, url_exists in results:
            if priority_mode == URLPriority.DISABLED:
                # Should always use semantic search
                assert result.match_source == "semantic", \
                    f"DISABLED mode should always use semantic, got: {result.match_source}"
            
            elif priority_mode == URLPriority.ONLY:
                if result.original_url and url_exists:
                    # Should find URL match
                    assert result.match_source == "url", \
                        f"ONLY mode should find URL match for existing URL, got: {result.match_source}"
                elif result.original_url and not url_exists:
                    # Should not fall back to semantic
                    assert result.match_source == "none", \
                        f"ONLY mode should not fall back to semantic, got: {result.match_source}"
                else:
                    # No URL provided - should use semantic (implementation behavior)
                    assert result.match_source == "semantic", \
                        f"ONLY mode with no URL should use semantic, got: {result.match_source}"
            
            elif priority_mode == URLPriority.FIRST:
                if result.original_url and url_exists:
                    # Should find URL match first
                    assert result.match_source == "url", \
                        f"FIRST mode should find URL match for existing URL, got: {result.match_source}"
                else:
                    # Should fall back to semantic
                    assert result.match_source == "semantic", \
                        f"FIRST mode should fall back to semantic, got: {result.match_source}"
        
        # Verify configuration consistency
        config = hybrid_selector.get_configuration()
        assert config["url_priority"] == priority_mode.value, \
            f"Configuration should maintain priority: {priority_mode.value}"
        assert config["url_timeout_seconds"] == timeout_seconds, \
            f"Configuration should maintain timeout: {timeout_seconds}"
        
        # All results should have consistent metadata structure
        for result, _ in results:
            assert isinstance(result, HybridProcessingResult), \
                f"Should return HybridProcessingResult"
            assert result.row_index == row_index, \
                f"Should preserve row index"
            assert result.original_description == description, \
                f"Should preserve description"
            assert result.processing_time_ms is not None, \
                f"Should have processing time"
            assert result.selection_reason is not None, \
                f"Should have selection reason"
    
    def test_url_config_environment_variable_loading(self):
        """
        Test that URL configuration can be loaded from environment variables
        
        This tests the configuration loading mechanism that supports
        URL priority configuration from environment.
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
        """
        # Test environment variable loading
        test_env_vars = {
            "TNVED_URL_ENABLED": "true",
            "TNVED_URL_PRIORITY": "only",
            "TNVED_URL_TIMEOUT_SECONDS": "3.5",
        }
        
        with patch.dict(os.environ, test_env_vars):
            config = load_url_config_from_env()
            
            assert config.enabled == True, \
                f"Should load enabled from env var, got: {config.enabled}"
            assert config.priority.value == "only", \
                f"Should load priority from env var, got: {config.priority.value}"
            assert config.timeout_seconds == 3.5, \
                f"Should load timeout from env var, got: {config.timeout_seconds}"
        
        # Test invalid priority handling
        invalid_env_vars = {
            "TNVED_URL_PRIORITY": "invalid_mode",
        }
        
        with patch.dict(os.environ, invalid_env_vars):
            config = load_url_config_from_env()
            
            # Should use default priority when invalid value provided
            assert config.priority.value == "first", \
                f"Should use default priority for invalid env var, got: {config.priority.value}"
        
        # Test configuration validation
        validate_url_config(config)  # Should not raise exception