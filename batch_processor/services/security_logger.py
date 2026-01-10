"""
Security-focused logging utilities for URL processing

This module provides enhanced logging capabilities specifically for
security events, violations, and URL processing activities.
"""

import logging
import json
import re
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

from ..config.settings import get_config


@dataclass
class SecurityLogEntry:
    """Structured security log entry"""
    timestamp: float
    event_type: str
    severity: str
    message: str
    url: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class SecurityLogger:
    """
    Enhanced security logger with structured logging and filtering
    """
    
    def __init__(self, logger_name: str = "url_security"):
        """
        Initialize security logger
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)
        self.config = get_config()
        
        # Set up structured logging if enabled
        if self.config.logging.structured_logging:
            self._setup_structured_logging()
        
        # Security event counters
        self.event_counters = {
            "violations": 0,
            "blocked_requests": 0,
            "sanitized_urls": 0,
            "validation_errors": 0
        }
        
        self.logger.info("SecurityLogger initialized with structured logging support")
    
    def log_security_violation(self, violation_type: str, severity: str, message: str,
                              url: Optional[str] = None, source_ip: Optional[str] = None,
                              user_agent: Optional[str] = None, session_id: Optional[str] = None,
                              additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Logs a security violation with structured data
        
        Args:
            violation_type: Type of security violation
            severity: Severity level (low, medium, high, critical)
            message: Descriptive message
            url: URL involved in the violation (will be sanitized)
            source_ip: Source IP address
            user_agent: User agent string
            session_id: Session identifier
            additional_data: Additional context data
        """
        self.event_counters["violations"] += 1
        
        # Create structured log entry
        entry = SecurityLogEntry(
            timestamp=time.time(),
            event_type=f"security_violation.{violation_type}",
            severity=severity,
            message=message,
            url=self._sanitize_url_for_logging(url) if url else None,
            source_ip=source_ip,
            user_agent=self._sanitize_user_agent(user_agent) if user_agent else None,
            session_id=session_id,
            additional_data=additional_data
        )
        
        # Log with appropriate level
        log_level = self._get_log_level(severity)
        
        if self.config.logging.structured_logging:
            self.logger.log(log_level, json.dumps(asdict(entry)))
        else:
            formatted_message = self._format_security_message(entry)
            self.logger.log(log_level, formatted_message)
    
    def log_url_processing_event(self, event_type: str, message: str, 
                                url: Optional[str] = None, processing_time_ms: Optional[float] = None,
                                additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Logs URL processing events
        
        Args:
            event_type: Type of processing event
            message: Descriptive message
            url: URL being processed (will be sanitized)
            processing_time_ms: Processing time in milliseconds
            additional_data: Additional context data
        """
        entry_data = {
            "timestamp": time.time(),
            "event_type": f"url_processing.{event_type}",
            "message": message,
            "url": self._sanitize_url_for_logging(url) if url else None,
            "processing_time_ms": processing_time_ms,
            "additional_data": additional_data
        }
        
        if self.config.logging.structured_logging:
            self.logger.info(json.dumps(entry_data))
        else:
            formatted_message = f"URL Processing [{event_type}]: {message}"
            if url:
                formatted_message += f" | URL: {self._sanitize_url_for_logging(url)}"
            if processing_time_ms:
                formatted_message += f" | Time: {processing_time_ms:.2f}ms"
            
            self.logger.info(formatted_message)
    
    def log_batch_processing_summary(self, total_urls: int, safe_urls: int, 
                                   violations: int, processing_time_ms: float,
                                   additional_stats: Optional[Dict[str, Any]] = None) -> None:
        """
        Logs batch processing summary
        
        Args:
            total_urls: Total number of URLs processed
            safe_urls: Number of safe URLs
            violations: Number of security violations
            processing_time_ms: Total processing time
            additional_stats: Additional statistics
        """
        summary_data = {
            "timestamp": time.time(),
            "event_type": "batch_processing.summary",
            "total_urls": total_urls,
            "safe_urls": safe_urls,
            "unsafe_urls": total_urls - safe_urls,
            "violations": violations,
            "processing_time_ms": processing_time_ms,
            "urls_per_second": total_urls / (processing_time_ms / 1000) if processing_time_ms > 0 else 0,
            "additional_stats": additional_stats
        }
        
        if self.config.logging.structured_logging:
            self.logger.info(json.dumps(summary_data))
        else:
            message = (f"Batch Processing Summary: {safe_urls}/{total_urls} URLs safe, "
                      f"{violations} violations, {processing_time_ms:.2f}ms total, "
                      f"{summary_data['urls_per_second']:.1f} URLs/sec")
            self.logger.info(message)
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """
        Gets current security statistics
        
        Returns:
            Dictionary with security statistics
        """
        return {
            "event_counters": self.event_counters.copy(),
            "logger_name": self.logger.name,
            "structured_logging_enabled": self.config.logging.structured_logging,
            "sensitive_data_masking_enabled": self.config.logging.sensitive_data_masking
        }
    
    def _setup_structured_logging(self) -> None:
        """Sets up structured JSON logging format"""
        # Create a JSON formatter
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": %(message)s}'
        )
        
        # Apply to all handlers
        for handler in self.logger.handlers:
            handler.setFormatter(json_formatter)
    
    def _sanitize_url_for_logging(self, url: str) -> str:
        """
        Sanitizes URL for safe logging
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL safe for logging
        """
        if not self.config.logging.sensitive_data_masking:
            return url
        
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            
            # Remove credentials
            if parsed.username or parsed.password:
                netloc = parsed.hostname
                if parsed.port:
                    netloc = f"{netloc}:{parsed.port}"
                parsed = parsed._replace(netloc=netloc)
            
            # Mask sensitive query parameters
            if parsed.query:
                from urllib.parse import parse_qs, urlencode
                params = parse_qs(parsed.query, keep_blank_values=True)
                
                sensitive_params = [
                    'password', 'pwd', 'pass', 'secret', 'key', 'token',
                    'auth', 'session', 'sid', 'api_key', 'access_token'
                ]
                
                for param_name in list(params.keys()):
                    if any(sensitive in param_name.lower() for sensitive in sensitive_params):
                        params[param_name] = ['***MASKED***']
                
                parsed = parsed._replace(query=urlencode(params, doseq=True))
            
            return parsed.geturl()
            
        except Exception:
            return "[MALFORMED_URL]"
    
    def _sanitize_user_agent(self, user_agent: str) -> str:
        """
        Sanitizes user agent string for logging
        
        Args:
            user_agent: User agent string
            
        Returns:
            Sanitized user agent
        """
        if not self.config.logging.sensitive_data_masking:
            return user_agent
        
        # Remove potentially sensitive information from user agent
        # Keep basic browser/OS info but remove detailed version numbers
        try:
            # Simple sanitization - remove version numbers and detailed system info
            sanitized = user_agent
            
            # Remove detailed version numbers (keep major versions only)
            sanitized = re.sub(r'(\d+\.\d+)\.\d+[\.\d]*', r'\1.x', sanitized)
            
            # Remove system-specific details
            sanitized = re.sub(r'Windows NT \d+\.\d+[^;)]*', 'Windows NT x.x', sanitized)
            sanitized = re.sub(r'Mac OS X \d+[_\d]*', 'Mac OS X x.x', sanitized)
            
            return sanitized
            
        except Exception:
            return "[SANITIZED_USER_AGENT]"
    
    def _get_log_level(self, severity: str) -> int:
        """Maps severity to logging level"""
        severity_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }
        return severity_map.get(severity, logging.WARNING)
    
    def _format_security_message(self, entry: SecurityLogEntry) -> str:
        """
        Formats security log entry for non-structured logging
        
        Args:
            entry: Security log entry
            
        Returns:
            Formatted message string
        """
        message = f"SECURITY [{entry.event_type}] [{entry.severity.upper()}]: {entry.message}"
        
        if entry.url:
            message += f" | URL: {entry.url}"
        
        if entry.source_ip:
            message += f" | IP: {entry.source_ip}"
        
        if entry.session_id:
            message += f" | Session: {entry.session_id}"
        
        if entry.additional_data:
            message += f" | Data: {json.dumps(entry.additional_data)}"
        
        return message


# Global security logger instance
_security_logger: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """Get the global security logger instance"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger