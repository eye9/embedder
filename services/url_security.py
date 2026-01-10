"""
URL Security and Sanitization for TNVED Code Matching System

This module provides security features for URL processing, including
input validation, sanitization, and protection against common attacks.
"""

import logging
import re
import hashlib
import time
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, quote, unquote
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class SecurityViolation:
    """Represents a security violation detected in URL processing"""
    violation_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    url: str
    timestamp: float = field(default_factory=time.time)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None


class URLSecurityError(Exception):
    """Raised when URL security validation fails"""
    pass


class SecurityViolationTracker:
    """
    Tracks and logs security violations for monitoring and alerting
    """
    
    def __init__(self):
        """Initialize security violation tracker"""
        self.violations: List[SecurityViolation] = []
        self.violation_counts: Dict[str, int] = {}
        self.blocked_patterns: Set[str] = set()
        
    def record_violation(self, violation: SecurityViolation) -> None:
        """
        Records a security violation
        
        Args:
            violation: SecurityViolation instance
        """
        self.violations.append(violation)
        self.violation_counts[violation.violation_type] = self.violation_counts.get(violation.violation_type, 0) + 1
        
        # Log the violation
        log_level = self._get_log_level(violation.severity)
        logger.log(log_level, 
                  f"Security violation detected: {violation.violation_type} - {violation.description} "
                  f"(URL: {self._sanitize_url_for_logging(violation.url)})")
        
        # Add to blocked patterns if critical
        if violation.severity == "critical":
            pattern_hash = hashlib.md5(violation.url.encode()).hexdigest()
            self.blocked_patterns.add(pattern_hash)
            logger.critical(f"URL pattern blocked due to critical security violation: {pattern_hash}")
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """
        Gets summary of security violations
        
        Returns:
            Dictionary with violation statistics
        """
        return {
            "total_violations": len(self.violations),
            "violations_by_type": self.violation_counts.copy(),
            "blocked_patterns_count": len(self.blocked_patterns),
            "recent_violations": [
                {
                    "type": v.violation_type,
                    "severity": v.severity,
                    "timestamp": v.timestamp,
                    "description": v.description
                }
                for v in self.violations[-10:]  # Last 10 violations
            ]
        }
    
    def is_pattern_blocked(self, url: str) -> bool:
        """
        Checks if URL pattern is blocked
        
        Args:
            url: URL to check
            
        Returns:
            True if pattern is blocked
        """
        pattern_hash = hashlib.md5(url.encode()).hexdigest()
        return pattern_hash in self.blocked_patterns
    
    def _get_log_level(self, severity: str) -> int:
        """Maps severity to logging level"""
        severity_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }
        return severity_map.get(severity, logging.WARNING)
    
    def _sanitize_url_for_logging(self, url: str) -> str:
        """Sanitizes URL for safe logging"""
        try:
            parsed = urlparse(url)
            # Remove credentials and sensitive params
            if parsed.username or parsed.password:
                netloc = parsed.hostname
                if parsed.port:
                    netloc = f"{netloc}:{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
            
            # Mask query parameters
            if parsed.query:
                parsed = parsed._replace(query="[MASKED_PARAMS]")
            
            return parsed.geturl()
        except Exception:
            return "[MALFORMED_URL]"


