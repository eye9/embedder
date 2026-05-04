#!/usr/bin/env python3
"""
Test script for URL security and logging enhancements

This script tests the enhanced URL security features including
violation tracking, parameterized query protection, and security logging.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from services.url_security import URLSecurity, SecurityViolation
from batch_processor.services.security_logger import SecurityLogger, get_security_logger


def test_basic_security_validation():
    """Test basic URL security validation"""
    print("=== Testing Basic Security Validation ===")
    
    security = URLSecurity()
    
    # Test safe URL
    safe_url = "https://ozon.ru/product/12345/"
    result = security.validate_url_security(safe_url)
    print(f"Safe URL: {result['is_safe']} - {safe_url}")
    
    # Test malicious URL
    malicious_url = "https://example.com/product?id=1'; DROP TABLE users; --"
    result = security.validate_url_security(malicious_url)
    print(f"Malicious URL: {result['is_safe']} - Threats: {len(result['threats_found'])}")
    
    # Test URL with credentials
    cred_url = "https://user:password@example.com/product/123"
    result = security.validate_url_security(cred_url)
    print(f"URL with credentials: {result['is_safe']} - Warnings: {len(result['warnings'])}")
    
    print()


def test_enhanced_sanitization():
    """Test enhanced URL sanitization"""
    print("=== Testing Enhanced URL Sanitization ===")
    
    security = URLSecurity()
    
    test_urls = [
        "https://user:pass@example.com/product?token=secret123&id=456",
        "https://example.com/search?q=<script>alert('xss')</script>",
        "https://example.com/api?key=abc123&password=secret",
        "javascript:alert('malicious')"
    ]
    
    for url in test_urls:
        sanitized_storage = security.sanitize_url_for_storage(url)
        sanitized_logging = security.sanitize_url_for_logging(url, mask_level="aggressive")
        query_safe = security.create_parameterized_query_safe_string(url)
        
        print(f"Original: {url}")
        print(f"  Storage: {sanitized_storage}")
        print(f"  Logging: {sanitized_logging}")
        print(f"  Query Safe: {query_safe}")
        print()


def test_violation_tracking():
    """Test security violation tracking"""
    print("=== Testing Security Violation Tracking ===")
    
    security = URLSecurity(enable_violation_tracking=True)
    
    # Test various malicious URLs to trigger violations
    malicious_urls = [
        "javascript:alert('xss')",
        "https://example.com/'; DROP TABLE users; --",
        "https://user:password@example.com/secret",
        "file:///etc/passwd",
        "https://example.com/search?q=<script>alert(1)</script>"
    ]
    
    for url in malicious_urls:
        result = security.validate_url_security(url, source_ip="192.168.1.100", user_agent="TestAgent/1.0")
        print(f"URL: {url[:50]}... - Safe: {result['is_safe']} - Violations: {result.get('violations_recorded', 0)}")
    
    # Get violation summary
    summary = security.get_security_violation_summary()
    print(f"\nViolation Summary:")
    print(f"  Total violations: {summary['total_violations']}")
    print(f"  Violations by type: {summary['violations_by_type']}")
    print(f"  Blocked patterns: {summary['blocked_patterns_count']}")
    
    print()


def test_batch_validation():
    """Test batch URL validation with enhanced reporting"""
    print("=== Testing Batch URL Validation ===")
    
    security = URLSecurity(enable_violation_tracking=True)
    
    test_urls = [
        "https://ozon.ru/product/12345/",
        "https://yandex.ru/market/product/67890",
        "javascript:alert('malicious')",
        "https://example.com/'; DROP TABLE users; --",
        "https://user:pass@example.com/secret",
        "https://wildberries.ru/catalog/11111/",
        "file:///etc/passwd",
        "https://aliexpress.com/item/22222.html"
    ]
    
    results = security.validate_batch_urls(test_urls, source_ip="192.168.1.100", user_agent="TestAgent/1.0")
    
    print(f"Batch validation results:")
    print(f"  Total URLs: {results['total_urls']}")
    print(f"  Safe URLs: {results['safe_urls']}")
    print(f"  Unsafe URLs: {results['unsafe_urls']}")
    print(f"  Total violations: {results['total_violations']}")
    print(f"  Processing time: {results['processing_time_ms']:.2f}ms")
    print(f"  Threats by type: {results['threats_by_type']}")
    print(f"  Violations by severity: {results['violations_by_severity']}")
    
    print()


def test_security_logging():
    """Test security logging functionality"""
    print("=== Testing Security Logging ===")
    
    # Get security logger
    sec_logger = get_security_logger()
    
    # Test various log types
    sec_logger.log_security_violation(
        violation_type="malicious_pattern",
        severity="high",
        message="SQL injection attempt detected",
        url="https://example.com/'; DROP TABLE users; --",
        source_ip="192.168.1.100",
        user_agent="BadBot/1.0",
        additional_data={"pattern": "drop table", "blocked": True}
    )
    
    sec_logger.log_url_processing_event(
        event_type="normalization",
        message="URL normalized successfully",
        url="https://ozon.ru/product/12345/?utm_source=google",
        processing_time_ms=2.5,
        additional_data={"original_params": 1, "removed_params": 1}
    )
    
    sec_logger.log_batch_processing_summary(
        total_urls=100,
        safe_urls=85,
        violations=15,
        processing_time_ms=1250.0,
        additional_stats={"avg_url_length": 65, "unique_domains": 12}
    )
    
    # Get statistics
    stats = sec_logger.get_security_statistics()
    print(f"Security logging statistics:")
    print(f"  Event counters: {stats['event_counters']}")
    print(f"  Structured logging: {stats['structured_logging_enabled']}")
    print(f"  Data masking: {stats['sensitive_data_masking_enabled']}")
    
    print()


def test_parameterized_query_protection():
    """Test enhanced parameterized query protection"""
    print("=== Testing Parameterized Query Protection ===")
    
    security = URLSecurity()
    
    dangerous_urls = [
        "https://example.com/'; DROP TABLE users; --",
        "https://example.com/search?q=1' UNION SELECT * FROM passwords --",
        "https://example.com/api?exec=xp_cmdshell('dir')",
        "https://example.com/page?id=1; DELETE FROM products; --",
        "https://example.com/search?term=<script>alert('xss')</script>"
    ]
    
    for url in dangerous_urls:
        safe_query = security.create_parameterized_query_safe_string(url)
        print(f"Original: {url}")
        print(f"Query Safe: {safe_query}")
        print()


def main():
    """Run all security enhancement tests"""
    print("URL Security and Logging Enhancements Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_basic_security_validation()
        test_enhanced_sanitization()
        test_violation_tracking()
        test_batch_validation()
        test_security_logging()
        test_parameterized_query_protection()
        
        print("✅ All security enhancement tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()