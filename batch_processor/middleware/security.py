"""
Security middleware for the batch processor web application.

This module provides security enhancements including rate limiting,
CSRF protection, and security headers.
"""

import time
import hashlib
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from fastapi import Request, Response, HTTPException
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from batch_processor.config.settings import get_config


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm."""
    
    def __init__(self, app):
        super().__init__(app)
        self.config = get_config()
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, float] = {}
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers if behind proxy
        if self.config.web.proxy_headers:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
            
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str) -> Tuple[bool, Optional[int]]:
        """Check if client is rate limited."""
        if not self.config.security.rate_limiting.enabled:
            return False, None
        
        current_time = time.time()
        window_size = 60  # 1 minute window
        
        # Check if IP is temporarily blocked
        if client_ip in self.blocked_ips:
            if current_time < self.blocked_ips[client_ip]:
                remaining = int(self.blocked_ips[client_ip] - current_time)
                return True, remaining
            else:
                del self.blocked_ips[client_ip]
        
        # Clean old requests outside the window
        client_requests = self.requests[client_ip]
        while client_requests and client_requests[0] < current_time - window_size:
            client_requests.popleft()
        
        # Check rate limit
        requests_per_minute = self.config.security.rate_limiting.requests_per_minute
        burst_size = self.config.security.rate_limiting.burst_size
        
        if len(client_requests) >= requests_per_minute:
            # Block IP for 1 minute
            self.blocked_ips[client_ip] = current_time + 60
            return True, 60
        
        # Check burst limit (requests in last 10 seconds)
        recent_requests = sum(1 for req_time in client_requests if req_time > current_time - 10)
        if recent_requests >= burst_size:
            return True, 10
        
        # Add current request
        client_requests.append(current_time)
        return False, None
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        is_limited, retry_after = self._is_rate_limited(client_ip)
        if is_limited:
            headers = {"Retry-After": str(retry_after)} if retry_after else {}
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": retry_after},
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if self.config.security.rate_limiting.enabled:
            remaining = max(0, self.config.security.rate_limiting.requests_per_minute - len(self.requests[client_ip]))
            response.headers["X-RateLimit-Limit"] = str(self.config.security.rate_limiting.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.config = get_config()
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HTTPS enforcement
        if self.config.security.https_only:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Hide server information
        if not self.config.web.server_header:
            response.headers.pop("Server", None)
        
        return response


class FailedLoginTracker:
    """Track failed login attempts and implement lockout."""
    
    def __init__(self):
        self.config = get_config()
        self.failed_attempts: Dict[str, deque] = defaultdict(deque)
        self.locked_accounts: Dict[str, float] = {}
    
    def _get_key(self, username: str, client_ip: str) -> str:
        """Get tracking key based on configuration."""
        if self.config.auth.failed_login_protection.track_by_ip:
            return f"{username}:{client_ip}"
        return username
    
    def is_locked(self, username: str, client_ip: str) -> Tuple[bool, Optional[int]]:
        """Check if account/IP is locked."""
        key = self._get_key(username, client_ip)
        current_time = time.time()
        
        # Check if locked
        if key in self.locked_accounts:
            if current_time < self.locked_accounts[key]:
                remaining = int(self.locked_accounts[key] - current_time)
                return True, remaining
            else:
                del self.locked_accounts[key]
                self.failed_attempts[key].clear()
        
        return False, None
    
    def record_failed_attempt(self, username: str, client_ip: str) -> bool:
        """Record failed login attempt. Returns True if account should be locked."""
        key = self._get_key(username, client_ip)
        current_time = time.time()
        window_size = self.config.auth.failed_login_protection.lockout_duration_minutes * 60
        
        # Clean old attempts
        attempts = self.failed_attempts[key]
        while attempts and attempts[0] < current_time - window_size:
            attempts.popleft()
        
        # Add current attempt
        attempts.append(current_time)
        
        # Check if should lock
        max_attempts = self.config.auth.failed_login_protection.max_attempts
        if len(attempts) >= max_attempts:
            lockout_duration = self.config.auth.failed_login_protection.lockout_duration_minutes * 60
            self.locked_accounts[key] = current_time + lockout_duration
            return True
        
        return False
    
    def record_successful_login(self, username: str, client_ip: str):
        """Record successful login and clear failed attempts."""
        key = self._get_key(username, client_ip)
        self.failed_attempts[key].clear()
        self.locked_accounts.pop(key, None)


# Global instance
failed_login_tracker = FailedLoginTracker()


def validate_password_policy(password: str) -> Tuple[bool, str]:
    """Validate password against policy."""
    config = get_config()
    policy = config.auth.password_policy
    
    if len(password) < policy.min_length:
        return False, f"Password must be at least {policy.min_length} characters long"
    
    if policy.require_uppercase and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if policy.require_lowercase and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if policy.require_numbers and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if policy.require_special_chars and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"


def generate_csrf_token(session_id: str) -> str:
    """Generate CSRF token for session."""
    config = get_config()
    data = f"{session_id}:{config.auth.session_secret}:{time.time()}"
    return hashlib.sha256(data.encode()).hexdigest()


def validate_csrf_token(token: str, session_id: str) -> bool:
    """Validate CSRF token."""
    if not token or not session_id:
        return False
    
    config = get_config()
    # Simple validation - in production, use more sophisticated approach
    expected_prefix = hashlib.sha256(f"{session_id}:{config.auth.session_secret}".encode()).hexdigest()[:16]
    return token.startswith(expected_prefix)