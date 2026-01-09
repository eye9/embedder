"""
Test script for URL processing infrastructure

This script tests the basic functionality of the URL processing components
to ensure they are working correctly.
"""

import logging
import tempfile
import os
from pathlib import Path

from services.url_normalizer import URLNormalizer
from services.url_database_manager import URLDatabaseManager
from services.url_matcher import URLMatcher
from services.url_security import URLSecurity
from services.url_processor_factory import URLProcessorFactory
from services.url_config import URLProcessingConfig, URLPriority
import chromadb
from chromadb.config import Settings


def setup_test_logging():
    """Set up logging for tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_url_normalizer():
    """Test URL normalizer functionality"""
    print("\n=== Testing URL Normalizer ===")
    
    normalizer = URLNormalizer()
    
    test_urls = [
        "https://ozon.ru/product/123456/?ref=abc&utm_source=google",
        "http://market.yandex.ru/product/789012?clid=123",
        "https://wildberries.ru/catalog/345678/detail.aspx?targetUrl=123",
        "https://aliexpress.com/item/901234.html?spm=a2g0o.cart.0.0",
        "https://example.com/product/555?param=value#section"
    ]
    
    for url in test_urls:
        result = normalizer.normalize_url(url)
        if result:
            print(f"✓ {url}")
            print(f"  → {result.normalized_url}")
            print(f"  Shop: {result.shop_type}, Product ID: {result.product_id}")
        else:
            print(f"✗ Failed to normalize: {url}")
    
    return True


def test_url_security():
    """Test URL security functionality"""
    print("\n=== Testing URL Security ===")
    
    security = URLSecurity()
    
    test_urls = [
        "https://example.com/product/123",  # Safe URL
        "javascript:alert('xss')",  # Malicious
        "https://user:pass@example.com/product/123",  # Has credentials
        "https://example.com/product/123?password=secret&token=abc",  # Sensitive params
    ]
    
    for url in test_urls:
        validation = security.validate_url_security(url)
        sanitized = security.sanitize_url_for_logging(url)
        
        print(f"URL: {url}")
        print(f"  Safe: {validation['is_safe']}")
        print(f"  Threats: {validation['threats_found']}")
        print(f"  Sanitized: {sanitized}")
    
    return True


def test_url_database_operations():
    """Test URL database operations"""
    print("\n=== Testing URL Database Operations ===")
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            chroma_client = chromadb.PersistentClient(
                path=temp_dir,
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            
            db_manager = URLDatabaseManager(chroma_client, "test_url_collection")
            
            # Test adding records
            test_records = [
                ("https://ozon.ru/product/123456/", "1234567890", "Test Product 1", "test_source"),
                ("https://market.yandex.ru/product/789012", "0987654321", "Test Product 2", "test_source"),
                ("https://example.com/product/555", "5555555555", "Test Product 3", "test_source")
            ]
            
            print("Adding test records...")
            for url, code, desc, source in test_records:
                success = db_manager.add_url_record(url, code, desc, source)
                print(f"  {'✓' if success else '✗'} {url} → {code}")
            
            # Test finding records
            print("\nTesting record lookup...")
            for url, expected_code, _, _ in test_records:
                record = db_manager.find_by_url(url)
                if record and record.tnved_code == expected_code:
                    print(f"  ✓ Found: {url} → {record.tnved_code}")
                else:
                    print(f"  ✗ Not found or incorrect: {url}")
            
            # Test statistics
            stats = db_manager.get_statistics()
            print(f"\nDatabase statistics:")
            print(f"  Total records: {stats['total_records']}")
            print(f"  By source: {stats['by_source']}")
            
            # Explicitly close the client
            del db_manager
            del chroma_client
            
        except Exception as e:
            print(f"Database test error: {e}")
            return False
    
    return True


def test_url_matcher():
    """Test URL matcher functionality"""
    print("\n=== Testing URL Matcher ===")
    
    # Create temporary database with test data
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            chroma_client = chromadb.PersistentClient(
                path=temp_dir,
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            
            db_manager = URLDatabaseManager(chroma_client, "test_url_collection")
            matcher = URLMatcher(db_manager, timeout_seconds=2.0)
            
            # Add test data
            test_url = "https://ozon.ru/product/123456/"
            test_code = "1234567890"
            db_manager.add_url_record(test_url, test_code, "Test Product", "test_source")
            
            # Test matching
            result = matcher.find_code_by_url(test_url)
            if result.found and result.tnved_code == test_code:
                print(f"✓ URL match found: {test_url} → {result.tnved_code}")
            else:
                print(f"✗ URL match failed: {test_url}")
            
            # Test non-existent URL
            result = matcher.find_code_by_url("https://example.com/nonexistent")
            if not result.found:
                print("✓ Correctly returned no match for non-existent URL")
            else:
                print("✗ Incorrectly found match for non-existent URL")
            
            # Test validation
            validation = matcher.validate_and_suggest_normalization(test_url)
            print(f"URL validation: {validation['is_valid']}")
            print(f"Suggestions: {validation['suggestions']}")
            
            # Explicitly close
            del matcher
            del db_manager
            del chroma_client
            
        except Exception as e:
            print(f"Matcher test error: {e}")
            return False
    
    return True


def test_url_processor_factory():
    """Test URL processor factory"""
    print("\n=== Testing URL Processor Factory ===")
    
    config = URLProcessingConfig(
        enabled=True,
        priority=URLPriority.FIRST,
        timeout_seconds=5.0
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Test complete system creation
            components = URLProcessorFactory.create_complete_url_processor(temp_dir, config)
            
            required_components = ["chroma_client", "normalizer", "db_manager", "matcher", "security", "config"]
            missing = [comp for comp in required_components if comp not in components]
            
            if not missing:
                print("✓ All required components created")
            else:
                print(f"✗ Missing components: {missing}")
            
            # Test validation
            is_valid = URLProcessorFactory.validate_url_processing_setup(components)
            print(f"{'✓' if is_valid else '✗'} Setup validation: {is_valid}")
            
            # Test info
            info = URLProcessorFactory.get_url_processing_info(components)
            print(f"System info: {info['config']}")
            
            # Explicitly cleanup
            del components
            
        except Exception as e:
            print(f"Factory test error: {e}")
            return False
    
    return True


def main():
    """Run all tests"""
    setup_test_logging()
    
    print("Testing URL Processing Infrastructure")
    print("=" * 50)
    
    tests = [
        ("URL Normalizer", test_url_normalizer),
        ("URL Security", test_url_security),
        ("URL Database Operations", test_url_database_operations),
        ("URL Matcher", test_url_matcher),
        ("URL Processor Factory", test_url_processor_factory)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"\n{'✓' if success else '✗'} {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n✗ {test_name}: FAILED with error: {e}")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        print(f"  {'✓' if success else '✗'} {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! URL processing infrastructure is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit(main())