class URLSecurity:
    """
    Provides URL security validation and sanitization
    
    Features:
    - Input validation against malicious patterns
    - URL sanitization for safe storage and logging
    - Parameter masking for sensitive data
    - SQL injection prevention for database queries
    - Security violation tracking and logging
    - Parameterized query protection
    """
    
    def __init__(self, enable_violation_tracking: bool = True):
        """Initialize URL security validator"""
        self.violation_tracker = SecurityViolationTracker() if enable_violation_tracking else None
        
        # Enhanced patterns that indicate potential security threats
        self.malicious_patterns = [
            # Script injection patterns
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
            r'onfocus\s*=',
            
            # Data URI schemes that could be dangerous
            r'data:text/html',
            r'data:application/javascript',
            r'data:text/javascript',
            
            # File system access
            r'file://',
            r'\.\./',
            r'%2e%2e%2f',
            r'%2e%2e\\',
            
            # Protocol manipulation
            r'ftp://',
            r'ldap://',
            r'gopher://',
            r'telnet://',
            
            # SQL injection patterns in URLs
            r'union\s+select',
            r'drop\s+table',
            r'insert\s+into',
            r'delete\s+from',
            r'update\s+set',
            r'exec\s*\(',
            r'sp_executesql',
            
            # Command injection
            r';\s*rm\s+',
            r';\s*cat\s+',
            r';\s*ls\s+',
            r';\s*dir\s+',
            r';\s*del\s+',
            r'`[^`]*`',
            r'\$\([^)]*\)',
            r'&&\s*[a-zA-Z]',
            r'\|\|\s*[a-zA-Z]',
            
            # XSS patterns
            r'alert\s*\(',
            r'confirm\s*\(',
            r'prompt\s*\(',
            r'document\.cookie',
            r'window\.location',
            
            # Path traversal
            r'\.\.[\\/]',
            r'%c0%af',
            r'%c1%9c',
            
            # LDAP injection
            r'\*\)\(\|',
            r'\*\)\(\&',
            
            # XML injection
            r'<\?xml',
            r'<!DOCTYPE',
            r'<!ENTITY'
        ]
        
        # Enhanced sensitive parameter names to mask in logs
        self.sensitive_params = [
            'password', 'pwd', 'pass', 'secret', 'key', 'token',
            'auth', 'session', 'sid', 'api_key', 'access_token',
            'refresh_token', 'oauth', 'credential', 'login',
            'username', 'user', 'email', 'phone', 'ssn',
            'credit_card', 'card_number', 'cvv', 'pin',
            'private_key', 'certificate', 'signature'
        ]
        
        logger.info("URLSecurity initialized with enhanced security patterns and violation tracking")
    
    def validate_url_security(self, url: str, source_ip: Optional[str] = None, 
                              user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates URL for security threats with enhanced logging
        
        Args:
            url: URL to validate
            source_ip: Source IP address for violation tracking
            user_agent: User agent for violation tracking
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_safe": True,
            "threats_found": [],
            "warnings": [],
            "sanitized_url": url,
            "violations_recorded": 0
        }
        
        if not url or not isinstance(url, str):
            violation = SecurityViolation(
                violation_type="invalid_input",
                severity="medium",
                description="Invalid or empty URL provided",
                url=str(url) if url else "[EMPTY]",
                source_ip=source_ip,
                user_agent=user_agent
            )
            self._record_violation(violation)
            
            result["is_safe"] = False
            result["threats_found"].append("Invalid or empty URL")
            result["violations_recorded"] = 1
            return result
        
        try:
            # Check if pattern is already blocked
            if self.violation_tracker and self.violation_tracker.is_pattern_blocked(url):
                result["is_safe"] = False
                result["threats_found"].append("URL pattern is blocked due to previous security violations")
                return result
            
            # Check for malicious patterns
            threats = self._detect_malicious_patterns(url, source_ip, user_agent)
            if threats:
                result["is_safe"] = False
                result["threats_found"].extend(threats)
                result["violations_recorded"] += len(threats)
            
            # Check URL structure
            structure_issues = self._validate_url_structure(url, source_ip, user_agent)
            if structure_issues:
                result["warnings"].extend(structure_issues)
            
            # Generate sanitized version
            result["sanitized_url"] = self.sanitize_url_for_storage(url)
            
            # Check for credentials
            if self._has_credentials(url):
                violation = SecurityViolation(
                    violation_type="credentials_in_url",
                    severity="high",
                    description="URL contains authentication credentials",
                    url=url,
                    source_ip=source_ip,
                    user_agent=user_agent
                )
                self._record_violation(violation)
                result["warnings"].append("URL contains authentication credentials")
                result["violations_recorded"] += 1
            
            # Check length
            if len(url) > 2048:
                violation = SecurityViolation(
                    violation_type="excessive_length",
                    severity="medium",
                    description=f"URL exceeds recommended length limit ({len(url)} chars)",
                    url=url,
                    source_ip=source_ip,
                    user_agent=user_agent
                )
                self._record_violation(violation)
                result["warnings"].append("URL exceeds recommended length limit")
                result["violations_recorded"] += 1
            
        except Exception as e:
            logger.error(f"Error during URL security validation: {e}")
            violation = SecurityViolation(
                violation_type="validation_error",
                severity="high",
                description=f"Validation error: {e}",
                url=url,
                source_ip=source_ip,
                user_agent=user_agent
            )
            self._record_violation(violation)
            
            result["is_safe"] = False
            result["threats_found"].append(f"Validation error: {e}")
            result["violations_recorded"] = 1
        
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
        Creates a URL string safe for parameterized database queries with enhanced protection
        
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
            
            # Enhanced escaping for database safety
            # Note: This is additional protection, parameterized queries
            # should still be used as the primary defense
            safe_url = sanitized.replace("'", "''")     # Escape single quotes
            safe_url = safe_url.replace('"', '""')      # Escape double quotes
            safe_url = safe_url.replace(";", "")        # Remove semicolons
            safe_url = safe_url.replace("--", "")       # Remove SQL comments
            safe_url = safe_url.replace("/*", "")       # Remove SQL block comments
            safe_url = safe_url.replace("*/", "")       # Remove SQL block comments
            safe_url = safe_url.replace("xp_", "")      # Remove SQL Server extended procedures
            safe_url = safe_url.replace("sp_", "")      # Remove SQL Server stored procedures
            
            # Remove potential SQL injection keywords
            sql_keywords = [
                "union", "select", "insert", "update", "delete", "drop", 
                "create", "alter", "exec", "execute", "declare", "cast",
                "convert", "substring", "ascii", "char", "nchar", "varchar"
            ]
            
            for keyword in sql_keywords:
                # Case-insensitive removal with word boundaries
                pattern = r'\b' + re.escape(keyword) + r'\b'
                safe_url = re.sub(pattern, "", safe_url, flags=re.IGNORECASE)
            
            # Final cleanup - remove multiple spaces
            safe_url = re.sub(r'\s+', ' ', safe_url).strip()
            
            return safe_url
            
        except Exception as e:
            logger.error(f"Error creating query-safe URL: {e}")
            return ""
    
    def sanitize_url_for_logging(self, url: str, mask_level: str = "standard") -> str:
        """
        Sanitizes URL for safe logging with configurable masking levels
        
        Args:
            url: URL to sanitize
            mask_level: Masking level - "minimal", "standard", "aggressive"
            
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
            
            # Apply masking based on level
            if mask_level == "minimal":
                # Only mask sensitive query parameters
                if parsed.query:
                    masked_query = self._mask_sensitive_params(parsed.query)
                    parsed = parsed._replace(query=masked_query)
            
            elif mask_level == "standard":
                # Mask sensitive params and remove fragment
                if parsed.query:
                    masked_query = self._mask_sensitive_params(parsed.query)
                    parsed = parsed._replace(query=masked_query)
                parsed = parsed._replace(fragment='')
            
            elif mask_level == "aggressive":
                # Mask all query parameters and fragment
                if parsed.query:
                    parsed = parsed._replace(query="[MASKED_PARAMS]")
                parsed = parsed._replace(fragment='')
                
                # Also mask path if it contains sensitive patterns
                if parsed.path and any(sensitive in parsed.path.lower() for sensitive in self.sensitive_params):
                    path_parts = parsed.path.split('/')
                    masked_parts = []
                    for part in path_parts:
                        if any(sensitive in part.lower() for sensitive in self.sensitive_params):
                            masked_parts.append("[MASKED]")
                        else:
                            masked_parts.append(part)
                    parsed = parsed._replace(path='/'.join(masked_parts))
            
            return parsed.geturl()
            
        except Exception as e:
            logger.error(f"Error sanitizing URL for logging: {e}")
            return "[MALFORMED_URL]"
    
    def get_security_violation_summary(self) -> Dict[str, Any]:
        """
        Gets summary of security violations for monitoring
        
        Returns:
            Dictionary with violation statistics
        """
        if not self.violation_tracker:
            return {"error": "Violation tracking is disabled"}
        
        return self.violation_tracker.get_violation_summary()
    
    def _record_violation(self, violation: SecurityViolation) -> None:
        """Records a security violation if tracking is enabled"""
        if self.violation_tracker:
            self.violation_tracker.record_violation(violation)
    
    def _detect_malicious_patterns(self, url: str, source_ip: Optional[str] = None, 
                                  user_agent: Optional[str] = None) -> List[str]:
        """Detects malicious patterns in URL and records violations"""
        threats = []
        
        for pattern in self.malicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                threat_desc = f"Malicious pattern detected: {pattern}"
                threats.append(threat_desc)
                
                # Determine severity based on pattern type
                severity = "high"
                if any(critical in pattern for critical in ['script', 'javascript', 'exec', 'drop', 'delete']):
                    severity = "critical"
                elif any(medium in pattern for medium in ['file://', 'ftp://', 'ldap://']):
                    severity = "medium"
                
                violation = SecurityViolation(
                    violation_type="malicious_pattern",
                    severity=severity,
                    description=threat_desc,
                    url=url,
                    source_ip=source_ip,
                    user_agent=user_agent
                )
                self._record_violation(violation)
        
        return threats
    
    def _validate_url_structure(self, url: str, source_ip: Optional[str] = None, 
                               user_agent: Optional[str] = None) -> List[str]:
        """Validates basic URL structure and records violations"""
        issues = []
        
        try:
            parsed = urlparse(url)
            
            # Check for valid scheme
            if parsed.scheme not in ['http', 'https']:
                issue = f"Unsupported URL scheme: {parsed.scheme}"
                issues.append(issue)
                
                violation = SecurityViolation(
                    violation_type="invalid_scheme",
                    severity="medium",
                    description=issue,
                    url=url,
                    source_ip=source_ip,
                    user_agent=user_agent
                )
                self._record_violation(violation)
            
            # Check for valid netloc
            if not parsed.netloc:
                issue = "URL missing domain name"
                issues.append(issue)
                
                violation = SecurityViolation(
                    violation_type="missing_domain",
                    severity="medium",
                    description=issue,
                    url=url,
                    source_ip=source_ip,
                    user_agent=user_agent
                )
                self._record_violation(violation)
            
            # Check for suspicious characters in domain
            if parsed.netloc and re.search(r'[<>"\']', parsed.netloc):
                issue = "Suspicious characters in domain name"
                issues.append(issue)
                
                violation = SecurityViolation(
                    violation_type="suspicious_domain_chars",
                    severity="high",
                    description=issue,
                    url=url,
                    source_ip=source_ip,
                    user_agent=user_agent
                )
                self._record_violation(violation)
            
            # Check for IP addresses in domain (potential security risk)
            if parsed.netloc and re.match(r'^\d+\.\d+\.\d+\.\d+', parsed.netloc):
                issue = "URL uses IP address instead of domain name"
                issues.append(issue)
                
                violation = SecurityViolation(
                    violation_type="ip_address_domain",
                    severity="low",
                    description=issue,
                    url=url,
                    source_ip=source_ip,
                    user_agent=user_agent
                )
                self._record_violation(violation)
            
        except Exception as e:
            issue = f"URL structure validation error: {e}"
            issues.append(issue)
            
            violation = SecurityViolation(
                violation_type="structure_validation_error",
                severity="medium",
                description=issue,
                url=url,
                source_ip=source_ip,
                user_agent=user_agent
            )
            self._record_violation(violation)
        
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
    
    def validate_batch_urls(self, urls: List[str], source_ip: Optional[str] = None, 
                           user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates a batch of URLs for security with enhanced reporting
        
        Args:
            urls: List of URLs to validate
            source_ip: Source IP address for violation tracking
            user_agent: User agent for violation tracking
            
        Returns:
            Dictionary with batch validation results
        """
        results = {
            "total_urls": len(urls),
            "safe_urls": 0,
            "unsafe_urls": 0,
            "warnings": 0,
            "total_violations": 0,
            "threats_by_type": {},
            "violations_by_severity": {},
            "unsafe_url_indices": [],
            "processing_time_ms": 0
        }
        
        start_time = time.time()
        
        for i, url in enumerate(urls):
            validation = self.validate_url_security(url, source_ip, user_agent)
            
            if validation["is_safe"]:
                results["safe_urls"] += 1
            else:
                results["unsafe_urls"] += 1
                results["unsafe_url_indices"].append(i)
            
            if validation["warnings"]:
                results["warnings"] += len(validation["warnings"])
            
            if validation.get("violations_recorded", 0) > 0:
                results["total_violations"] += validation["violations_recorded"]
            
            # Count threat types
            for threat in validation["threats_found"]:
                threat_type = threat.split(":")[0] if ":" in threat else threat
                results["threats_by_type"][threat_type] = results["threats_by_type"].get(threat_type, 0) + 1
        
        # Add violation summary if tracking is enabled
        if self.violation_tracker:
            violation_summary = self.violation_tracker.get_violation_summary()
            for violation in violation_summary.get("recent_violations", []):
                severity = violation["severity"]
                results["violations_by_severity"][severity] = results["violations_by_severity"].get(severity, 0) + 1
        
        results["processing_time_ms"] = (time.time() - start_time) * 1000
        
        # Log batch processing results
        logger.info(f"Batch URL validation completed: {results['safe_urls']}/{results['total_urls']} URLs safe, "
                   f"{results['total_violations']} violations recorded, "
                   f"processed in {results['processing_time_ms']:.2f}ms")
        
        return results