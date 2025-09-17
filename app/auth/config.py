"""Authentication configuration."""

import os
from dotenv import load_dotenv

load_dotenv()


class AuthConfig:
    """Authentication configuration settings."""

    # Google OAuth settings
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL: str = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # Application settings
    BASE_URL: str = os.getenv("BASE_URL")

    @classmethod
    def validate_config(cls) -> None:
        """Validate required configuration values."""
        if not cls.GOOGLE_CLIENT_ID:
            raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
        if not cls.GOOGLE_CLIENT_SECRET:
            raise ValueError("GOOGLE_CLIENT_SECRET environment variable is required")


auth_config = AuthConfig()
