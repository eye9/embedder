"""
URL Security and Sanitization for TNVED Code Matching System

This module provides security features for URL processing, including
input validation, sanitization, and protection against common attacks.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, quote, unquote


logger = logging.getLogger(__name__)


class URLSecurityError(Exception):
    """Raised when URL security validation fails"""
    pass


class URLSecurity:
    """
    Provides URL security validation and sanitization
    
    Features:
    - Input validation against malicious patterns
    - URL sanitization for safe storage and logging
    - Parameter masking for sensitive data
    - SQL injection prevention for database queries
    """
    
    def __init__(self):
        """Initialize URL security validator"""
        # Patterns that indicate potential security threats
        self.malicious_patterns = [
            # Script injection patterns
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            
            # Data URI schemes that could be dangerous
            r'data:text/html',
            r'data:application/javascript',
            
            # File system access
            r'file://',
            r'\.\./',
            r'%2e%2e%2f',
            
            # Protocol manipulation
            r'ftp://',
            r'ldap://',
            r'gopher://',
            
            # SQL injection patterns in URLs
            r'union\s+select',
            r'drop\s+table',
            r'insert\s+into',
            r'delete\s+from',
            
            # Command injection
            r';\s*rm\s+',
            r';\s*cat\s+',
            r';\s*ls\s+',
            r'`[^`]*`',
            r'\$\([^)]*\)',
        ]
        
        # Sensitive parameter names to mask in logs
        self.sensitive_params = [
            'password', 'pwd', 'pass', 'secret', 'key', 'token',
            'auth', 'session', 'sid', 'api_key', 'access_token',
            'refresh_token', 'oauth', 'credential', 'login'
        ]
        
        logger.info("URLSecurity initialized with security patterns")
    
    def validate_url_security(self, url: str) -> Dict[str, Any]:
        """
        Validates URL for security threats
        
        Args:
            url: URL to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_safe": True,
            "threats_found": [],
            "warnings": [],
            "sanitized_url": url
        }
        
        if not url or not isinstance(url, str):
            result["is_safe"] = False
            result["threats_found"].append("Invalid or empty URL")
            return result
        
        try:
            # Check for malicious patterns
            threats = self._detect_malicious_patterns(url)
            if threats:
                result["is_safe"] = False
                result["threats_found"].extend(threats)
            
            # Check URL structure
            structure_issues = self._validate_url_structure(url)
            if structure_issues:
                result["warnings"].extend(structure_issues)
            
            # Generate sanitized version
            result["sanitized_url"] = self.sanitize_url_for_storage(url)
            
            # Check for credentials
            if self._has_credentials(url):
                result["warnings"].append("URL contains authentication credentials")
            
            # Check length
            if len(url) > 2048:
                result["warnings"].append("URL exceeds recommended length limit")
            
        except Exception as e:
            logger.error(f"Error during URL security validation: {e}")
            result["is_safe"] = False
            result["threats_found"].append(f"Validation error: {e}")
        
        return result
    
    def sanitize_url_for_storage(self, url: str) -> str:
        """
        Sanitizes URL for safe database storage
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL safe for storage
        """
        if not url or not isinstance(url, str):
            return ""
        
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Remove credentials by reconstructing URL without them
            if parsed.username or parsed.password:
                # Reconstruct URL without credentials
                netloc = parsed.hostname
                if parsed.port:
                    netloc = f"{netloc}:{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
                logger.debug("Removed credentials from URL for storage")
            
            # URL encode any potentially dangerous characters
            safe_url = parsed.geturl()
            
            # Remove or encode dangerous characters
            safe_url = self._encode_dangerous_chars(safe_url)
            
            return safe_url
            
        except Exception as e:
            logger.error(f"Error sanitizing URL for storage: {e}")
            return ""
    
    def sanitize_url_for_logging(self, url: str) -> str:
        """
        Sanitizes URL for safe logging with parameter masking
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL safe for logging
        """
        if not url or not isinstance(url, str):
            return "[INVALID_URL]"
        
        try:
            parsed = urlparse(url)
            
            # Remove credentials by reconstructing URL without them
            if parsed.username or parsed.password:
                # Reconstruct URL without credentials
                netloc = parsed.hostname
                if parsed.port:
                    netloc = f"{netloc}:{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
            
            # Mask sensitive query parameters
            if parsed.query:
                masked_query = self._mask_sensitive_params(parsed.query)
                parsed = parsed._replace(query=masked_query)
            
            # Remove fragment for logging
            parsed = parsed._replace(fragment='')
            
            return parsed.geturl()
            
        except Exception as e:
            logger.error(f"Error sanitizing URL for logging: {e}")
            return "[MALFORMED_URL]"
    
    def create_parameterized_query_safe_string(self, url: str) -> str:
        """
        Creates a URL string safe for parameterized database queries
        
        Args:
            url: URL to make safe
            
        Returns:
            URL string safe for database queries
        """
        if not url or not isinstance(url, str):
            return ""
        
        try:
            # Basic sanitization
            sanitized = self.sanitize_url_for_storage(url)
            
            # Additional escaping for database safety
            # Note: This is additional protection, parameterized queries
            # should still be used as the primary defense
            safe_url = sanitized.replace("'", "''")  # Escape single quotes
            safe_url = safe_url.replace(";", "")     # Remove semicolons
            safe_url = safe_url.replace("--", "")    # Remove SQL comments
            
            return safe_url
            
        except Exception as e:
            logger.error(f"Error creating query-safe URL: {e}")
            return ""
    
    def _detect_malicious_patterns(self, url: str) -> List[str]:
        """Detects malicious patterns in URL"""
        threats = []
        
        for pattern in self.malicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                threats.append(f"Malicious pattern detected: {pattern}")
        
        return threats
    
    def _validate_url_structure(self, url: str) -> List[str]:
        """Validates basic URL structure"""
        issues = []
        
        try:
            parsed = urlparse(url)
            
            # Check for valid scheme
            if parsed.scheme not in ['http', 'https']:
                issues.append(f"Unsupported URL scheme: {parsed.scheme}")
            
            # Check for valid netloc
            if not parsed.netloc:
                issues.append("URL missing domain name")
            
            # Check for suspicious characters in domain
            if parsed.netloc and re.search(r'[<>"\']', parsed.netloc):
                issues.append("Suspicious characters in domain name")
            
        except Exception as e:
            issues.append(f"URL structure validation error: {e}")
        
        return issues
    
    def _has_credentials(self, url: str) -> bool:
        """Checks if URL contains authentication credentials"""
        try:
            parsed = urlparse(url)
            return bool(parsed.username or parsed.password)
        except Exception:
            return False
    
    def _encode_dangerous_chars(self, url: str) -> str:
        """Encodes potentially dangerous characters in URL"""
        # Characters that could be used for injection
        dangerous_chars = {
            '<': '%3C',
            '>': '%3E',
            '"': '%22',
            "'": '%27',
            '`': '%60'
        }
        
        for char, encoded in dangerous_chars.items():
            url = url.replace(char, encoded)
        
        return url
    
    def _mask_sensitive_params(self, query_string: str) -> str:
        """Masks sensitive parameters in query string"""
        if not query_string:
            return query_string
        
        try:
            from urllib.parse import parse_qs, urlencode
            
            # Parse query parameters
            params = parse_qs(query_string, keep_blank_values=True)
            
            # Mask sensitive parameters
            for param_name in list(params.keys()):
                if any(sensitive in param_name.lower() for sensitive in self.sensitive_params):
                    params[param_name] = ['***MASKED***']
            
            # Reconstruct query string
            return urlencode(params, doseq=True)
            
        except Exception as e:
            logger.error(f"Error masking sensitive parameters: {e}")
            return "[MASKED_QUERY]"
    
    def validate_batch_urls(self, urls: List[str]) -> Dict[str, Any]:
        """
        Validates a batch of URLs for security
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            Dictionary with batch validation results
        """
        results = {
            "total_urls": len(urls),
            "safe_urls": 0,
            "unsafe_urls": 0,
            "warnings": 0,
            "threats_by_type": {},
            "unsafe_url_indices": []
        }
        
        for i, url in enumerate(urls):
            validation = self.validate_url_security(url)
            
            if validation["is_safe"]:
                results["safe_urls"] += 1
            else:
                results["unsafe_urls"] += 1
                results["unsafe_url_indices"].append(i)
            
            if validation["warnings"]:
                results["warnings"] += len(validation["warnings"])
            
            # Count threat types
            for threat in validation["threats_found"]:
                threat_type = threat.split(":")[0] if ":" in threat else threat
                results["threats_by_type"][threat_type] = results["threats_by_type"].get(threat_type, 0) + 1
        
        return results