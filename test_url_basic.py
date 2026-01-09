"""
Basic test for URL processing components without database operations
"""

import logging
from services.url_normalizer import URLNormalizer
from services.url_security import URLSecurity
from services.url_config import URLProcessingConfig, URLPriority


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
    
    test_cases = [
        {
            "url": "https://ozon.ru/product/123456/?ref=abc&utm_source=google",
            "expected_shop": "ozon",
            "expected_id": "123456"
        },
        {
            "url": "http://market.yandex.ru/product/789012?clid=123",
            "expected_shop": "yandex_market",
            "expected_id": "789012"
        },
        {
            "url": "https://wildberries.ru/catalog/345678/detail.aspx?targetUrl=123",
            "expected_shop": "wildberries",
            "expected_id": "345678"
        },
        {
            "url": "https://example.com/product/555?param=value#section",
            "expected_shop": None,
            "expected_id": None
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for case in test_cases:
        result = normalizer.normalize_url(case["url"])
        if result:
            shop_match = result.shop_type == case["expected_shop"]
            id_match = result.product_id == case["expected_id"]
            
            if shop_match and id_match:
                print(f"✓ {case['url']}")
                print(f"  → {result.normalized_url}")
                passed += 1
            else:
                print(f"✗ {case['url']}")
                print(f"  Expected shop: {case['expected_shop']}, got: {result.shop_type}")
                print(f"  Expected ID: {case['expected_id']}, got: {result.product_id}")
        else:
            print(f"✗ Failed to normalize: {case['url']}")
    
    print(f"Passed: {passed}/{total}")
    return passed == total


def test_url_security():
    """Test URL security functionality"""
    print("\n=== Testing URL Security ===")
    
    security = URLSecurity()
    
    test_cases = [
        {
            "url": "https://example.com/product/123",
            "should_be_safe": True,
            "description": "Safe URL"
        },
        {
            "url": "javascript:alert('xss')",
            "should_be_safe": False,
            "description": "JavaScript injection"
        },
        {
            "url": "https://user:pass@example.com/product/123",
            "should_be_safe": True,  # Safe but has warnings
            "description": "URL with credentials"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for case in test_cases:
        validation = security.validate_url_security(case["url"])
        sanitized = security.sanitize_url_for_logging(case["url"])
        
        if validation["is_safe"] == case["should_be_safe"]:
            print(f"✓ {case['description']}: {case['url']}")
            print(f"  Safe: {validation['is_safe']}, Sanitized: {sanitized}")
            passed += 1
        else:
            print(f"✗ {case['description']}: {case['url']}")
            print(f"  Expected safe: {case['should_be_safe']}, got: {validation['is_safe']}")
    
    print(f"Passed: {passed}/{total}")
    return passed == total


def test_url_config():
    """Test URL configuration"""
    print("\n=== Testing URL Configuration ===")
    
    # Test default config
    config = URLProcessingConfig()
    
    checks = [
        ("enabled", config.enabled, True),
        ("priority", config.priority, URLPriority.FIRST),
        ("timeout_seconds", config.timeout_seconds, 5.0),
        ("collection_name", config.database.collection_name, "url_tnved_mapping"),
        ("security_enabled", config.security.enabled, True)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, actual, expected in checks:
        if actual == expected:
            print(f"✓ {name}: {actual}")
            passed += 1
        else:
            print(f"✗ {name}: expected {expected}, got {actual}")
    
    print(f"Passed: {passed}/{total}")
    return passed == total


def main():
    """Run basic tests"""
    setup_test_logging()
    
    print("Testing URL Processing Infrastructure (Basic)")
    print("=" * 50)
    
    tests = [
        ("URL Normalizer", test_url_normalizer),
        ("URL Security", test_url_security),
        ("URL Configuration", test_url_config)
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
        print("🎉 All basic tests passed! URL processing infrastructure core components are working.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit(main())