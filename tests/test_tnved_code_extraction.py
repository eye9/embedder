#!/usr/bin/env python3
"""
Test TNVED code extraction functionality.

This script tests that TNVED codes are properly extracted from database identifiers
and that only clean 10-digit codes are returned.
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.services.tnved_code_utils import (
    extract_tnved_code,
    is_valid_tnved_code,
    format_tnved_code
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_tnved_code_extraction():
    """Test TNVED code extraction from various identifiers."""
    print("Testing TNVED Code Extraction")
    print("=" * 40)
    
    test_cases = [
        # (input, expected_output, description)
        ("9405210013_003", "9405210013", "Code with sequence number"),
        ("9405210013", "9405210013", "Clean 10-digit code"),
        ("0901210009_001", "0901210009", "Code starting with 0"),
        ("7304316000_123", "7304316000", "Another code with sequence"),
        ("123456789", None, "9-digit code (invalid)"),
        ("12345678901", None, "11-digit code (invalid)"),
        ("abcd123456", None, "Non-numeric code"),
        ("", None, "Empty string"),
        (None, None, "None input"),
        ("9405210013_", "9405210013", "Code with trailing underscore"),
        ("9405210013_abc", "9405210013", "Code with non-numeric suffix"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_val, expected, description in test_cases:
        result = extract_tnved_code(input_val)
        
        if result == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
        
        print(f"{status} {description}")
        print(f"    Input: {repr(input_val)}")
        print(f"    Expected: {repr(expected)}")
        print(f"    Got: {repr(result)}")
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    return passed == total


def test_tnved_code_validation():
    """Test TNVED code validation."""
    print("Testing TNVED Code Validation")
    print("=" * 40)
    
    test_cases = [
        # (input, expected, description)
        ("9405210013", True, "Valid 10-digit code"),
        ("0901210009", True, "Valid code starting with 0"),
        ("9405210013_003", False, "Code with suffix"),
        ("123456789", False, "9-digit code"),
        ("12345678901", False, "11-digit code"),
        ("abcd123456", False, "Non-numeric"),
        ("", False, "Empty string"),
        (None, False, "None input"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for input_val, expected, description in test_cases:
        result = is_valid_tnved_code(input_val)
        
        if result == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
        
        print(f"{status} {description}")
        print(f"    Input: {repr(input_val)}")
        print(f"    Expected: {expected}")
        print(f"    Got: {result}")
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    return passed == total


def test_integration_with_selectors():
    """Test that selectors now return clean TNVED codes."""
    print("Testing Integration with Selectors")
    print("=" * 40)
    
    try:
        from batch_processor.services.tnved_integration import get_tnved_integration
        
        # Initialize integration
        integration = get_tnved_integration()
        
        # Create similarity selector
        selector = integration.create_selector('similarity_top1')
        
        # Test with a sample description
        test_description = "кофейные зерна арабика"
        result = selector.select_code(test_description, row_index=0)
        
        print(f"Test Description: {test_description}")
        print(f"Selected TNVED Code: {result.tnved_code}")
        print(f"Selection Reason: {result.selection_reason[:200]}...")
        
        # Validate that the returned code is clean
        if result.tnved_code:
            is_clean = is_valid_tnved_code(result.tnved_code)
            print(f"Is Clean 10-digit Code: {'✅ YES' if is_clean else '❌ NO'}")
            
            if is_clean:
                print("✅ Integration test PASSED - Clean TNVED code returned")
                return True
            else:
                print("❌ Integration test FAILED - Invalid TNVED code format")
                return False
        else:
            print("⚠️  No TNVED code assigned (this may be normal for some descriptions)")
            return True
            
    except Exception as e:
        print(f"❌ Integration test FAILED with exception: {e}")
        return False


def main():
    """Run all TNVED code extraction tests."""
    print("TNVED Code Extraction Test Suite")
    print("=" * 50)
    
    tests = [
        ("Code Extraction", test_tnved_code_extraction),
        ("Code Validation", test_tnved_code_validation),
        ("Selector Integration", test_integration_with_selectors)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! TNVED code extraction is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())