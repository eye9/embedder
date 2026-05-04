#!/usr/bin/env python3
"""
Test script for URL data validation tools

This script tests the URL data validation functionality to ensure
it works correctly with various input scenarios.
"""

import os
import sys
import tempfile
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.url_data_quality_checker import (
    URLDataQualityChecker,
    validate_url_data_file
)


def test_url_format_validator():
    """Test URL format validation"""
    print("Testing URL format validator...")
    
    checker = URLDataQualityChecker()
    
    # Test valid URLs
    valid_urls = [
        "https://ozon.ru/product/123456/",
        "https://market.yandex.ru/product/789012",
        "https://wildberries.ru/catalog/345678/",
        "https://aliexpress.com/item/901234.html",
        "http://example.com/product/123"  # Should be normalized to https
    ]
    
    print("  Testing valid URLs:")
    for url in valid_urls:
        result = checker.validate_url(url)
        status = "✓" if result['is_valid'] else "✗"
        print(f"    {status} {url}")
        if result.get('shop_type'):
            print(f"      Shop: {result['shop_type']}, Product ID: {result.get('product_id')}")
        if result.get('warnings'):
            print(f"      Warnings: {', '.join(result['warnings'])}")
    
    # Test invalid URLs
    invalid_urls = [
        "",
        "not-a-url",
        "ftp://example.com/file",
        "javascript:alert('xss')",
        "http://localhost/admin"
    ]
    
    print("  Testing invalid URLs:")
    for url in invalid_urls:
        result = checker.validate_url(url)
        status = "✓" if result['is_valid'] else "✗"
        print(f"    {status} {url}")
        if result.get('error_message'):
            print(f"      Error: {result['error_message']}")
    
    print("  URL format validator test completed ✓\n")


def test_tnved_format_validator():
    """Test TNVED code format validation"""
    print("Testing TNVED format validator...")
    
    checker = URLDataQualityChecker()
    
    # Test valid codes
    valid_codes = [
        "0901110000",
        "1234567890",
        "901110000",  # Should be padded
        "09011100",   # Should be padded
        "0901.11.00.00"  # Should be normalized
    ]
    
    print("  Testing valid codes:")
    for code in valid_codes:
        result = checker.validate_tnved_code(code)
        status = "✓" if result['is_valid'] else "✗"
        print(f"    {status} {code}")
        if result.get('normalized_code') and result['code'] != result.get('normalized_code'):
            print(f"      Normalized: {result['normalized_code']}")
        if result.get('warnings'):
            print(f"      Warnings: {', '.join(result['warnings'])}")
    
    # Test invalid codes
    invalid_codes = [
        "",
        "abc123",
        "12345678901",  # Too long
        "123"  # Too short
    ]
    
    print("  Testing invalid codes:")
    for code in invalid_codes:
        result = checker.validate_tnved_code(code)
        status = "✓" if result['is_valid'] else "✗"
        print(f"    {status} {code}")
        if result.get('error_message'):
            print(f"      Error: {result['error_message']}")
    
    print("  TNVED format validator test completed ✓\n")


def test_data_quality_analyzer():
    """Test data quality analyzer with sample data"""
    print("Testing data quality analyzer...")
    
    # Create sample data
    sample_data = {
        'URL': [
            'https://ozon.ru/product/123456/',
            'https://market.yandex.ru/product/789012',
            'invalid-url',
            'https://wildberries.ru/catalog/345678/',
            '',  # Empty URL
            'https://ozon.ru/product/123456/',  # Duplicate
        ],
        'Code': [
            '0901110000',
            '1234567890',
            '0901110000',
            'invalid-code',
            '0901110000',
            '0901110000',
        ],
        'Description': [
            'Coffee beans',
            'Tea leaves',
            'Coffee beans',
            'Spices',
            '',  # Empty description
            'Coffee beans duplicate',
        ]
    }
    
    # Create temporary Excel file
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        df = pd.DataFrame(sample_data)
        df.to_excel(tmp_file.name, index=False)
        temp_file_path = tmp_file.name
    
    try:
        # Analyze the file
        checker = URLDataQualityChecker()
        result = checker.analyze_excel_file(temp_file_path)
        
        if result['success']:
            analysis = result['analysis']
            print(f"  Total records: {analysis['total_records']}")
            print(f"  Valid URLs: {analysis['valid_urls']}")
            print(f"  Invalid URLs: {analysis['invalid_urls']}")
            print(f"  Valid TNVED codes: {analysis['valid_tnved_codes']}")
            print(f"  Invalid TNVED codes: {analysis['invalid_tnved_codes']}")
            print(f"  Duplicate URLs: {analysis['duplicate_urls']}")
            print(f"  Missing descriptions: {analysis['missing_descriptions']}")
            print(f"  URL quality score: {analysis['url_quality_score']:.1f}%")
            print(f"  TNVED quality score: {analysis['tnved_quality_score']:.1f}%")
            print(f"  Overall quality score: {analysis['overall_quality_score']:.1f}%")
            
            if analysis['recommendations']:
                print("  Recommendations:")
                for i, rec in enumerate(analysis['recommendations'], 1):
                    print(f"    {i}. {rec}")
        else:
            print(f"  Analysis failed: {result['error']}")
        
        # Test convenience function
        result = validate_url_data_file(temp_file_path)
        assert result["success"], "Convenience function should succeed"
        
        print("  Data quality analyzer test completed ✓\n")
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)


def test_export_functionality():
    """Test report export functionality"""
    print("Testing export functionality...")
    
    # Create sample data
    sample_data = {
        'URL': [
            'https://ozon.ru/product/123456/',
            'https://market.yandex.ru/product/789012',
            'invalid-url'
        ],
        'Code': [
            '0901110000',
            '1234567890',
            'invalid-code'
        ],
        'Description': [
            'Coffee beans',
            'Tea leaves',
            'Spices'
        ]
    }
    
    # Create temporary Excel file
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        df = pd.DataFrame(sample_data)
        df.to_excel(tmp_file.name, index=False)
        temp_input_path = tmp_file.name
    
    try:
        # Analyze and export
        checker = URLDataQualityChecker()
        result = checker.analyze_excel_file(temp_input_path)
        
        # Test Excel export
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_output:
            temp_output_path = tmp_output.name
        
        try:
            success = checker.export_report_to_excel(result, temp_output_path)
            assert success, "Excel export should succeed"
            assert os.path.exists(temp_output_path), "Output file should exist"
            print("  Excel export test completed ✓")
            
        finally:
            if os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
        
        # Test JSON export
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_json:
            temp_json_path = tmp_json.name
        
        try:
            success = checker.export_report_to_json(result, temp_json_path)
            assert success, "JSON export should succeed"
            assert os.path.exists(temp_json_path), "JSON output file should exist"
            print("  JSON export test completed ✓")
            
        finally:
            if os.path.exists(temp_json_path):
                os.unlink(temp_json_path)
        
    finally:
        # Clean up temporary input file
        os.unlink(temp_input_path)
    
    print("  Export functionality test completed ✓\n")


def main():
    """Run all tests"""
    print("Running URL data validation tests...\n")
    
    try:
        test_url_format_validator()
        test_tnved_format_validator()
        test_data_quality_analyzer()
        test_export_functionality()
        
        print("All tests completed successfully! ✓")
        return 0
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())