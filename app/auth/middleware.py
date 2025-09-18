"""Authentication middleware and dependencies."""

from typing import Optional
from fastapi import HTTPException, status, Request
from fastapi.responses import RedirectResponse
from app.database.models.users import User
import time


async def get_user_from_session(request: Request) -> Optional[User]:
    """Get user from session cookie with enhanced security checks."""
    user_data = request.session.get("user")
    if not user_data:
        return None

    # Check session timestamp to enforce timeout
    session_timestamp = request.session.get("timestamp")
    if session_timestamp:
        current_time = time.time()
        session_age = current_time - session_timestamp

        # Session timeout: 15 minutes (900 seconds)
        if session_age > 900:
            # Clear expired session
            request.session.clear()
            return None

        # Update timestamp for sliding window
        request.session["timestamp"] = current_time
    else:
        # Set timestamp if not present
        request.session["timestamp"] = time.time()

    try:
        # Reconstruct User object from session data
        return User.from_dict(user_data)
    except Exception:
        # Clear invalid session data
        request.session.clear()
        return None


async def check_session_security(request: Request) -> None:
    """Additional session security checks."""
    # Check for session fixation attacks by validating session ID rotation
    user_agent = request.headers.get("User-Agent", "")
    stored_user_agent = request.session.get("user_agent")

    if stored_user_agent and stored_user_agent != user_agent:
        # Potential session hijacking - clear session
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session security violation detected",
        )

    # Store user agent for future checks
    if not stored_user_agent:
        request.session["user_agent"] = user_agent


async def require_authenticated_user(request: Request) -> User:
    """Dependency that requires an authenticated user."""
    user = await get_user_from_session(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Additional security checks
    await check_session_security(request)

    return user
