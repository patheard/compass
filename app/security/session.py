"""Secure session configuration."""

import os
from typing import Optional


class SecureSessionConfig:
    """Configuration for secure session middleware."""

    # Session settings
    SESSION_COOKIE_NAME: str = "session"
    SESSION_MAX_AGE: int = 28800  # 8 hours
    SESSION_COOKIE_SECURE: bool = True  # Only send over HTTPS
    SESSION_COOKIE_HTTPONLY: bool = True  # Prevent JS access
    SESSION_COOKIE_SAMESITE: str = "strict"  # CSRF protection
    SESSION_COOKIE_PATH: str = "/"
    SESSION_COOKIE_DOMAIN: Optional[str] = None

    # JWT token lifetime
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    @classmethod
    def get_session_middleware_kwargs(cls) -> dict:
        """Get kwargs for SessionMiddleware configuration."""
        return {
            "secret_key": os.getenv("SECRET_KEY"),
            "max_age": cls.SESSION_MAX_AGE,
            "session_cookie": cls.SESSION_COOKIE_NAME,
            "https_only": cls.SESSION_COOKIE_SECURE,
            "same_site": cls.SESSION_COOKIE_SAMESITE,
            "path": cls.SESSION_COOKIE_PATH,
            "domain": cls.SESSION_COOKIE_DOMAIN,
        }


session_config = SecureSessionConfig()
