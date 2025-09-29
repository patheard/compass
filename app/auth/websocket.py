"""WebSocket authentication utilities."""

from typing import Optional
from base64 import b64decode
import json
import logging

from fastapi import WebSocket
from itsdangerous import TimestampSigner

from app.database.models.users import User
from app.security.session import session_config

logger = logging.getLogger(__name__)

class WebSocketAuth:
    """WebSocket authentication helper."""

    def __init__(self):
        """Initialize WebSocket authentication."""
        cfg = session_config.get_session_middleware_kwargs()
        # Use the same TimestampSigner as Starlette's SessionMiddleware
        self.signer = TimestampSigner(str(cfg.get("secret_key")))
        # Keep the max_age so we can validate timestamped signatures
        self.max_age = cfg.get("max_age")

    async def get_user_from_websocket(self, websocket: WebSocket) -> Optional[User]:
        """Extract user from WebSocket session cookie."""
        try:
            # Get cookies from WebSocket headers
            cookie_header = None
            for name, value in websocket.headers.items():
                if name.lower() == "cookie":
                    cookie_header = value
                    break

            if not cookie_header:
                return None

            # Parse session cookie
            session_cookie = None
            for cookie_pair in cookie_header.split(";"):
                cookie_pair = cookie_pair.strip()
                if cookie_pair.startswith("session="):
                    session_cookie = cookie_pair.split("=", 1)[1]
                    break

            if not session_cookie:
                return None

            # Decode session data the same way Starlette does:
            # signer.unsign -> base64 decode -> json.loads
            try:
                unsigned = self.signer.unsign(
                    session_cookie.encode("utf-8"), max_age=self.max_age
                )
                session_data = json.loads(b64decode(unsigned))
            except Exception:
                return None

            # Extract user data from session
            user_data = session_data.get("user")
            if not user_data:
                return None

            return User.from_dict(user_data)

        except Exception:
            return None

    async def authenticate_websocket(self, websocket: WebSocket) -> Optional[User]:
        """Authenticate WebSocket connection and return user if valid."""
        try:
            user = await self.get_user_from_websocket(websocket)
            if not user:
                await websocket.close(code=1008, reason="Authentication required")
                return None
            return user
        except Exception as e:
            logger.error(f"WebSocket authentication error: {str(e)}")

            try:
                await websocket.close(code=1011, reason="Authentication error")
            except Exception as _e:
                logger.debug(f"WebSocket close during auth failure: {_e}")
            return None


def get_websocket_auth() -> WebSocketAuth:
    """Get a WebSocketAuth instance."""
    return WebSocketAuth()
