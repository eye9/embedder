"""
Property-based tests for Excel URL column detection functionality.

**Feature: url-based-code-matching, Property 1: Excel File URL Column Detection**
**Validates: Requirements 1.1, 1.2**
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, assume
from batch_processor.services.excel_processor import ExcelProcessor


class TestExcelURLColumnDetectionProperty:
    """Property-based tests for Excel URL column detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ExcelProcessor()
    
    @given(
        has_url_column=st.booleans(),
        url_column_name=st.sampled_from([
            "Link to customer's web-page with item description",
            "URL",
            "Product URL", 
            "Link"
        ]),
        num_rows=st.integers(min_value=1, max_value=50),
        url_fill_rate=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_url_column_detection_property(self, has_url_column, url_column_name, num_rows, url_fill_rate):
        """
        Property: For any Excel file, the system should correctly identify the presence 
        or absence of URL columns and extract URL values from detected columns for each row.
        
        **Feature: url-based-code-matching, Property 1: Excel File URL Column Detection**
        **Validates: Requirements 1.1, 1.2**
        """
        # Generate test data
        data = {
            "Product Detailed Description": [f"Product {i}" for i in range(num_rows)]
        }
        
        # Add URL column if specified
        if has_url_column:
            urls = []
            for i in range(num_rows):
                if i < int(num_rows * url_fill_rate):
                    urls.append(f"https://example.com/product/{i}")
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
            
            # Test validate_file_with_url_support
            is_valid, error_msg, total_rows, detected_url_column = self.processor.validate_file_with_url_support(file_path)
            
            # Property assertions
            assert is_valid, f"File should be valid but got error: {error_msg}"
            assert total_rows == num_rows, f"Expected {num_rows} rows, got {total_rows}"
            assert detected_url_column == has_url_column, f"URL column detection mismatch: expected {has_url_column}, got {detected_url_column}"
            
            # Test get_file_info for URL column detection
            file_info = self.processor.get_file_info(file_path)
            assert file_info["has_url_column"] == has_url_column, "get_file_info URL column detection mismatch"
            assert file_info["total_rows"] == num_rows, "get_file_info row count mismatch"
            
            if has_url_column:
                assert file_info["url_column"] == url_column_name, "URL column name mismatch"
                expected_url_count = int(num_rows * url_fill_rate)
                assert file_info["rows_with_urls"] == expected_url_count, f"Expected {expected_url_count} URLs, got {file_info['rows_with_urls']}"
            else:
                assert file_info["url_column"] is None, "URL column should be None when not present"
                assert file_info["rows_with_urls"] == 0, "Should have 0 URLs when no URL column"
            
            # Test read_file_chunked_with_urls
            chunks = list(self.processor.read_file_chunked_with_urls(file_path))
            assert len(chunks) > 0, "Should yield at least one chunk"
            
            for chunk_df, start_row, total_rows_chunk, url_col in chunks:
                assert total_rows_chunk == num_rows, "Total rows should match in chunks"
                assert url_col == (url_column_name if has_url_column else None), "URL column name should match in chunks"
                
                # Test URL extraction from rows
                for _, row in chunk_df.iterrows():
                    extracted_url = self.processor.extract_url_from_row(row, url_col)
                    
                    if has_url_column and url_col in row.index:
                        original_url = row[url_col]
                        if pd.isna(original_url) or str(original_url).strip() == "":
                            assert extracted_url is None, "Should extract None for empty URLs"
                        else:
                            assert extracted_url == str(original_url).strip(), "Should extract non-empty URLs correctly"
                    else:
                        assert extracted_url is None, "Should extract None when no URL column"
            
        finally:
            # Clean up temporary file
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except PermissionError:
                    pass  # Ignore permission errors on Windows
    
    @given(
        column_names=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    def test_url_column_detection_with_various_column_names(self, column_names):
        """
        Property: The system should correctly identify URL columns among various column names.
        
        **Feature: url-based-code-matching, Property 1: Excel File URL Column Detection**
        **Validates: Requirements 1.1, 1.2**
        """
        # Ensure we have the required description column
        if "Product Detailed Description" not in column_names:
            column_names.append("Product Detailed Description")
        
        # Check if any of the known URL column names are present
        known_url_columns = [
            "Link to customer's web-page with item description",
            "URL",
            "Product URL",
            "Link"
        ]
        
        has_known_url_column = any(col in column_names for col in known_url_columns)
        expected_url_column = None
        if has_known_url_column:
            expected_url_column = next(col for col in column_names if col in known_url_columns)
        
        # Create test data
        data = {}
        for col in column_names:
            if col == "Product Detailed Description":
                data[col] = ["Test product"]
            else:
                data[col] = ["test_value"]
        
        # Create temporary Excel file
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
            
            df = pd.DataFrame(data)
            df.to_excel(tmp_file_path, index=False, engine='openpyxl')
            file_path = Path(tmp_file_path)
            
            # Test URL column detection
            detected_url_column = self.processor._find_url_column(column_names)
            
            # Property assertion
            if has_known_url_column:
                assert detected_url_column == expected_url_column, f"Should detect URL column {expected_url_column}, got {detected_url_column}"
            else:
                assert detected_url_column is None, f"Should not detect URL column, got {detected_url_column}"
            
            # Test with file validation
            is_valid, error_msg, total_rows, detected_has_url = self.processor.validate_file_with_url_support(file_path)
            assert is_valid, f"File should be valid: {error_msg}"
            assert detected_has_url == has_known_url_column, "File validation URL detection should match column detection"
            
        finally:
            # Clean up temporary file
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except PermissionError:
                    pass  # Ignore permission errors on Windows
    
    def test_url_extraction_edge_cases(self):
        """
        Property: URL extraction should handle edge cases correctly.
        
        **Feature: url-based-code-matching, Property 1: Excel File URL Column Detection**
        **Validates: Requirements 1.1, 1.2**
        """
        # Test cases for URL extraction
        test_cases = [
            (None, None, None),  # No URL column
            ("URL", None, None),  # URL column exists but value is None
            ("URL", "", None),    # URL column exists but value is empty string
            ("URL", "   ", None), # URL column exists but value is whitespace
            ("URL", "https://example.com", "https://example.com"),  # Valid URL
            ("URL", "  https://example.com  ", "https://example.com"),  # URL with whitespace
        ]
        
        for url_column, url_value, expected_result in test_cases:
            # Create test row
            row_data = {"Product Detailed Description": "Test product"}
            if url_column and url_value is not None:
                row_data[url_column] = url_value
            
            row = pd.Series(row_data)
            
            # Test URL extraction
            extracted_url = self.processor.extract_url_from_row(row, url_column)
            
            # Property assertion
            assert extracted_url == expected_result, f"URL extraction failed for case {test_cases.index((url_column, url_value, expected_result))}: expected {expected_result}, got {extracted_url}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])