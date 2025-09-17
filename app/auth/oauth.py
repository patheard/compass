"""OAuth handlers for Google authentication."""

from authlib.integrations.starlette_client import OAuth
from app.auth.config import auth_config


class GoogleOAuth:
    """Google OAuth handler."""

    def __init__(self) -> None:
        """Initialize OAuth client."""
        self.oauth = OAuth()
        self.oauth.register(
            name="google",
            client_id=auth_config.GOOGLE_CLIENT_ID,
            client_secret=auth_config.GOOGLE_CLIENT_SECRET,
            server_metadata_url=auth_config.GOOGLE_DISCOVERY_URL,
            client_kwargs={
                "scope": "openid email profile",
            },
        )

    def get_client(self) -> OAuth:
        """Get OAuth client."""
        return self.oauth.google


# Singleton instance
google_oauth = GoogleOAuth()
