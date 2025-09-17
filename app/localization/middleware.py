"""Localization middleware for automatic locale detection."""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.localization.utils import get_user_preferred_language


class LocalizationMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically detect and set user's preferred locale."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and set locale in request state."""
        # Get user's preferred language from available sources
        accept_language = request.headers.get("accept-language")

        # Safely get session preference
        session_preference = None
        try:
            if hasattr(request, "session"):
                session_preference = request.session.get("preferred_language")
        except (AttributeError, AssertionError):
            # Session not available, skip session preference
            pass

        # Determine the best language
        preferred_language = get_user_preferred_language(
            accept_language=accept_language, session_preference=session_preference
        )

        # Store the determined language in request state
        request.state.locale = preferred_language

        response = await call_next(request)
        return response


def get_request_locale(request: Request) -> str:
    """Get the locale for the current request."""
    return getattr(request.state, "locale", "en")
