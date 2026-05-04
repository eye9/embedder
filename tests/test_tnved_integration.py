#!/usr/bin/env python3
"""
Test script for TNVED system integration with batch processor.

This script tests the integration between the batch processor and the existing
TNVED embedder system to ensure proper functionality.
"""

import logging
import sys
from pathlib import Path
import pandas as pd
import tempfile
import os
import uuid

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.services.tnved_integration import (
    get_tnved_integration, 
    TNVEDIntegrationError,
    initialize_tnved_integration
)
from batch_processor.workers.processing_task import process_file_sync


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_integration_initialization():
    """Test TNVED integration initialization."""
    print("\n=== Testing TNVED Integration Initialization ===")
    
    try:
        # Initialize integration
        integration = get_tnved_integration()
        
        # Get system info
        system_info = integration.get_system_info()
        print(f"Integration Status: {system_info['status']}")
        
        if system_info['status'] == 'initialized':
            print(f"Database Records: {system_info['database']['total_records']}")
            print(f"Model: {system_info['model']['name']}")
            print(f"Device: {system_info['model']['device']}")
            print(f"Available Algorithms: {system_info['algorithms']}")
            return True
        else:
            print(f"Integration failed: {system_info.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Integration initialization failed: {e}")
        return False


def test_search_functionality():
    """Test TNVED search functionality."""
    print("\n=== Testing TNVED Search Functionality ===")
    
    try:
        integration = get_tnved_integration()
        
        # Test with sample queries
        test_queries = [
            "кофейные зерна арабика",
            "хлопковая ткань",
            "стальные трубы",
            "пластиковые игрушки"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: '{query}'")
            
            # Get TNVED searcher
            searcher = integration.get_tnved_searcher()
            
            # Perform search
            results = searcher.search(query, top_k=3)
            
            if results:
                print(f"  Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print(f"    {i}. Code: {result.code}")
                    print(f"       Score: {result.similarity_score:.3f}")
                    print(f"       Description: {result.description[:100]}...")
            else:
                print("  No results found")
        
        return True
        
    except Exception as e:
        print(f"Search functionality test failed: {e}")
        return False


def test_selector_functionality():
    """Test TNVED selector functionality."""
    print("\n=== Testing TNVED Selector Functionality ===")
    
    try:
        integration = get_tnved_integration()
        
        # Test similarity selector
        print("\nTesting similarity_top1 selector:")
        similarity_selector = integration.create_selector('similarity_top1')
        
        test_description = "кофейные зерна арабика высшего качества"
        result = similarity_selector.select_code(test_description, row_index=0)
        
        print(f"  Input: {test_description}")
        print(f"  Selected Code: {result.tnved_code}")
        print(f"  Confidence: {result.confidence_score}")
        print(f"  Reason: {result.selection_reason[:200]}...")
        
        # Test LLM selector if available
        try:
            print("\nTesting llm_reasoning selector:")
            llm_selector = integration.create_selector('llm_reasoning')
            
            result = llm_selector.select_code(test_description, row_index=0)
            
            print(f"  Input: {test_description}")
            print(f"  Selected Code: {result.tnved_code}")
            print(f"  Confidence: {result.confidence_score}")
            print(f"  Reason: {result.selection_reason[:200]}...")
            
        except Exception as e:
            print(f"  LLM selector test failed (expected if no API key): {e}")
        
        return True
        
    except Exception as e:
        print(f"Selector functionality test failed: {e}")
        return False


def create_test_excel_file():
    """Create a test Excel file for processing."""
    # Create test data
    test_data = {
        'Product Detailed Description': [
            'Кофейные зерна арабика высшего качества',
            'Хлопковая ткань для одежды',
            'Стальные трубы диаметром 50мм',
            'Пластиковые игрушки для детей',
            'Натуральный мед цветочный'
        ],
        'HTS Code': ['', '', '7304.31.6000', '', ''],  # Some existing codes
        'Quantity': [100, 50, 200, 75, 30],
        'Unit Price': [25.50, 15.00, 45.00, 8.99, 12.00]
    }
    
    df = pd.DataFrame(test_data)
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    temp_file.close()
    
    # Write Excel file
    df.to_excel(temp_file.name, index=False, engine='openpyxl')
    
    return temp_file.name


def test_file_processing():
    """Test complete file processing workflow."""
    print("\n=== Testing File Processing Workflow ===")
    
    try:
        # Create test Excel file
        test_file = create_test_excel_file()
        print(f"Created test file: {test_file}")
        
        # Test processing in "all" mode
        print("\nTesting 'all' processing mode:")
        result = process_file_sync(
            session_id=str(uuid.uuid4()),
            file_path=test_file,
            process_mode="all",
            algorithm="similarity_top1"
        )
        
        print(f"  Status: {result['status']}")
        if result['status'] == 'completed':
            print(f"  Processed Rows: {result['processed_rows']}")
            print(f"  Total Rows: {result['total_rows']}")
            print(f"  Error Count: {result['error_count']}")
            print(f"  Processing Time: {result['processing_time_seconds']:.2f}s")
            print(f"  Output File: {result['output_file']}")
            
            # Check if output file exists and has correct structure
            if os.path.exists(result['output_file']):
                output_df = pd.read_excel(result['output_file'])
                print(f"  Output columns: {list(output_df.columns)}")
                print(f"  TNVED codes assigned: {output_df['TNVED_Code'].notna().sum()}")
            else:
                print("  Warning: Output file not found")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")
        
        # Test processing in "empty_only" mode
        print("\nTesting 'empty_only' processing mode:")
        result = process_file_sync(
            session_id=str(uuid.uuid4()),
            file_path=test_file,
            process_mode="empty_only",
            algorithm="similarity_top1"
        )
        
        print(f"  Status: {result['status']}")
        if result['status'] == 'completed':
            print(f"  Processed Rows: {result['processed_rows']}")
            print(f"  Total Rows: {result['total_rows']}")
            print(f"  Error Count: {result['error_count']}")
            print(f"  Processing Time: {result['processing_time_seconds']:.2f}s")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")
        
        # Clean up
        try:
            os.unlink(test_file)
            if 'output_file' in result and os.path.exists(result['output_file']):
                os.unlink(result['output_file'])
        except:
            pass
        
        return result['status'] == 'completed'
        
    except Exception as e:
        print(f"File processing test failed: {e}")
        return False


def test_integration_test():
    """Run the built-in integration test."""
    print("\n=== Running Built-in Integration Test ===")
    
    try:
        integration = get_tnved_integration()
        
        # Run integration test
        test_result = integration.test_integration()
        
        print(f"Test Status: {test_result['status']}")
        
        if test_result['status'] == 'success':
            print(f"Test Query: {test_result['test_query']}")
            print(f"Search Results Count: {test_result['search_results_count']}")
            
            if test_result['top_result']:
                top = test_result['top_result']
                print(f"Top Result:")
                print(f"  Code: {top['code']}")
                print(f"  Score: {top['similarity_score']:.3f}")
                print(f"  Description: {top['description']}")
            
            selector_result = test_result['selector_result']
            print(f"Selector Result:")
            print(f"  TNVED Code: {selector_result['tnved_code']}")
            print(f"  Confidence: {selector_result['confidence_score']}")
            print(f"  Has Error: {selector_result['has_error']}")
            
            return True
        else:
            print(f"Test failed: {test_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Integration test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("TNVED System Integration Test Suite")
    print("=" * 50)
    
    # Track test results
    tests = [
        ("Integration Initialization", test_integration_initialization),
        ("Search Functionality", test_search_functionality),
        ("Selector Functionality", test_selector_functionality),
        ("Built-in Integration Test", test_integration_test),
        ("File Processing Workflow", test_file_processing)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\nTest '{test_name}' crashed: {e}")
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
        print("✅ All tests passed! TNVED integration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())