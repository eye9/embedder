"""
URL Normalizer for TNVED Code Matching System

This module provides URL normalization functionality for consistent URL processing
and storage in the URL-based code matching system.
"""

import logging
import re
from urllib.parse import urlparse, urlunparse
from typing import Optional, Dict, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class NormalizedURL:
    """
    Represents a normalized URL with metadata
    
    Attributes:
        original_url: Original URL as provided
        normalized_url: Normalized URL for database storage
        domain: Domain name extracted from URL
        product_id: Product ID extracted from URL path (if available)
        shop_type: Type of shop detected (ozon, yandex_market, etc.)
    """
    original_url: str
    normalized_url: str
    domain: str
    product_id: Optional[str] = None
    shop_type: Optional[str] = None


class URLNormalizer:
    """
    Normalizes URLs for consistent storage and matching
    
    Features:
    - Removes query parameters and fragments
    - Standardizes protocol to HTTPS
    - Extracts product IDs from known shop patterns
    - Provides shop-specific normalization rules
    """
    
    def __init__(self):
        """Initialize URL normalizer with shop-specific patterns"""
        self.shop_patterns = {
            'ozon': {
                'domain_pattern': r'ozon\.ru',
                'product_pattern': r'/product/(\d+)/?',
                'normalize_path': '/product/{product_id}/'
            },
            'yandex_market': {
                'domain_pattern': r'market\.yandex\.ru',
                'product_pattern': r'/product/(\d+)',
                'normalize_path': '/product/{product_id}'
            },
            'wildberries': {
                'domain_pattern': r'wildberries\.ru',
                'product_pattern': r'/catalog/(\d+)/',
                'normalize_path': '/catalog/{product_id}/'
            },
            'aliexpress': {
                'domain_pattern': r'aliexpress\.(ru|com)',
                'product_pattern': r'/item/(\d+)\.html',
                'normalize_path': '/item/{product_id}.html'
            }
        }
        
        logger.info(f"URLNormalizer initialized with {len(self.shop_patterns)} shop patterns")
    
    def normalize_url(self, url: str) -> Optional[NormalizedURL]:
        """
        Normalizes URL for database storage and matching
        
        Args:
            url: Original URL to normalize
            
        Returns:
            NormalizedURL object or None if URL is invalid
            
        Examples:
            >>> normalizer = URLNormalizer()
            >>> result = normalizer.normalize_url("http://ozon.ru/product/123456?ref=abc")
            >>> print(result.normalized_url)
            https://ozon.ru/product/123456/
        """
        if not url or not isinstance(url, str):
            logger.debug("Empty or invalid URL provided")
            return None
        
        url = url.strip()
        if not url:
            logger.debug("URL is empty after stripping")
            return None
        
        try:
            # Basic URL parsing
            parsed = urlparse(url)
            
            # Add protocol if missing
            if not parsed.scheme:
                url = 'https://' + url
                parsed = urlparse(url)
            elif parsed.scheme == 'http':
                # Standardize to HTTPS
                parsed = parsed._replace(scheme='https')
            
            # Validate that we have a domain
            if not parsed.netloc:
                logger.debug(f"No domain found in URL: {url}")
                return None
            
            # Remove query parameters and fragments for normalization
            clean_parsed = parsed._replace(query='', fragment='')
            
            # Identify shop type and extract product ID
            shop_type, product_id = self._identify_shop_and_extract_id(
                parsed.netloc, parsed.path
            )
            
            # Apply shop-specific normalization if recognized
            if shop_type and product_id:
                pattern_info = self.shop_patterns[shop_type]
                normalized_path = pattern_info['normalize_path'].format(
                    product_id=product_id
                )
                clean_parsed = clean_parsed._replace(path=normalized_path)
                logger.debug(f"Applied {shop_type} normalization: {normalized_path}")
            
            normalized_url = urlunparse(clean_parsed)
            
            result = NormalizedURL(
                original_url=url,
                normalized_url=normalized_url,
                domain=parsed.netloc,
                product_id=product_id,
                shop_type=shop_type
            )
            
            logger.debug(f"Normalized URL: {url} -> {normalized_url}")
            return result
            
        except Exception as e:
            logger.error(f"Error normalizing URL '{url}': {e}")
            return None
    
    def _identify_shop_and_extract_id(
        self, 
        domain: str, 
        path: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Identifies shop type and extracts product ID from URL
        
        Args:
            domain: Domain name from URL
            path: Path component from URL
            
        Returns:
            Tuple of (shop_type, product_id) or (None, None) if not recognized
        """
        for shop_type, pattern_info in self.shop_patterns.items():
            # Check if domain matches
            if re.search(pattern_info['domain_pattern'], domain, re.IGNORECASE):
                # Try to extract product ID from path
                match = re.search(pattern_info['product_pattern'], path)
                if match:
                    product_id = match.group(1)
                    logger.debug(f"Identified {shop_type} with product_id: {product_id}")
                    return shop_type, product_id
                else:
                    logger.debug(f"Domain matches {shop_type} but no product ID found")
        
        return None, None
    
    def validate_url(self, url: str) -> bool:
        """
        Validates if URL can be normalized
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid and can be normalized
        """
        normalized = self.normalize_url(url)
        return normalized is not None
    
    def sanitize_url_for_logging(self, url: str) -> str:
        """
        Sanitizes URL for safe logging by removing sensitive parameters
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL safe for logging
        """
        if not url or not isinstance(url, str):
            return "[INVALID_URL]"
        
        try:
            parsed = urlparse(url)
            
            # Remove credentials if present
            if parsed.username or parsed.password:
                parsed = parsed._replace(username=None, password=None)
            
            # Remove query parameters that might contain sensitive data
            parsed = parsed._replace(query='', fragment='')
            
            return urlunparse(parsed)
            
        except Exception:
            return "[MALFORMED_URL]"
    
    def get_supported_shops(self) -> list[str]:
        """
        Returns list of supported shop types
        
        Returns:
            List of supported shop type names
        """
        return list(self.shop_patterns.keys())