"""Security middleware for FastAPI application."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    def __init__(
        self,
        app,
        enforce_https: bool = True,
        max_age: int = 31536000,  # 1 year
        include_subdomains: bool = True,
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
            "script-src 'self' https://cdn.design-system.alpha.canada.ca https://cdn.jsdelivr.net/npm/chart.js@4.5.0/; "
            "style-src 'self' https://cdn.design-system.alpha.canada.ca https://fonts.googleapis.com/; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.design-system.alpha.canada.ca https://fonts.gstatic.com; "
            "connect-src 'self' https://cdn.design-system.alpha.canada.ca https://cdn.jsdelivr.net/npm/chart.js@4.5.0/; "
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
