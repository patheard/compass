"""Security middleware for FastAPI application."""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(
        self, 
        app,
        enforce_https: bool = True,
        max_age: int = 31536000,  # 1 year
        include_subdomains: bool = True
    ) -> None:
        super().__init__(app)
        self.enforce_https = enforce_https
        self.max_age = max_age
        self.include_subdomains = include_subdomains
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response."""
        response: Response = await call_next(request)
        
        # HSTS - Enforce HTTPS
        if self.enforce_https:
            hsts_value = f"max-age={self.max_age}"
            if self.include_subdomains:
                hsts_value += "; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # Content Security Policy - Prevent XSS
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.design-system.alpha.canada.ca; "
            "style-src 'self' https://cdn.design-system.alpha.canada.ca https://fonts.googleapis.com/; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.design-system.alpha.canada.ca https://fonts.gstatic.com; "
            "connect-src 'self' https://cdn.design-system.alpha.canada.ca; "
            "frame-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # Cache-Control for sensitive pages
        if request.url.path.startswith("/auth") or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(
        self, 
        app,
        requests_per_minute: int = 60,
        burst_requests: int = 10
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_requests = burst_requests
        self.request_counts: Dict[str, list] = defaultdict(list)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _clean_old_requests(self, client_ip: str, current_time: float) -> None:
        """Remove requests older than 1 minute."""
        cutoff_time = current_time - 60
        self.request_counts[client_ip] = [
            timestamp for timestamp in self.request_counts[client_ip]
            if timestamp > cutoff_time
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old requests
        self._clean_old_requests(client_ip, current_time)
        
        # Check rate limits
        request_count = len(self.request_counts[client_ip])
        
        if request_count >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        # Check burst limit (last 10 seconds)
        recent_requests = [
            timestamp for timestamp in self.request_counts[client_ip]
            if timestamp > current_time - 10
        ]
        
        if len(recent_requests) >= self.burst_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests in short time. Please slow down.",
                headers={"Retry-After": "10"}
            )
        
        # Record this request
        self.request_counts[client_ip].append(current_time)
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - len(self.request_counts[client_ip]))
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + 60)
        )
        
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for basic input validation and sanitization."""
    
    BLOCKED_PATTERNS = [
        "<script",
        "javascript:",
        "vbscript:",
        "onload=",
        "onerror=",
        "onclick=",
        "eval(",
        "expression(",
        "<?php",
        "<?xml"
    ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate request inputs."""
        # Check URL path for suspicious patterns
        path_lower = request.url.path.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in path_lower:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request"
                )
        
        # Check query parameters
        for key, value in request.query_params.items():
            value_lower = str(value).lower()
            for pattern in self.BLOCKED_PATTERNS:
                if pattern in value_lower:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request parameters"
                    )
        
        return await call_next(request)