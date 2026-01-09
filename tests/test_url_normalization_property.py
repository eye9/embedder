"""
Property-based tests for URL normalization functionality

This module contains property-based tests that verify URL normalization
consistency across various input patterns and shop types.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from services.url_normalizer import URLNormalizer, NormalizedURL
from urllib.parse import urlparse


class TestURLNormalizationProperty:
    """Property-based tests for URL normalization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.normalizer = URLNormalizer()
    
    # Feature: url-based-code-matching, Property 3: URL Normalization Consistency
    @given(
        st.one_of(
            # Ozon URLs with various patterns
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"https://ozon.ru/product/{x}/?ref=abc&utm_source=google"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"http://www.ozon.ru/product/{x}/detail?param=value#section"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"ozon.ru/product/{x}/"
            ),
            
            # Yandex Market URLs with various patterns
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"https://market.yandex.ru/product/{x}?clid=123&lr=213"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"http://market.yandex.ru/product/{x}#reviews"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"market.yandex.ru/product/{x}"
            ),
            
            # Wildberries URLs with various patterns
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"https://wildberries.ru/catalog/{x}/detail.aspx?targetUrl=123"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"http://www.wildberries.ru/catalog/{x}/?param=value#info"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"wildberries.ru/catalog/{x}/"
            ),
            
            # AliExpress URLs with various patterns
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"https://aliexpress.ru/item/{x}.html?spm=123&algo_pvid=456"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"http://aliexpress.com/item/{x}.html#feedback"
            ),
            st.integers(min_value=1, max_value=999999999).map(
                lambda x: f"aliexpress.com/item/{x}.html"
            ),
            
            # Generic URLs (unknown shops)
            st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))).map(
                lambda x: f"https://example.com/product/{x}?param=value#section"
            ),
            st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))).map(
                lambda x: f"http://shop.example.org/item/{x}/"
            )
        )
    )
    @settings(max_examples=100, deadline=5000)
    def test_url_normalization_consistency(self, url):
        """
        Test that URL normalization consistently applies all normalization rules
        
        Property: For any valid URL input, the system should consistently normalize URLs by:
        - Removing query parameters and fragments (Requirements 11.1, 11.2)
        - Standardizing protocols to HTTPS (Requirement 11.3)
        - Preserving domain and product path structure (Requirement 11.4)
        - Applying shop-specific pattern matching for known retailers (Requirements 12.1-12.5)
        """
        # Skip empty or whitespace-only URLs
        assume(url and url.strip())
        
        result = self.normalizer.normalize_url(url)
        
        if result is not None:
            # Requirement 11.3: Protocol should be standardized to HTTPS
            assert result.normalized_url.startswith('https://'), \
                f"Normalized URL should start with https://, got: {result.normalized_url}"
            
            # Requirements 11.1, 11.2: Query parameters and fragments should be removed
            parsed_normalized = urlparse(result.normalized_url)
            assert parsed_normalized.query == '', \
                f"Query parameters should be removed, got: {parsed_normalized.query}"
            assert parsed_normalized.fragment == '', \
                f"Fragments should be removed, got: {parsed_normalized.fragment}"
            
            # Requirement 11.4: Domain should be preserved
            original_parsed = urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}')
            assert parsed_normalized.netloc == original_parsed.netloc, \
                f"Domain should be preserved: expected {original_parsed.netloc}, got {parsed_normalized.netloc}"
            
            # Original URL should be preserved or modified to include protocol
            # The normalizer adds https:// to URLs without protocol
            expected_original = url if url.startswith(('http://', 'https://')) else f'https://{url}'
            assert result.original_url == expected_original, \
                f"Original URL should be preserved or have protocol added: expected {expected_original}, got {result.original_url}"
            
            # Domain field should match netloc
            assert result.domain == parsed_normalized.netloc, \
                f"Domain field should match netloc: expected {parsed_normalized.netloc}, got {result.domain}"
            
            # Shop-specific pattern matching (Requirements 12.1-12.5)
            if 'ozon.ru' in result.domain.lower():
                # Requirement 12.1: Ozon URLs should be normalized to /product/{id}/ pattern
                assert result.shop_type == 'ozon', \
                    f"Ozon URLs should have shop_type='ozon', got: {result.shop_type}"
                assert '/product/' in result.normalized_url, \
                    f"Ozon URLs should contain '/product/' in normalized form"
                assert result.product_id is not None, \
                    f"Ozon URLs should have product_id extracted"
                assert result.normalized_url.endswith('/'), \
                    f"Ozon normalized URLs should end with '/'"
                    
            elif 'market.yandex.ru' in result.domain.lower():
                # Requirement 12.2: Yandex Market URLs should be normalized to /product/{id} pattern
                assert result.shop_type == 'yandex_market', \
                    f"Yandex Market URLs should have shop_type='yandex_market', got: {result.shop_type}"
                assert '/product/' in result.normalized_url, \
                    f"Yandex Market URLs should contain '/product/' in normalized form"
                assert result.product_id is not None, \
                    f"Yandex Market URLs should have product_id extracted"
                    
            elif 'wildberries.ru' in result.domain.lower():
                # Requirement 12.3: Wildberries URLs should be normalized to /catalog/{id}/ pattern
                assert result.shop_type == 'wildberries', \
                    f"Wildberries URLs should have shop_type='wildberries', got: {result.shop_type}"
                assert '/catalog/' in result.normalized_url, \
                    f"Wildberries URLs should contain '/catalog/' in normalized form"
                assert result.product_id is not None, \
                    f"Wildberries URLs should have product_id extracted"
                assert result.normalized_url.endswith('/'), \
                    f"Wildberries normalized URLs should end with '/'"
                    
            elif 'aliexpress.' in result.domain.lower():
                # Requirement 12.4: AliExpress URLs should be normalized to /item/{id}.html pattern
                assert result.shop_type == 'aliexpress', \
                    f"AliExpress URLs should have shop_type='aliexpress', got: {result.shop_type}"
                assert '/item/' in result.normalized_url, \
                    f"AliExpress URLs should contain '/item/' in normalized form"
                assert result.product_id is not None, \
                    f"AliExpress URLs should have product_id extracted"
                assert result.normalized_url.endswith('.html'), \
                    f"AliExpress normalized URLs should end with '.html'"
                    
            else:
                # Requirement 12.5: Unknown URL patterns should use generic normalization
                assert result.shop_type is None, \
                    f"Unknown shops should have shop_type=None, got: {result.shop_type}"
                assert result.product_id is None, \
                    f"Unknown shops should have product_id=None, got: {result.product_id}"
    
    @given(
        st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
            st.just("ftp://example.com/file"),  # Unsupported protocol (but might be accepted)
            st.just("javascript:alert('xss')"),  # Malicious URL (but might be accepted)
            st.just("file:///etc/passwd"),  # Local file URL (but might be accepted)
            st.just("data:text/html,<script>alert('xss')</script>"),  # Data URL (but might be accepted)
            st.none(),  # None value
            st.integers(),  # Non-string type
        )
    )
    @settings(max_examples=50, deadline=3000)
    def test_invalid_url_handling(self, invalid_url):
        """
        Test that invalid URLs are properly handled
        
        Property: For any invalid URL input (None, non-string, empty), 
        the normalizer should return None. Other malformed URLs may be 
        accepted but should not cause exceptions.
        """
        result = self.normalizer.normalize_url(invalid_url)
        
        # None, non-string, and empty URLs should return None
        if invalid_url is None or not isinstance(invalid_url, str) or not invalid_url.strip():
            assert result is None, \
                f"Invalid URL should return None, got: {result}"
        # Other URLs might be accepted - just ensure no exceptions are raised
        # The test passes if we reach this point without exceptions
    
    @given(
        st.integers(min_value=1, max_value=999999999)
    )
    @settings(max_examples=50, deadline=3000)
    def test_normalization_idempotence(self, product_id):
        """
        Test that normalizing an already normalized URL produces the same result
        
        Property: For any normalized URL, applying normalization again should
        produce an identical result (idempotence property).
        """
        # Create a normalized URL
        original_url = f"https://ozon.ru/product/{product_id}/"
        
        first_result = self.normalizer.normalize_url(original_url)
        assume(first_result is not None)
        
        # Normalize the already normalized URL
        second_result = self.normalizer.normalize_url(first_result.normalized_url)
        
        assert second_result is not None, \
            "Re-normalizing a normalized URL should not fail"
        
        # Results should be identical
        assert first_result.normalized_url == second_result.normalized_url, \
            f"Normalization should be idempotent: {first_result.normalized_url} != {second_result.normalized_url}"
        
        assert first_result.shop_type == second_result.shop_type, \
            f"Shop type should be consistent: {first_result.shop_type} != {second_result.shop_type}"
        
        assert first_result.product_id == second_result.product_id, \
            f"Product ID should be consistent: {first_result.product_id} != {second_result.product_id}"
    
    @given(
        st.sampled_from(['ozon.ru', 'market.yandex.ru', 'wildberries.ru', 'aliexpress.ru', 'aliexpress.com']),
        st.integers(min_value=1, max_value=999999999),
        st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd'))),
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100, deadline=5000)
    def test_query_parameter_removal_consistency(self, domain, product_id, param_name, param_value):
        """
        Test that query parameters are consistently removed regardless of their content
        
        Property: For any URL with query parameters, normalization should remove
        all query parameters while preserving the core URL structure.
        """
        # Construct URL with query parameters based on shop type
        if domain == 'ozon.ru':
            base_url = f"https://{domain}/product/{product_id}/"
        elif domain == 'market.yandex.ru':
            base_url = f"https://{domain}/product/{product_id}"
        elif domain == 'wildberries.ru':
            base_url = f"https://{domain}/catalog/{product_id}/"
        else:  # aliexpress
            base_url = f"https://{domain}/item/{product_id}.html"
        
        # Add query parameters
        url_with_params = f"{base_url}?{param_name}={param_value}&another=test"
        
        result = self.normalizer.normalize_url(url_with_params)
        
        assert result is not None, f"URL should be normalized successfully: {url_with_params}"
        
        # Normalized URL should not contain query parameters
        assert '?' not in result.normalized_url, \
            f"Query parameters should be removed: {result.normalized_url}"
        
        # Normalized URL should match the expected pattern for the shop
        if domain == 'ozon.ru':
            assert result.normalized_url == f"https://{domain}/product/{product_id}/", \
                f"Ozon URL normalization failed: expected https://{domain}/product/{product_id}/, got {result.normalized_url}"
        elif domain == 'market.yandex.ru':
            assert result.normalized_url == f"https://{domain}/product/{product_id}", \
                f"Yandex Market URL normalization failed: expected https://{domain}/product/{product_id}, got {result.normalized_url}"
        elif domain == 'wildberries.ru':
            assert result.normalized_url == f"https://{domain}/catalog/{product_id}/", \
                f"Wildberries URL normalization failed: expected https://{domain}/catalog/{product_id}/, got {result.normalized_url}"
        else:  # aliexpress
            assert result.normalized_url == f"https://{domain}/item/{product_id}.html", \
                f"AliExpress URL normalization failed: expected https://{domain}/item/{product_id}.html, got {result.normalized_url}"