"""
Property-based tests for hybrid selection strategy functionality.

**Feature: url-based-code-matching, Property 2: Hybrid Selection Strategy**
**Validates: Requirements 1.3, 1.4, 1.5**
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, MagicMock

from batch_processor.services.enhanced_excel_processor import EnhancedExcelProcessor
from batch_processor.models.result import ProcessingResult
from services.hybrid_selector import HybridSelector, HybridProcessingResult, URLPriority
from services.url_matcher import URLMatcher, URLMatchResult


class TestHybridSelectionStrategyProperty:
    """Property-based tests for hybrid selection strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = EnhancedExcelProcessor()
    
    def create_mock_hybrid_selector(self, url_match_behavior: str = "found") -> HybridSelector:
        """
        Create a mock hybrid selector for testing.
        
        Args:
            url_match_behavior: "found", "not_found", or "error"
            
        Returns:
            Mock HybridSelector instance
        """
        # Create mock URL matcher
        mock_url_matcher = Mock(spec=URLMatcher)
        
        if url_match_behavior == "found":
            mock_url_matcher.find_code_by_url.return_value = URLMatchResult(
                found=True,
                tnved_code="1234567890",
                description="Test product from URL",
                source_name="test_source",
                original_url="https://example.com/product/123",
                normalized_url="https://example.com/product/123",
                confidence=1.0,
                match_type="exact_url"
            )
        elif url_match_behavior == "not_found":
            mock_url_matcher.find_code_by_url.return_value = URLMatchResult(found=False)
        else:  # error
            mock_url_matcher.find_code_by_url.side_effect = Exception("URL matcher error")
        
        # Create mock semantic selector
        mock_semantic_selector = Mock()
        mock_semantic_selector.select_code.return_value = ProcessingResult(
            row_index=0,
            original_description="Test product",
            tnved_code="9876543210",
            selection_reason="Found by semantic search",
            confidence_score=0.85
        )
        mock_semantic_selector.get_algorithm_name.return_value = "mock_semantic"
        
        # Create hybrid selector
        hybrid_selector = HybridSelector(
            url_matcher=mock_url_matcher,
            semantic_selector=mock_semantic_selector,
            url_priority=URLPriority.FIRST
        )
        
        return hybrid_selector
    
    def create_mock_semantic_selector(self) -> Mock:
        """Create a mock semantic selector for backward compatibility testing."""
        mock_selector = Mock()
        mock_selector.select_code.return_value = ProcessingResult(
            row_index=0,
            original_description="Test product",
            tnved_code="1111111111",
            selection_reason="Found by semantic search only",
            confidence_score=0.75
        )
        return mock_selector
    
    @given(
        has_url_column=st.booleans(),
        url_column_name=st.sampled_from([
            "Link to customer's web-page with item description",
            "URL",
            "Product URL",
            "Link"
        ]),
        num_rows=st.integers(min_value=1, max_value=20),
        url_fill_rate=st.floats(min_value=0.0, max_value=1.0),
        url_match_behavior=st.sampled_from(["found", "not_found"])
    )
    def test_hybrid_selection_strategy_property(
        self, 
        has_url_column, 
        url_column_name, 
        num_rows, 
        url_fill_rate,
        url_match_behavior
    ):
        """
        Property: For any row with both description and URL, the system should use both 
        pieces of information for code selection, while rows with only description should 
        fall back to semantic search, and files without URL columns should process using 
        semantic search only.
        
        **Feature: url-based-code-matching, Property 2: Hybrid Selection Strategy**
        **Validates: Requirements 1.3, 1.4, 1.5**
        """
        # Generate test data
        data = {
            "Product Detailed Description": [f"Product {i}" for i in range(num_rows)]
        }
        
        # Add URL column if specified
        urls_with_values = 0
        if has_url_column:
            urls = []
            for i in range(num_rows):
                if i < int(num_rows * url_fill_rate):
                    urls.append(f"https://example.com/product/{i}")
                    urls_with_values += 1
                else:
                    urls.append("")  # Empty URL
            data[url_column_name] = urls
        
        # Create temporary Excel file
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file_path, index=False, engine='openpyxl')
            file_path = Path(tmp_file_path)
            
            # Create mock hybrid selector
            hybrid_selector = self.create_mock_hybrid_selector(url_match_behavior)
            
            # Process file with hybrid selector
            results = list(self.processor.process_file_with_hybrid_selector(
                file_path, hybrid_selector, "all"
            ))
            
            # Property assertions
            assert len(results) == num_rows, f"Expected {num_rows} results, got {len(results)}"
            
            # Verify hybrid selection behavior
            for i, result in enumerate(results):
                assert isinstance(result, HybridProcessingResult), "Should return HybridProcessingResult"
                assert result.row_index == i, f"Row index mismatch for result {i}"
                assert result.original_description == f"Product {i}", "Description should match"
                
                # Check URL handling
                if has_url_column and i < urls_with_values:
                    # Row has URL
                    expected_url = f"https://example.com/product/{i}"
                    assert result.original_url == expected_url, f"URL should match for row {i}"
                    
                    if url_match_behavior == "found":
                        # URL match should be found
                        assert result.match_source == "url", f"Should use URL match for row {i}"
                        assert result.tnved_code == "1234567890", "Should return URL-matched code"
                    else:
                        # URL match not found, should fall back to semantic
                        assert result.match_source == "semantic", f"Should fall back to semantic for row {i}"
                        assert result.tnved_code == "9876543210", "Should return semantic-matched code"
                else:
                    # Row has no URL or no URL column
                    assert result.original_url is None or result.original_url == "", "URL should be empty"
                    assert result.match_source == "semantic", f"Should use semantic search for row {i}"
                    assert result.tnved_code == "9876543210", "Should return semantic-matched code"
            
            # Test backward compatibility mode
            semantic_selector = self.create_mock_semantic_selector()
            backward_results = list(self.processor.process_file_with_backward_compatibility(
                file_path, semantic_selector, "all"
            ))
            
            # Backward compatibility assertions
            assert len(backward_results) == num_rows, "Backward compatibility should process all rows"
            
            for i, result in enumerate(backward_results):
                assert isinstance(result, ProcessingResult), "Should return ProcessingResult in backward mode"
                assert result.tnved_code == "1111111111", "Should use semantic selector only"
                assert "semantic search only" in result.selection_reason, "Should indicate semantic-only processing"
            
        finally:
            # Clean up temporary file
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except PermissionError:
                    pass  # Ignore permission errors on Windows
    
    @given(
        num_rows=st.integers(min_value=1, max_value=10),
        url_fill_rate=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_processing_strategy_determination_property(self, num_rows, url_fill_rate):
        """
        Property: The system should correctly determine processing strategy based on 
        file characteristics and URL coverage.
        
        **Feature: url-based-code-matching, Property 2: Hybrid Selection Strategy**
        **Validates: Requirements 1.3, 1.4, 1.5**
        """
        # Test with URL column
        data_with_urls = {
            "Product Detailed Description": [f"Product {i}" for i in range(num_rows)],
            "URL": []
        }
        
        urls_with_values = 0
        for i in range(num_rows):
            if i < int(num_rows * url_fill_rate):
                data_with_urls["URL"].append(f"https://example.com/product/{i}")
                urls_with_values += 1
            else:
                data_with_urls["URL"].append("")
        
        # Test with no URL column
        data_without_urls = {
            "Product Detailed Description": [f"Product {i}" for i in range(num_rows)]
        }
        
        test_cases = [
            (data_with_urls, True, urls_with_values),
            (data_without_urls, False, 0)
        ]
        
        for data, has_urls, expected_url_count in test_cases:
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                    tmp_file_path = tmp_file.name
                
                df = pd.DataFrame(data)
                df.to_excel(tmp_file_path, index=False, engine='openpyxl')
                file_path = Path(tmp_file_path)
                
                # Determine processing strategy
                strategy = self.processor.determine_processing_strategy(file_path)
                
                # Property assertions
                assert "strategy" in strategy, "Should return strategy"
                assert "recommended_selector" in strategy, "Should recommend selector"
                assert "file_characteristics" in strategy, "Should include file characteristics"
                
                file_chars = strategy["file_characteristics"]
                assert file_chars["has_url_column"] == has_urls, "URL column detection should match"
                assert file_chars["total_rows"] == num_rows, "Row count should match"
                assert file_chars["rows_with_urls"] == expected_url_count, "URL count should match"
                
                if has_urls:
                    expected_coverage = expected_url_count / num_rows
                    assert abs(file_chars["url_coverage"] - expected_coverage) < 0.01, "URL coverage should match"
                    
                    if expected_coverage == 0.0:
                        assert strategy["recommended_selector"] == "semantic", "Should recommend semantic for no URLs"
                    else:
                        assert strategy["recommended_selector"] == "hybrid", "Should recommend hybrid for URLs"
                else:
                    assert file_chars["url_coverage"] == 0.0, "Should have zero URL coverage"
                    assert strategy["recommended_selector"] == "semantic", "Should recommend semantic without URLs"
                
            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    try:
                        os.unlink(tmp_file_path)
                    except PermissionError:
                        pass
    
    def test_hybrid_processing_summary_property(self):
        """
        Property: The system should generate accurate processing summaries with 
        correct statistics for hybrid processing results.
        
        **Feature: url-based-code-matching, Property 2: Hybrid Selection Strategy**
        **Validates: Requirements 1.3, 1.4, 1.5**
        """
        # Create test data
        data = {
            "Product Detailed Description": ["Product 1", "Product 2", "Product 3"],
            "URL": ["https://example.com/1", "", "https://example.com/3"]
        }
        
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file_path, index=False, engine='openpyxl')
            file_path = Path(tmp_file_path)
            
            # Create mock results
            results = [
                HybridProcessingResult(
                    row_index=0,
                    original_description="Product 1",
                    original_url="https://example.com/1",
                    tnved_code="1111111111",
                    selection_reason="Found by URL",
                    match_source="url",
                    processing_time_ms=10.0
                ),
                HybridProcessingResult(
                    row_index=1,
                    original_description="Product 2",
                    original_url=None,
                    tnved_code="2222222222",
                    selection_reason="Found by semantic search",
                    match_source="semantic",
                    processing_time_ms=20.0
                ),
                HybridProcessingResult(
                    row_index=2,
                    original_description="Product 3",
                    original_url="https://example.com/3",
                    tnved_code="3333333333",
                    selection_reason="URL not found, used semantic search",
                    match_source="semantic",
                    processing_time_ms=30.0
                )
            ]
            
            # Generate summary
            summary = self.processor.generate_hybrid_processing_summary(
                file_path, results, "all"
            )
            
            # Property assertions
            assert summary["processing_statistics"]["rows_processed"] == 3, "Should process 3 rows"
            assert summary["processing_statistics"]["successful_processing"] == 3, "All should be successful"
            assert summary["processing_statistics"]["success_rate"] == 1.0, "Success rate should be 100%"
            
            # Match source breakdown
            match_breakdown = summary["match_source_breakdown"]
            assert match_breakdown["url_matches"] == 1, "Should have 1 URL match"
            assert match_breakdown["semantic_matches"] == 2, "Should have 2 semantic matches"
            assert match_breakdown["no_matches"] == 0, "Should have 0 no-matches"
            
            # URL processing stats
            url_stats = summary["url_processing_stats"]
            assert url_stats["rows_with_urls"] == 2, "Should have 2 rows with URLs"
            assert url_stats["rows_without_urls"] == 1, "Should have 1 row without URL"
            assert abs(url_stats["url_coverage"] - 2/3) < 0.01, "URL coverage should be 2/3"
            
            # Performance metrics
            perf_metrics = summary["performance_metrics"]
            assert perf_metrics["average_processing_time_ms"] == 20.0, "Average time should be 20ms"
            assert perf_metrics["total_processing_time_ms"] == 60.0, "Total time should be 60ms"
            assert perf_metrics["fastest_processing_ms"] == 10.0, "Fastest should be 10ms"
            assert perf_metrics["slowest_processing_ms"] == 30.0, "Slowest should be 30ms"
            
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except PermissionError:
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])