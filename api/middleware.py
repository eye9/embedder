"""
API Middleware

This module provides middleware for authentication, rate limiting, CORS, and security headers.
"""

import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.base import SecurityBase
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger(__name__)


class APIKeyAuth(SecurityBase):
    """API Key authentication scheme"""
    
    def __init__(self, api_keys: List[str], auto_error: bool = True):
        self.api_keys = set(api_keys) if api_keys else set()
        self.auto_error = auto_error
        self.model = HTTPBearer(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Validate API key from request"""
        if not self.api_keys:
            # If no API keys configured, allow all requests
            return None
        
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # Try to get from Authorization header as Bearer token
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header[7:]  # Remove "Bearer " prefix
        
        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required. Provide via X-API-Key header or Authorization: Bearer <key>",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        if api_key not in self.api_keys:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        return api_key


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window algorithm"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute in seconds
        self.client_requests: Dict[str, deque] = defaultdict(deque)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        # Try to get real IP from X-Forwarded-For header (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Fall back to direct client IP
            client_ip = request.client.host if request.client else "unknown"
        
        return client_ip
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited"""
        now = time.time()
        client_requests = self.client_requests[client_id]
        
        # Remove requests outside the current window
        while client_requests and client_requests[0] <= now - self.window_size:
            client_requests.popleft()
        
        # Check if client has exceeded the limit
        if len(client_requests) >= self.requests_per_minute:
            return True
        
        # Add current request
        client_requests.append(now)
        return False
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting"""
        client_id = self._get_client_id(request)
        
        if self._is_rate_limited(client_id):
            logger.warning(f"Rate limit exceeded for client {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Log request and response details"""
        start_time = time.time()
        
        # Log request
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"Request: {request.method} {request.url.path} from {client_ip}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {response.status_code} for {request.method} {request.url.path} "
                f"({process_time:.3f}s)"
            )
            
            # Add processing time to response headers
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Error: {str(e)} for {request.method} {request.url.path} "
                f"({process_time:.3f}s)",
                exc_info=True
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response"""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


def setup_cors_middleware(app, cors_config):
    """Setup CORS middleware"""
    if cors_config.enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_config.origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for origins: {cors_config.origins}")


def setup_rate_limiting(app, rate_limit_config):
    """Setup rate limiting middleware"""
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=rate_limit_config.requests_per_minute
    )
    logger.info(f"Rate limiting enabled: {rate_limit_config.requests_per_minute} requests/minute")


def setup_logging_middleware(app):
    """Setup request/response logging middleware"""
    app.add_middleware(LoggingMiddleware)
    logger.info("Request/response logging enabled")


def setup_security_headers(app):
    """Setup security headers middleware"""
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware enabled")