"""CORS configuration for the application."""

from typing import List


class CORSConfig:
    """Configuration for CORS middleware."""

    # Allowed origins (restrict to your domains in production)
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8000",
    ]

    # Allowed methods
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

    # Allowed headers
    ALLOWED_HEADERS: List[str] = [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
    ]

    # Whether to allow credentials
    ALLOW_CREDENTIALS: bool = True

    # Max age for preflight requests
    MAX_AGE: int = 300  # 5 minutes

    @classmethod
    def get_cors_kwargs(cls) -> dict:
        """Get kwargs for CORSMiddleware configuration."""
        return {
            "allow_origins": cls.ALLOWED_ORIGINS,
            "allow_credentials": cls.ALLOW_CREDENTIALS,
            "allow_methods": cls.ALLOWED_METHODS,
            "allow_headers": cls.ALLOWED_HEADERS,
            "max_age": cls.MAX_AGE,
        }


cors_config = CORSConfig()
