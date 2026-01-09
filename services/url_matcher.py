"""
URL Matcher for TNVED Code Matching System

This module provides URL-based TNVED code matching functionality,
performing exact URL lookups in the URL database.
"""

import logging
import signal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from services.url_database_manager import URLDatabaseManager, URLRecord


logger = logging.getLogger(__name__)


@dataclass
class URLMatchResult:
    """
    Represents the result of a URL-based code search
    
    Attributes:
        found: Whether a match was found
        tnved_code: TNVED code if found
        description: Product description if found
        source_name: Data source name if found
        original_url: Original URL from database
        normalized_url: Normalized URL used for matching
        confidence: Confidence score (1.0 for exact URL matches)
        match_type: Type of match performed
        shop_type: Shop type detected (if available)
        product_id: Product ID extracted (if available)
    """
    found: bool
    tnved_code: Optional[str] = None
    description: Optional[str] = None
    source_name: Optional[str] = None
    original_url: Optional[str] = None
    normalized_url: Optional[str] = None
    confidence: float = 1.0  # URL matches have maximum confidence
    match_type: str = "exact_url"
    shop_type: Optional[str] = None
    product_id: Optional[str] = None


class URLMatcher:
    """
    Performs URL-based TNVED code matching
    
    Features:
    - Exact URL lookup with normalization
    - URL validation and suggestion
    - Timeout handling for database queries
    - Security sanitization for logging
    """
    
    def __init__(self, url_db_manager: URLDatabaseManager, timeout_seconds: float = 5.0):
        """
        Initialize URL matcher
        
        Args:
            url_db_manager: URL database manager instance
            timeout_seconds: Timeout for URL database queries
        """
        self.url_db = url_db_manager
        self.normalizer = url_db_manager.normalizer
        self.timeout_seconds = timeout_seconds
        
        logger.info(f"URLMatcher initialized with timeout: {timeout_seconds}s")
    
    def find_code_by_url(self, url: str) -> URLMatchResult:
        """
        Finds TNVED code by URL lookup
        
        Args:
            url: Product URL to search for
            
        Returns:
            URLMatchResult with search results
        """
        if not url or not isinstance(url, str):
            logger.debug("Empty or invalid URL provided")
            return URLMatchResult(found=False)
        
        # Sanitize URL for logging
        safe_url = self.normalizer.sanitize_url_for_logging(url)
        logger.debug(f"Searching for URL: {safe_url}")
        
        try:
            # Apply timeout to URL database query
            record = self._find_with_timeout(url)
            
            if record:
                logger.info(f"URL match found: {record.tnved_code}")
                return URLMatchResult(
                    found=True,
                    tnved_code=record.tnved_code,
                    description=record.description,
                    source_name=record.source_name,
                    original_url=record.original_url,
                    normalized_url=record.normalized_url,
                    confidence=1.0,
                    match_type="exact_url",
                    shop_type=record.shop_type,
                    product_id=record.product_id
                )
            else:
                logger.debug("No URL match found")
                return URLMatchResult(found=False)
                
        except TimeoutError:
            logger.warning(f"URL search timeout for: {safe_url}")
            return URLMatchResult(found=False)
        except Exception as e:
            logger.error(f"Error during URL search: {e}")
            return URLMatchResult(found=False)
    
    def _find_with_timeout(self, url: str) -> Optional[URLRecord]:
        """
        Performs URL lookup with timeout protection
        
        Args:
            url: URL to search for
            
        Returns:
            URLRecord if found, None otherwise
            
        Raises:
            TimeoutError: If query exceeds timeout
        """
        def timeout_handler(signum, frame):
            raise TimeoutError("URL database query timeout")
        
        # Set up timeout handler (Unix-like systems only)
        old_handler = None
        try:
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(self.timeout_seconds))
            
            # Perform the actual database lookup
            result = self.url_db.find_by_url(url)
            
            # Clear timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            return result
            
        except TimeoutError:
            # Clear timeout and re-raise
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            raise
        finally:
            # Restore original signal handler
            if old_handler is not None and hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, old_handler)
    
    def validate_and_suggest_normalization(self, url: str) -> Dict[str, Any]:
        """
        Validates URL and provides normalization information
        
        Args:
            url: URL to validate
            
        Returns:
            Dictionary with validation results and suggestions
        """
        result = {
            "original_url": url,
            "is_valid": False,
            "normalized_url": None,
            "shop_type": None,
            "product_id": None,
            "domain": None,
            "suggestions": [],
            "security_issues": []
        }
        
        if not url or not isinstance(url, str):
            result["suggestions"].append("URL is empty or invalid")
            return result
        
        # Check for potential security issues
        security_issues = self._check_security_issues(url)
        result["security_issues"] = security_issues
        
        # Attempt normalization
        normalized = self.normalizer.normalize_url(url)
        if normalized:
            result.update({
                "is_valid": True,
                "normalized_url": normalized.normalized_url,
                "shop_type": normalized.shop_type,
                "product_id": normalized.product_id,
                "domain": normalized.domain
            })
            
            # Provide normalization suggestions
            if normalized.original_url != normalized.normalized_url:
                result["suggestions"].append(
                    f"URL normalized: {normalized.original_url} → {normalized.normalized_url}"
                )
            
            if normalized.shop_type:
                result["suggestions"].append(
                    f"Recognized as {normalized.shop_type} product URL"
                )
            
            if normalized.product_id:
                result["suggestions"].append(
                    f"Extracted product ID: {normalized.product_id}"
                )
        else:
            result["suggestions"].append("URL format is invalid or not supported")
        
        return result
    
    def _check_security_issues(self, url: str) -> List[str]:
        """
        Checks URL for potential security issues
        
        Args:
            url: URL to check
            
        Returns:
            List of security issues found
        """
        issues = []
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Check for credentials in URL
            if parsed.username or parsed.password:
                issues.append("URL contains authentication credentials")
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r'javascript:',
                r'data:',
                r'file:',
                r'ftp:',
                r'<script',
                r'%3Cscript'
            ]
            
            import re
            for pattern in suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    issues.append(f"Suspicious pattern detected: {pattern}")
            
            # Check for excessively long URLs (potential DoS)
            if len(url) > 2048:
                issues.append("URL exceeds recommended length limit")
            
        except Exception as e:
            issues.append(f"Error during security check: {e}")
        
        return issues
    
    def get_matcher_statistics(self) -> Dict[str, Any]:
        """
        Returns statistics about the URL matcher and database
        
        Returns:
            Dictionary with matcher statistics
        """
        try:
            db_stats = self.url_db.get_statistics()
            
            return {
                "timeout_seconds": self.timeout_seconds,
                "supported_shops": self.normalizer.get_supported_shops(),
                "database_stats": db_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting matcher statistics: {e}")
            return {"error": str(e)}