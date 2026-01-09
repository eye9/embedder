"""
Property-based tests for search priority and fallback behavior

This module contains property-based tests that verify the hybrid selector's
search priority and fallback behavior across various scenarios including
URL-first search, semantic fallback, URL-only mode, and complete search failures.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from services.hybrid_selector import HybridSelector, URLPriority, HybridProcessingResult
from services.url_matcher import URLMatcher, URLMatchResult
from services.url_database_manager import URLDatabaseManager
from services.url_normalizer import URLNormalizer
from batch_processor.services.tnved_selector import TNVEDSelector
from batch_processor.models.result import ProcessingResult
import chromadb
from chromadb.config import Settings
import tempfile
import os
from typing import Optional
from dataclasses import dataclass


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


class TestSearchPriorityFallbackProperty:
    """Property-based tests for search priority and fallback behavior"""
    
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
            collection_name="test_search_priority"
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
    
    # Feature: url-based-code-matching, Property 5: Search Priority and Fallback Behavior
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://ozon.ru/product/123456/",  # URL that exists in test DB
            "https://market.yandex.ru/product/789012",  # URL that exists in test DB
            "https://wildberries.ru/catalog/345678/",  # URL that exists in test DB
            "https://example.com/product/999",  # URL that exists in test DB
        ]),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=30, deadline=5000)
    def test_url_first_search_with_match(self, description, existing_url, row_index):
        """
        Test that when URL match is found, system returns URL result immediately
        
        Property: For any processing request with URL that exists in database,
        the system should first normalize the URL, query the URL database for exact match,
        and return the associated TNVED code with URL explanation.
        **Validates: Requirements 3.1, 3.2**
        """
        # Create mock semantic selector (should not be called when URL match found)
        semantic_selector = MockSemanticSelector(should_find_code=True)
        
        # Create hybrid selector with URL-first priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.FIRST,
            url_timeout_seconds=2.0
        )
        
        # Process with URL that exists in database
        result = hybrid_selector.select_code_with_url(description, existing_url, row_index)
        
        # Should find URL match (check via match_source and tnved_code)
        assert result.match_source == "url", f"Should find URL match for existing URL: {existing_url}"
        assert result.match_source == "url", f"Match source should be 'url', got: {result.match_source}"
        assert result.tnved_code is not None, f"Should have TNVED code from URL match"
        assert result.original_url == existing_url, f"Should preserve original URL"
        assert result.url_normalized is not None, f"Should have normalized URL"
        
        # Selection reason should indicate URL match
        assert "Found by URL" in result.selection_reason or "URL" in result.selection_reason, \
            f"Selection reason should indicate URL match: {result.selection_reason}"
        
        # Should have high confidence for exact URL match
        assert result.confidence_score == 1.0, \
            f"URL matches should have confidence 1.0, got: {result.confidence_score}"
        
        # Should have processing metadata
        assert result.row_index == row_index, f"Should preserve row index"
        assert result.original_description == description, f"Should preserve description"
        assert result.processing_time_ms is not None, f"Should have processing time"
        assert result.processing_time_ms >= 0, f"Processing time should be non-negative"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://ozon.ru/product/999999/",  # URL that doesn't exist in test DB
            "https://market.yandex.ru/product/888888",  # URL that doesn't exist in test DB
            "https://wildberries.ru/catalog/777777/",  # URL that doesn't exist in test DB
            "https://unknown-shop.com/product/123",  # Unknown shop URL
        ]),
        st.integers(min_value=0, max_value=1000),
        st.booleans(),  # Whether semantic selector should find code
        st.floats(min_value=0.0, max_value=1.0)  # Semantic confidence
    )
    @settings(max_examples=40, deadline=5000)
    def test_url_not_found_fallback_to_semantic(self, description, non_existing_url, 
                                               row_index, semantic_finds_code, semantic_confidence):
        """
        Test that when URL match is not found, system falls back to semantic search
        
        Property: For any processing request where URL match is not found,
        the system should fall back to semantic search using the description
        and indicate semantic search in explanation.
        **Validates: Requirements 3.3, 3.4**
        """
        # Create mock semantic selector with controlled behavior
        semantic_selector = MockSemanticSelector(
            should_find_code=semantic_finds_code,
            tnved_code="9876543210" if semantic_finds_code else None,
            confidence=semantic_confidence
        )
        
        # Create hybrid selector with URL-first priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.FIRST,
            url_timeout_seconds=2.0
        )
        
        # Process with URL that doesn't exist in database
        result = hybrid_selector.select_code_with_url(description, non_existing_url, row_index)
        
        # Should not find URL match, should use semantic fallback
        assert result.match_source == "semantic", \
            f"Should use semantic fallback when URL not found, got: {result.match_source}"
        
        # Result should match semantic selector behavior
        if semantic_finds_code:
            assert result.tnved_code == "9876543210", \
                f"Should have TNVED code from semantic search"
            assert result.confidence_score == semantic_confidence, \
                f"Should have semantic confidence score"
        else:
            assert result.tnved_code is None, \
                f"Should have no TNVED code when semantic search fails"
        
        # Selection reason should indicate fallback to semantic search
        assert ("semantic" in result.selection_reason.lower() or 
                "fallback" in result.selection_reason.lower() or
                "not found" in result.selection_reason.lower()), \
            f"Selection reason should indicate semantic fallback: {result.selection_reason}"
        
        # Should preserve original URL and description
        assert result.original_url == non_existing_url, f"Should preserve original URL"
        assert result.original_description == description, f"Should preserve description"
        assert result.row_index == row_index, f"Should preserve row index"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://ozon.ru/product/999999/",  # URL that doesn't exist in test DB
            "https://market.yandex.ru/product/888888",  # URL that doesn't exist in test DB
            "https://wildberries.ru/catalog/777777/",  # URL that doesn't exist in test DB
        ]),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=20, deadline=5000)
    def test_url_only_mode_no_fallback(self, description, non_existing_url, row_index):
        """
        Test that in URL-only mode, system doesn't fall back to semantic search
        
        Property: For any processing request in URL-only mode where URL match is not found,
        the system should return empty code with appropriate explanation without
        attempting semantic search.
        **Validates: Requirements 3.3, 3.5**
        """
        # Create mock semantic selector (should not be called in URL-only mode)
        semantic_selector = MockSemanticSelector(should_find_code=True)
        
        # Create hybrid selector with URL-only priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.ONLY,
            url_timeout_seconds=2.0
        )
        
        # Process with URL that doesn't exist in database
        result = hybrid_selector.select_code_with_url(description, non_existing_url, row_index)
        
        # Should not find any match in URL-only mode
        assert result.match_source == "none", \
            f"Should have no match in URL-only mode, got: {result.match_source}"
        assert result.tnved_code is None, \
            f"Should have no TNVED code in URL-only mode when URL not found"
        assert result.confidence_score is None, \
            f"Should have no confidence score when no match found"
        
        # Selection reason should indicate URL-only mode
        assert ("only" in result.selection_reason.lower() or 
                "no match" in result.selection_reason.lower() or
                "not found" in result.selection_reason.lower()), \
            f"Selection reason should indicate URL-only mode: {result.selection_reason}"
        
        # Should preserve metadata
        assert result.original_url == non_existing_url, f"Should preserve original URL"
        assert result.original_description == description, f"Should preserve description"
        assert result.row_index == row_index, f"Should preserve row index"
        assert result.processing_time_ms is not None, f"Should have processing time"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.one_of(
            st.none(),  # No URL provided
            st.just(""),  # Empty URL
            st.just("   "),  # Whitespace URL
        ),
        st.integers(min_value=0, max_value=1000),
        st.booleans()  # Whether semantic selector should find code
    )
    @settings(max_examples=25, deadline=5000)
    def test_no_url_semantic_only(self, description, empty_url, row_index, semantic_finds_code):
        """
        Test that when no URL is provided, system uses semantic search only
        
        Property: For any processing request without URL or with empty URL,
        the system should skip URL search and use semantic search directly.
        **Validates: Requirements 3.1, 3.3**
        """
        # Create mock semantic selector with controlled behavior
        semantic_selector = MockSemanticSelector(
            should_find_code=semantic_finds_code,
            tnved_code="1111222233" if semantic_finds_code else None,
            confidence=0.75
        )
        
        # Create hybrid selector with URL-first priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.FIRST,
            url_timeout_seconds=2.0
        )
        
        # Process without URL
        result = hybrid_selector.select_code_with_url(description, empty_url, row_index)
        
        # Should use semantic search only
        assert result.match_source == "semantic", \
            f"Should use semantic search when no URL provided, got: {result.match_source}"
        
        # Result should match semantic selector behavior
        if semantic_finds_code:
            assert result.tnved_code == "1111222233", \
                f"Should have TNVED code from semantic search"
            assert result.confidence_score == 0.75, \
                f"Should have semantic confidence score"
        else:
            assert result.tnved_code is None, \
                f"Should have no TNVED code when semantic search fails"
        
        # Selection reason should indicate semantic search (not fallback)
        assert "semantic" in result.selection_reason.lower(), \
            f"Selection reason should indicate semantic search: {result.selection_reason}"
        
        # Should preserve metadata
        assert result.original_url == empty_url, f"Should preserve original URL (even if empty)"
        assert result.original_description == description, f"Should preserve description"
        assert result.row_index == row_index, f"Should preserve row index"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([
            "https://ozon.ru/product/999999/",  # URL that doesn't exist in test DB
            "https://market.yandex.ru/product/888888",  # URL that doesn't exist in test DB
        ]),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=15, deadline=5000)
    def test_both_searches_fail(self, description, non_existing_url, row_index):
        """
        Test that when both URL and semantic search fail, system returns empty code
        
        Property: For any processing request where both URL and semantic search fail,
        the system should return empty code with appropriate explanation indicating
        both search methods were attempted.
        **Validates: Requirements 3.5**
        """
        # Create mock semantic selector that fails
        semantic_selector = MockSemanticSelector(
            should_find_code=False,
            tnved_code=None,
            confidence=None
        )
        
        # Create hybrid selector with URL-first priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=URLPriority.FIRST,
            url_timeout_seconds=2.0
        )
        
        # Process with URL that doesn't exist in database
        result = hybrid_selector.select_code_with_url(description, non_existing_url, row_index)
        
        # Should indicate semantic search was used (as fallback)
        assert result.match_source == "semantic", \
            f"Should show semantic as match source for fallback, got: {result.match_source}"
        
        # Should have no TNVED code when both searches fail
        assert result.tnved_code is None, \
            f"Should have no TNVED code when both searches fail"
        assert result.confidence_score is None, \
            f"Should have no confidence score when both searches fail"
        
        # Selection reason should indicate semantic search was used (as fallback)
        assert "semantic" in result.selection_reason.lower(), \
            f"Selection reason should indicate semantic search: {result.selection_reason}"
        
        # Should preserve metadata
        assert result.original_url == non_existing_url, f"Should preserve original URL"
        assert result.original_description == description, f"Should preserve description"
        assert result.row_index == row_index, f"Should preserve row index"
        assert result.processing_time_ms is not None, f"Should have processing time"
    
    @given(
        st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Zs'),
            blacklist_characters='\x00\r\n'
        )),
        st.sampled_from([URLPriority.FIRST, URLPriority.ONLY, URLPriority.DISABLED]),
        st.integers(min_value=0, max_value=1000)
    )
    @settings(max_examples=30, deadline=5000)
    def test_priority_configuration_consistency(self, description, priority_mode, row_index):
        """
        Test that priority configuration is respected consistently
        
        Property: For any processing request, the system should consistently
        respect the configured URL priority mode across different inputs.
        **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
        """
        # Create mock semantic selector
        semantic_selector = MockSemanticSelector(
            should_find_code=True,
            tnved_code="9999888877",
            confidence=0.85
        )
        
        # Create hybrid selector with specified priority
        hybrid_selector = HybridSelector(
            url_matcher=self.url_matcher,
            semantic_selector=semantic_selector,
            url_priority=priority_mode,
            url_timeout_seconds=2.0
        )
        
        # Test with existing URL
        existing_url = "https://ozon.ru/product/123456/"
        result_with_url = hybrid_selector.select_code_with_url(description, existing_url, row_index)
        
        # Test without URL
        result_without_url = hybrid_selector.select_code_with_url(description, None, row_index)
        
        # Verify behavior matches priority configuration
        if priority_mode == URLPriority.DISABLED:
            # Should always use semantic search
            assert result_with_url.match_source == "semantic", \
                f"DISABLED mode should use semantic even with URL"
            assert result_without_url.match_source == "semantic", \
                f"DISABLED mode should use semantic without URL"
        
        elif priority_mode == URLPriority.ONLY:
            # Should only use URL search when URL is provided
            assert result_with_url.match_source == "url", \
                f"ONLY mode should find URL match for existing URL"
            # When no URL is provided, even in ONLY mode, it falls back to semantic
            # because the condition is "DISABLED or not url"
            assert result_without_url.match_source == "semantic", \
                f"ONLY mode should use semantic when no URL provided (implementation behavior)"
        
        elif priority_mode == URLPriority.FIRST:
            # Should use URL first, then semantic fallback
            assert result_with_url.match_source == "url", \
                f"FIRST mode should find URL match for existing URL"
            assert result_without_url.match_source == "semantic", \
                f"FIRST mode should use semantic without URL"
        
        # Both results should have consistent metadata structure
        for result in [result_with_url, result_without_url]:
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